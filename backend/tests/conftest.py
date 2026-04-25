import pytest
import asyncio
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from app.main import app
from app.database import Base, get_db
from app.core.security import hash_password, create_access_token
from app.models.user import User
from app.models.document import Document
from app.models.media import MediaFile
from app.models.chat import ChatSession, ChatMessage
import fakeredis.aioredis


TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = async_sessionmaker(test_engine, expire_on_commit=False)


@pytest.fixture(scope="session", autouse=True)
async def create_test_tables():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(autouse=True)
async def clean_tables():
    """Truncate all tables before each test."""
    async with test_engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())
    yield


@pytest.fixture(autouse=True)
def disable_rate_limiter():
    """Disable rate limiting in all tests."""
    from app.core.rate_limiter import limiter
    original = limiter.enabled
    limiter.enabled = False
    yield
    limiter.enabled = original


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with TestingSessionLocal() as session:
        yield session


@pytest.fixture
def fake_redis():
    return fakeredis.aioredis.FakeRedis(decode_responses=True)


@pytest.fixture
async def client(db_session: AsyncSession, fake_redis) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db_session

    from app.services.cache_service import cache_service
    cache_service._client = fake_redis

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    user = User(
        email="test@example.com",
        username="testuser",
        hashed_password=hash_password("password123"),
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def test_user2(db_session: AsyncSession) -> User:
    user = User(
        email="test2@example.com",
        username="testuser2",
        hashed_password=hash_password("password123"),
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user: User) -> dict:
    token = create_access_token({"sub": str(test_user.id), "email": test_user.email})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers2(test_user2: User) -> dict:
    token = create_access_token({"sub": str(test_user2.id), "email": test_user2.email})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def test_document(db_session: AsyncSession, test_user: User) -> Document:
    document = Document(
        user_id=test_user.id,
        filename="test.pdf",
        original_filename="test.pdf",
        file_path="/tmp/test.pdf",
        file_size=1024,
        content_type="application/pdf",
        extracted_text="This is test document content about machine learning.",
        summary="A test document about ML.",
        page_count=1,
    )
    db_session.add(document)
    await db_session.commit()
    await db_session.refresh(document)
    return document


@pytest.fixture
async def test_media(db_session: AsyncSession, test_user: User) -> MediaFile:
    media = MediaFile(
        user_id=test_user.id,
        filename="test.mp4",
        original_filename="test.mp4",
        file_path="/tmp/test.mp4",
        file_size=2048,
        content_type="video/mp4",
        media_type="video",
        duration=120.0,
        transcription="This is a test video about Python programming.",
        summary="A test video about Python.",
        segments=[
            {"start": 0.0, "end": 5.0, "text": "Hello and welcome to Python."},
            {"start": 5.0, "end": 10.0, "text": "Today we cover functions."},
            {"start": 10.0, "end": 15.0, "text": "Let us look at classes."},
        ],
    )
    db_session.add(media)
    await db_session.commit()
    await db_session.refresh(media)
    return media


@pytest.fixture
async def test_chat_session(db_session: AsyncSession, test_user: User, test_document: Document) -> ChatSession:
    session = ChatSession(
        user_id=test_user.id,
        document_id=test_document.id,
        title="Test Chat",
    )
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)
    return session