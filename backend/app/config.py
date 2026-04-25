from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # App
    APP_NAME: str = "DocQA API"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    SECRET_KEY: str = "change-me-in-production-use-long-random-string"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://docqa:docqa@db:5432/docqa"
    DATABASE_URL_SYNC: str = "postgresql://docqa:docqa@db:5432/docqa"

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"

    # AI APIs
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""

    # LLM
    LLM_MODEL: str = "claude-sonnet-4-6"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"

    # File Upload
    MAX_FILE_SIZE_MB: int = 100
    UPLOAD_DIR: str = "/tmp/uploads"
    ALLOWED_AUDIO_TYPES: list[str] = ["audio/mpeg", "audio/wav", "audio/ogg", "audio/mp4", "audio/webm"]
    ALLOWED_VIDEO_TYPES: list[str] = ["video/mp4", "video/mpeg", "video/webm", "video/quicktime"]
    ALLOWED_PDF_TYPES: list[str] = ["application/pdf"]

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
