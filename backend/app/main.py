from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.config import settings
from app.database import create_tables
from app.core.rate_limiter import limiter
from app.api.v1 import auth, documents, media, chat
from app.core.security import get_current_user
from app.schemas.user import UserOut
from fastapi import Depends


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="AI-Powered Document & Multimedia Q&A API",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(auth.router, prefix="/api/v1")
app.include_router(documents.router, prefix="/api/v1")
app.include_router(media.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok", "version": settings.VERSION}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
