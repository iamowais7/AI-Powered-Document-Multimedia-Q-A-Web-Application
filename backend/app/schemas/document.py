from pydantic import BaseModel
from datetime import datetime


class DocumentOut(BaseModel):
    id: int
    filename: str
    original_filename: str
    file_size: int
    content_type: str
    extracted_text: str | None
    summary: str | None
    page_count: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentList(BaseModel):
    documents: list[DocumentOut]
    total: int
