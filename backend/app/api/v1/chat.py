import json
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.models.user import User
from app.models.document import Document
from app.models.media import MediaFile
from app.models.chat import ChatSession, ChatMessage
from app.schemas.chat import (
    ChatSessionCreate, ChatSessionOut, ChatRequest, ChatResponse,
    ChatMessageOut, TimestampRef
)
from app.core.security import get_current_user
from app.core.rate_limiter import limiter
from app.services.vector_service import vector_service
from app.services.llm_service import llm_service
from app.services.transcription_service import transcription_service
from app.services.cache_service import cache_service

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("/sessions", response_model=ChatSessionOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def create_session(
    request: Request,
    session_data: ChatSessionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if session_data.document_id:
        result = await db.execute(
            select(Document).where(Document.id == session_data.document_id, Document.user_id == current_user.id)
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Document not found")

    if session_data.media_file_id:
        result = await db.execute(
            select(MediaFile).where(MediaFile.id == session_data.media_file_id, MediaFile.user_id == current_user.id)
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Media file not found")

    session = ChatSession(
        user_id=current_user.id,
        document_id=session_data.document_id,
        media_file_id=session_data.media_file_id,
        title=session_data.title,
    )
    db.add(session)
    await db.flush()
    await db.refresh(session)
    return ChatSessionOut(
        id=session.id,
        title=session.title,
        document_id=session.document_id,
        media_file_id=session.media_file_id,
        created_at=session.created_at,
        messages=[],
    )


@router.get("/sessions", response_model=list[ChatSessionOut])
@limiter.limit("60/minute")
async def list_sessions(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.user_id == current_user.id)
        .options(selectinload(ChatSession.messages))
        .order_by(ChatSession.created_at.desc())
    )
    sessions = result.scalars().all()
    return [ChatSessionOut.model_validate(s) for s in sessions]


@router.get("/sessions/{session_id}", response_model=ChatSessionOut)
@limiter.limit("60/minute")
async def get_session(
    request: Request,
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.id == session_id, ChatSession.user_id == current_user.id)
        .options(selectinload(ChatSession.messages))
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return ChatSessionOut.model_validate(session)


@router.post("/message", response_model=ChatResponse)
@limiter.limit("30/minute")
async def send_message(
    request: Request,
    chat_request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session_result = await db.execute(
        select(ChatSession)
        .where(ChatSession.id == chat_request.session_id, ChatSession.user_id == current_user.id)
        .options(selectinload(ChatSession.messages))
    )
    session = session_result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    history = [{"role": m.role, "content": m.content} for m in session.messages]

    # Save user message
    user_msg = ChatMessage(session_id=session.id, role="user", content=chat_request.message)
    db.add(user_msg)
    await db.flush()

    context_chunks = []
    relevant_timestamps = []
    segments = []

    # Vector search for documents
    if session.document_id:
        doc_result = await db.execute(select(Document).where(Document.id == session.document_id))
        document = doc_result.scalar_one_or_none()
        if document and document.vector_index_path:
            context_chunks = await vector_service.search(chat_request.message, document.vector_index_path, top_k=5)

    # Timestamp extraction for media
    if session.media_file_id:
        media_result = await db.execute(select(MediaFile).where(MediaFile.id == session.media_file_id))
        media_file = media_result.scalar_one_or_none()
        if media_file:
            segments = media_file.segments or []
            if segments:
                keywords = llm_service.extract_keywords(chat_request.message)
                relevant_segs = transcription_service.find_relevant_segments(segments, keywords, top_k=5)
                if media_file.vector_index_path and not relevant_segs:
                    vector_results = await vector_service.search(
                        chat_request.message, media_file.vector_index_path, top_k=5
                    )
                    context_chunks = vector_results
                relevant_timestamps = [
                    TimestampRef(
                        start=s["start"],
                        end=s["end"],
                        text=s["text"],
                        relevance_score=s.get("relevance_score", 1.0),
                    )
                    for s in relevant_segs
                ]

    answer = await llm_service.chat(
        message=chat_request.message,
        history=history,
        context_chunks=context_chunks if context_chunks else None,
        media_segments=segments if segments else None,
        relevant_segments=[t.model_dump() for t in relevant_timestamps] if relevant_timestamps else None,
    )

    ts_data = [t.model_dump() for t in relevant_timestamps] if relevant_timestamps else None
    assistant_msg = ChatMessage(
        session_id=session.id,
        role="assistant",
        content=answer,
        relevant_timestamps=ts_data,
    )
    db.add(assistant_msg)
    await db.flush()
    await db.refresh(assistant_msg)

    return ChatResponse(
        message=ChatMessageOut.model_validate(assistant_msg),
        relevant_timestamps=relevant_timestamps if relevant_timestamps else None,
    )


@router.post("/message/stream")
@limiter.limit("30/minute")
async def send_message_stream(
    request: Request,
    chat_request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session_result = await db.execute(
        select(ChatSession)
        .where(ChatSession.id == chat_request.session_id, ChatSession.user_id == current_user.id)
        .options(selectinload(ChatSession.messages))
    )
    session = session_result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    history = [{"role": m.role, "content": m.content} for m in session.messages]

    user_msg = ChatMessage(session_id=session.id, role="user", content=chat_request.message)
    db.add(user_msg)
    await db.flush()

    context_chunks = []
    relevant_timestamps = []
    segments = []

    if session.document_id:
        doc_result = await db.execute(select(Document).where(Document.id == session.document_id))
        document = doc_result.scalar_one_or_none()
        if document and document.vector_index_path:
            context_chunks = await vector_service.search(chat_request.message, document.vector_index_path, top_k=5)

    if session.media_file_id:
        media_result = await db.execute(select(MediaFile).where(MediaFile.id == session.media_file_id))
        media_file = media_result.scalar_one_or_none()
        if media_file:
            segments = media_file.segments or []
            if segments:
                keywords = llm_service.extract_keywords(chat_request.message)
                relevant_segs = transcription_service.find_relevant_segments(segments, keywords, top_k=5)
                relevant_timestamps = [
                    TimestampRef(start=s["start"], end=s["end"], text=s["text"], relevance_score=s.get("relevance_score", 1.0))
                    for s in relevant_segs
                ]

    async def generate():
        full_response = []
        # First yield timestamps metadata
        if relevant_timestamps:
            ts_data = [t.model_dump() for t in relevant_timestamps]
            yield f"data: {json.dumps({'type': 'timestamps', 'data': ts_data})}\n\n"

        async for chunk in llm_service.chat_stream(
            message=chat_request.message,
            history=history,
            context_chunks=context_chunks if context_chunks else None,
            media_segments=segments if segments else None,
            relevant_segments=[t.model_dump() for t in relevant_timestamps] if relevant_timestamps else None,
        ):
            full_response.append(chunk)
            yield f"data: {json.dumps({'type': 'content', 'data': chunk})}\n\n"

        # Save assistant message to DB
        full_text = "".join(full_response)
        ts_data = [t.model_dump() for t in relevant_timestamps] if relevant_timestamps else None
        assistant_msg = ChatMessage(
            session_id=session.id,
            role="assistant",
            content=full_text,
            relevant_timestamps=ts_data,
        )
        db.add(assistant_msg)
        await db.flush()
        await db.refresh(assistant_msg)
        await db.commit()

        yield f"data: {json.dumps({'type': 'done', 'message_id': assistant_msg.id})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("20/minute")
async def delete_session(
    request: Request,
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == current_user.id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    await db.delete(session)
