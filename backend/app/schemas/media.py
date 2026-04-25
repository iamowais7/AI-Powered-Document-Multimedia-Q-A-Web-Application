from pydantic import BaseModel
from datetime import datetime


class TranscriptSegment(BaseModel):
    start: float
    end: float
    text: str


class MediaFileOut(BaseModel):
    id: int
    filename: str
    original_filename: str
    file_size: int
    content_type: str
    media_type: str
    duration: float | None
    transcription: str | None
    summary: str | None
    segments: list[dict] | None
    created_at: datetime

    model_config = {"from_attributes": True}


class MediaFileList(BaseModel):
    media_files: list[MediaFileOut]
    total: int
