import os
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.user import User
from app.models.document import Document
from app.schemas.document import DocumentOut, DocumentList
from app.core.security import get_current_user
from app.core.rate_limiter import limiter
from app.services.pdf_service import pdf_service
from app.services.vector_service import vector_service
from app.services.llm_service import llm_service
from app.services.cache_service import cache_service
from app.config import settings

router = APIRouter(prefix="/documents", tags=["Documents"])

MAX_SIZE = settings.MAX_FILE_SIZE_MB * 1024 * 1024


@router.post("/upload", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute")
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if file.content_type not in settings.ALLOWED_PDF_TYPES:
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    file_content = await file.read()
    if len(file_content) > MAX_SIZE:
        raise HTTPException(status_code=400, detail=f"File too large. Max {settings.MAX_FILE_SIZE_MB}MB")

    filename, file_path = await pdf_service.save_file(file_content, file.filename)
    extracted_text, page_count = pdf_service.extract_text(file_path)

    # Build vector index
    vector_index_path = None
    if extracted_text:
        chunks = pdf_service.chunk_text(extracted_text)
        index_id = f"doc_{current_user.id}_{filename.split('.')[0]}"
        vector_index_path = await vector_service.build_index(chunks, index_id)

    # Generate summary
    summary = None
    if extracted_text:
        summary = await llm_service.summarize(extracted_text)

    document = Document(
        user_id=current_user.id,
        filename=filename,
        original_filename=file.filename,
        file_path=file_path,
        file_size=len(file_content),
        content_type=file.content_type,
        extracted_text=extracted_text,
        summary=summary,
        page_count=page_count,
        vector_index_path=vector_index_path,
    )
    db.add(document)
    await db.flush()
    await db.refresh(document)

    await cache_service.delete(cache_service.make_key("user_docs", str(current_user.id)))
    return DocumentOut.model_validate(document)


@router.get("/", response_model=DocumentList)
@limiter.limit("60/minute")
async def list_documents(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cache_key = cache_service.make_key("user_docs", str(current_user.id))
    cached = await cache_service.get(cache_key)
    if cached:
        return cached

    result = await db.execute(
        select(Document).where(Document.user_id == current_user.id).order_by(Document.created_at.desc())
    )
    documents = result.scalars().all()
    response = DocumentList(
        documents=[DocumentOut.model_validate(d) for d in documents],
        total=len(documents),
    )
    await cache_service.set(cache_key, response.model_dump(mode="json"), ttl=300)
    return response


@router.get("/{document_id}", response_model=DocumentOut)
@limiter.limit("60/minute")
async def get_document(
    request: Request,
    document_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Document).where(Document.id == document_id, Document.user_id == current_user.id)
    )
    document = result.scalar_one_or_none()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentOut.model_validate(document)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("20/minute")
async def delete_document(
    request: Request,
    document_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Document).where(Document.id == document_id, Document.user_id == current_user.id)
    )
    document = result.scalar_one_or_none()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    pdf_service.delete_file(document.file_path)
    if document.vector_index_path:
        vector_service.delete_index(document.vector_index_path)

    await db.delete(document)
    await cache_service.delete(cache_service.make_key("user_docs", str(current_user.id)))
