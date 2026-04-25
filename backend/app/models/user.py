from sqlalchemy import String, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    documents: Mapped[list["Document"]] = relationship("Document", back_populates="owner", cascade="all, delete-orphan")
    media_files: Mapped[list["MediaFile"]] = relationship("MediaFile", back_populates="owner", cascade="all, delete-orphan")
    chat_sessions: Mapped[list["ChatSession"]] = relationship("ChatSession", back_populates="owner", cascade="all, delete-orphan")
