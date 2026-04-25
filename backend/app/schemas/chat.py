from pydantic import BaseModel
from datetime import datetime


class ChatSessionCreate(BaseModel):
    document_id: int | None = None
    media_file_id: int | None = None
    title: str = "New Chat"


class ChatRequest(BaseModel):
    session_id: int
    message: str
    stream: bool = True


class TimestampRef(BaseModel):
    start: float
    end: float
    text: str
    relevance_score: float = 1.0


class ChatMessageOut(BaseModel):
    id: int
    session_id: int
    role: str
    content: str
    relevant_timestamps: list[dict] | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatSessionOut(BaseModel):
    id: int
    title: str
    document_id: int | None
    media_file_id: int | None
    created_at: datetime
    messages: list[ChatMessageOut] = []

    model_config = {"from_attributes": True}


class ChatResponse(BaseModel):
    message: ChatMessageOut
    relevant_timestamps: list[TimestampRef] | None = None
