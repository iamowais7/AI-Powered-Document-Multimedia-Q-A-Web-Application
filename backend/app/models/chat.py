from sqlalchemy import String, Text, Integer, ForeignKey, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.database import Base


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    document_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("documents.id"), nullable=True)
    media_file_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("media_files.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(255), default="New Chat")
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    owner: Mapped["User"] = relationship("User", back_populates="chat_sessions")
    document: Mapped["Document | None"] = relationship("Document", back_populates="chat_sessions")
    media_file: Mapped["MediaFile | None"] = relationship("MediaFile", back_populates="chat_sessions")
    messages: Mapped[list["ChatMessage"]] = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan", order_by="ChatMessage.created_at")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(Integer, ForeignKey("chat_sessions.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # "user" or "assistant"
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # Timestamps found relevant to the answer (for media files)
    relevant_timestamps: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    session: Mapped["ChatSession"] = relationship("ChatSession", back_populates="messages")
