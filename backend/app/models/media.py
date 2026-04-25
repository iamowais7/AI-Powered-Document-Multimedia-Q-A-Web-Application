from sqlalchemy import String, Text, Integer, Float, ForeignKey, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.database import Base


class MediaFile(Base):
    __tablename__ = "media_files"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    media_type: Mapped[str] = mapped_column(String(20), nullable=False)  # "audio" or "video"
    duration: Mapped[float | None] = mapped_column(Float, nullable=True)
    transcription: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Timestamped segments from transcription
    segments: Mapped[list | None] = mapped_column(JSON, nullable=True)
    vector_index_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    owner: Mapped["User"] = relationship("User", back_populates="media_files")
    chat_sessions: Mapped[list["ChatSession"]] = relationship("ChatSession", back_populates="media_file")
