from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.user import User
from app.models.media import MediaFile
from app.schemas.media import MediaFileOut, MediaFileList
from app.core.security import get_current_user
from app.core.rate_limiter import limiter
from app.services.transcription_service import transcription_service
from app.services.vector_service import vector_service
from app.services.llm_service import llm_service
from app.services.pdf_service import pdf_service
from app.services.cache_service import cache_service
from app.config import settings

router = APIRouter(prefix="/media", tags=["Media"])

MAX_SIZE = settings.MAX_FILE_SIZE_MB * 1024 * 1024


@router.post("/upload", response_model=MediaFileOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def upload_media(
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    allowed = settings.ALLOWED_AUDIO_TYPES + settings.ALLOWED_VIDEO_TYPES
    if file.content_type not in allowed:
        raise HTTPException(status_code=400, detail="Only audio and video files are allowed")

    file_content = await file.read()
    if len(file_content) > MAX_SIZE:
        raise HTTPException(status_code=400, detail=f"File too large. Max {settings.MAX_FILE_SIZE_MB}MB")

    media_type = "audio" if file.content_type in settings.ALLOWED_AUDIO_TYPES else "video"
    filename, file_path = await transcription_service.save_file(file_content, file.filename)

    # Transcribe
    transcription_result = await transcription_service.transcribe(file_path)

    transcription_text = transcription_result.get("text", "")
    segments = transcription_result.get("segments", [])
    duration = transcription_result.get("duration", 0.0)

    # Build vector index from transcription
    vector_index_path = None
    if transcription_text:
        chunks = pdf_service.chunk_text(transcription_text, chunk_size=500, overlap=100)
        index_id = f"media_{current_user.id}_{filename.split('.')[0]}"
        vector_index_path = await vector_service.build_index(chunks, index_id)

    # Generate summary
    summary = None
    if transcription_text:
        summary = await llm_service.summarize(transcription_text)

    media_file = MediaFile(
        user_id=current_user.id,
        filename=filename,
        original_filename=file.filename,
        file_path=file_path,
        file_size=len(file_content),
        content_type=file.content_type,
        media_type=media_type,
        duration=duration,
        transcription=transcription_text,
        summary=summary,
        segments=segments,
        vector_index_path=vector_index_path,
    )
    db.add(media_file)
    await db.flush()
    await db.refresh(media_file)

    await cache_service.delete(cache_service.make_key("user_media", str(current_user.id)))
    return MediaFileOut.model_validate(media_file)


@router.get("/", response_model=MediaFileList)
@limiter.limit("60/minute")
async def list_media(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cache_key = cache_service.make_key("user_media", str(current_user.id))
    cached = await cache_service.get(cache_key)
    if cached:
        return cached

    result = await db.execute(
        select(MediaFile).where(MediaFile.user_id == current_user.id).order_by(MediaFile.created_at.desc())
    )
    media_files = result.scalars().all()
    response = MediaFileList(
        media_files=[MediaFileOut.model_validate(m) for m in media_files],
        total=len(media_files),
    )
    await cache_service.set(cache_key, response.model_dump(mode="json"), ttl=300)
    return response


@router.get("/{media_id}", response_model=MediaFileOut)
@limiter.limit("60/minute")
async def get_media(
    request: Request,
    media_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(MediaFile).where(MediaFile.id == media_id, MediaFile.user_id == current_user.id)
    )
    media_file = result.scalar_one_or_none()
    if not media_file:
        raise HTTPException(status_code=404, detail="Media file not found")
    return MediaFileOut.model_validate(media_file)


@router.delete("/{media_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("20/minute")
async def delete_media(
    request: Request,
    media_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(MediaFile).where(MediaFile.id == media_id, MediaFile.user_id == current_user.id)
    )
    media_file = result.scalar_one_or_none()
    if not media_file:
        raise HTTPException(status_code=404, detail="Media file not found")

    transcription_service.delete_file(media_file.file_path)
    if media_file.vector_index_path:
        vector_service.delete_index(media_file.vector_index_path)

    await db.delete(media_file)
    await cache_service.delete(cache_service.make_key("user_media", str(current_user.id)))
