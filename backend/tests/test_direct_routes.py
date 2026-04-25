"""Direct route handler tests calling __wrapped__ to bypass the slowapi decorator
and ensure coverage tracking works correctly in Python 3.13."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException
from app.models.user import User
from app.models.document import Document
from app.models.media import MediaFile
from app.models.chat import ChatSession
from app.core.security import hash_password
from app.schemas.user import UserCreate, UserLogin
from app.schemas.chat import ChatSessionCreate, ChatRequest

pytestmark = pytest.mark.asyncio


# ── AUTH ──────────────────────────────────────────────────────────────────────

async def test_register_direct_success(db_session: AsyncSession):
    from app.api.v1.auth import register
    request = MagicMock()
    user_data = UserCreate(email="dr1@test.com", username="druser1", password="password123")
    result = await register.__wrapped__(request=request, user_data=user_data, db=db_session)
    assert result.access_token is not None
    assert result.user.email == "dr1@test.com"


async def test_register_direct_duplicate_email(db_session: AsyncSession, test_user: User):
    from app.api.v1.auth import register
    request = MagicMock()
    user_data = UserCreate(email=test_user.email, username="uniquedr2", password="password123")
    with pytest.raises(HTTPException) as exc:
        await register.__wrapped__(request=request, user_data=user_data, db=db_session)
    assert exc.value.status_code == 400
    assert "Email" in exc.value.detail


async def test_register_direct_duplicate_username(db_session: AsyncSession, test_user: User):
    from app.api.v1.auth import register
    request = MagicMock()
    user_data = UserCreate(email="unique_dr3@test.com", username=test_user.username, password="password123")
    with pytest.raises(HTTPException) as exc:
        await register.__wrapped__(request=request, user_data=user_data, db=db_session)
    assert exc.value.status_code == 400
    assert "Username" in exc.value.detail


async def test_login_direct_success(db_session: AsyncSession, test_user: User):
    from app.api.v1.auth import login
    request = MagicMock()
    credentials = UserLogin(email=test_user.email, password="password123")
    result = await login.__wrapped__(request=request, credentials=credentials, db=db_session)
    assert result.access_token is not None
    assert result.user.email == test_user.email


async def test_login_direct_invalid_password(db_session: AsyncSession, test_user: User):
    from app.api.v1.auth import login
    request = MagicMock()
    credentials = UserLogin(email=test_user.email, password="wrongpassword")
    with pytest.raises(HTTPException) as exc:
        await login.__wrapped__(request=request, credentials=credentials, db=db_session)
    assert exc.value.status_code == 401


async def test_login_direct_inactive_user(db_session: AsyncSession):
    from app.api.v1.auth import login
    user = User(
        email="inactive_dr@test.com", username="inactivedr",
        hashed_password=hash_password("password123"), is_active=False,
    )
    db_session.add(user)
    await db_session.commit()
    request = MagicMock()
    credentials = UserLogin(email="inactive_dr@test.com", password="password123")
    with pytest.raises(HTTPException) as exc:
        await login.__wrapped__(request=request, credentials=credentials, db=db_session)
    assert exc.value.status_code == 403


# ── DOCUMENTS ─────────────────────────────────────────────────────────────────

async def test_upload_document_direct(db_session: AsyncSession, test_user: User):
    from app.api.v1.documents import upload_document
    with patch("app.api.v1.documents.pdf_service") as mock_pdf, \
         patch("app.api.v1.documents.vector_service") as mock_vs, \
         patch("app.api.v1.documents.llm_service") as mock_llm, \
         patch("app.api.v1.documents.cache_service") as mock_cache:
        mock_pdf.save_file = AsyncMock(return_value=("dr_test.pdf", "/tmp/dr_test.pdf"))
        mock_pdf.extract_text = MagicMock(return_value=("text content", 2))
        mock_pdf.chunk_text = MagicMock(return_value=["chunk1", "chunk2"])
        mock_vs.build_index = AsyncMock(return_value="/tmp/dr_index")
        mock_llm.summarize = AsyncMock(return_value="A test summary.")
        mock_cache.delete = AsyncMock()
        mock_cache.make_key = MagicMock(return_value="key")
        file_mock = MagicMock()
        file_mock.content_type = "application/pdf"
        file_mock.filename = "dr_test.pdf"
        file_mock.read = AsyncMock(return_value=b"%PDF fake content")
        request = MagicMock()
        result = await upload_document.__wrapped__(
            request=request, file=file_mock, db=db_session, current_user=test_user
        )
    assert result.original_filename == "dr_test.pdf"
    assert result.summary == "A test summary."


async def test_upload_document_direct_no_text(db_session: AsyncSession, test_user: User):
    from app.api.v1.documents import upload_document
    with patch("app.api.v1.documents.pdf_service") as mock_pdf, \
         patch("app.api.v1.documents.vector_service") as mock_vs, \
         patch("app.api.v1.documents.llm_service") as mock_llm, \
         patch("app.api.v1.documents.cache_service") as mock_cache:
        mock_pdf.save_file = AsyncMock(return_value=("empty.pdf", "/tmp/empty.pdf"))
        mock_pdf.extract_text = MagicMock(return_value=("", 0))
        mock_pdf.chunk_text = MagicMock(return_value=[])
        mock_vs.build_index = AsyncMock(return_value=None)
        mock_llm.summarize = AsyncMock(return_value=None)
        mock_cache.delete = AsyncMock()
        mock_cache.make_key = MagicMock(return_value="key")
        file_mock = MagicMock()
        file_mock.content_type = "application/pdf"
        file_mock.filename = "empty.pdf"
        file_mock.read = AsyncMock(return_value=b"%PDF empty")
        request = MagicMock()
        result = await upload_document.__wrapped__(
            request=request, file=file_mock, db=db_session, current_user=test_user
        )
    assert result.summary is None


async def test_list_documents_direct_cache_miss(db_session: AsyncSession, test_user: User, test_document: Document):
    from app.api.v1.documents import list_documents
    with patch("app.api.v1.documents.cache_service") as mock_cache:
        mock_cache.make_key = MagicMock(return_value="docs_key")
        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock()
        request = MagicMock()
        result = await list_documents.__wrapped__(request=request, db=db_session, current_user=test_user)
    assert result.total >= 1


async def test_get_document_direct_success(db_session: AsyncSession, test_user: User, test_document: Document):
    from app.api.v1.documents import get_document
    request = MagicMock()
    result = await get_document.__wrapped__(
        request=request, document_id=test_document.id, db=db_session, current_user=test_user
    )
    assert result.id == test_document.id


async def test_get_document_direct_not_found(db_session: AsyncSession, test_user: User):
    from app.api.v1.documents import get_document
    request = MagicMock()
    with pytest.raises(HTTPException) as exc:
        await get_document.__wrapped__(
            request=request, document_id=99999, db=db_session, current_user=test_user
        )
    assert exc.value.status_code == 404


async def test_delete_document_direct_success(db_session: AsyncSession, test_user: User, test_document: Document):
    from app.api.v1.documents import delete_document
    with patch("app.api.v1.documents.pdf_service") as mock_pdf, \
         patch("app.api.v1.documents.vector_service") as mock_vs, \
         patch("app.api.v1.documents.cache_service") as mock_cache:
        mock_pdf.delete_file = MagicMock()
        mock_vs.delete_index = MagicMock()
        mock_cache.make_key = MagicMock(return_value="key")
        mock_cache.delete = AsyncMock()
        request = MagicMock()
        await delete_document.__wrapped__(
            request=request, document_id=test_document.id, db=db_session, current_user=test_user
        )


async def test_delete_document_direct_not_found(db_session: AsyncSession, test_user: User):
    from app.api.v1.documents import delete_document
    request = MagicMock()
    with pytest.raises(HTTPException) as exc:
        await delete_document.__wrapped__(
            request=request, document_id=99999, db=db_session, current_user=test_user
        )
    assert exc.value.status_code == 404


async def test_delete_document_direct_with_vector(db_session: AsyncSession, test_user: User):
    from app.api.v1.documents import delete_document
    from app.models.document import Document as DocModel
    doc = DocModel(
        user_id=test_user.id, filename="vec.pdf", original_filename="vec.pdf",
        file_path="/tmp/vec.pdf", file_size=100, content_type="application/pdf",
        vector_index_path="/tmp/vec_index",
    )
    db_session.add(doc)
    await db_session.commit()
    await db_session.refresh(doc)
    with patch("app.api.v1.documents.pdf_service") as mock_pdf, \
         patch("app.api.v1.documents.vector_service") as mock_vs, \
         patch("app.api.v1.documents.cache_service") as mock_cache:
        mock_pdf.delete_file = MagicMock()
        mock_vs.delete_index = MagicMock()
        mock_cache.make_key = MagicMock(return_value="key")
        mock_cache.delete = AsyncMock()
        request = MagicMock()
        await delete_document.__wrapped__(
            request=request, document_id=doc.id, db=db_session, current_user=test_user
        )
    mock_vs.delete_index.assert_called_once_with("/tmp/vec_index")


# ── MEDIA ─────────────────────────────────────────────────────────────────────

async def test_upload_media_direct(db_session: AsyncSession, test_user: User):
    from app.api.v1.media import upload_media
    with patch("app.api.v1.media.transcription_service") as mock_ts, \
         patch("app.api.v1.media.vector_service") as mock_vs, \
         patch("app.api.v1.media.llm_service") as mock_llm, \
         patch("app.api.v1.media.pdf_service") as mock_pdf, \
         patch("app.api.v1.media.cache_service") as mock_cache:
        mock_ts.save_file = AsyncMock(return_value=("dr_audio.mp3", "/tmp/dr_audio.mp3"))
        mock_ts.transcribe = AsyncMock(return_value={
            "text": "Hello world transcript", "segments": [], "duration": 10.0
        })
        mock_pdf.chunk_text = MagicMock(return_value=["chunk"])
        mock_vs.build_index = AsyncMock(return_value="/tmp/dr_media_index")
        mock_llm.summarize = AsyncMock(return_value="Audio summary.")
        mock_cache.delete = AsyncMock()
        mock_cache.make_key = MagicMock(return_value="key")
        file_mock = MagicMock()
        file_mock.content_type = "audio/mpeg"
        file_mock.filename = "dr_audio.mp3"
        file_mock.read = AsyncMock(return_value=b"fake audio bytes")
        request = MagicMock()
        result = await upload_media.__wrapped__(
            request=request, file=file_mock, db=db_session, current_user=test_user
        )
    assert result.media_type == "audio"
    assert result.transcription == "Hello world transcript"


async def test_upload_media_direct_video(db_session: AsyncSession, test_user: User):
    from app.api.v1.media import upload_media
    with patch("app.api.v1.media.transcription_service") as mock_ts, \
         patch("app.api.v1.media.vector_service") as mock_vs, \
         patch("app.api.v1.media.llm_service") as mock_llm, \
         patch("app.api.v1.media.pdf_service") as mock_pdf, \
         patch("app.api.v1.media.cache_service") as mock_cache:
        mock_ts.save_file = AsyncMock(return_value=("dr_video.mp4", "/tmp/dr_video.mp4"))
        mock_ts.transcribe = AsyncMock(return_value={"text": "", "segments": [], "duration": 30.0})
        mock_pdf.chunk_text = MagicMock(return_value=[])
        mock_vs.build_index = AsyncMock(return_value=None)
        mock_llm.summarize = AsyncMock(return_value=None)
        mock_cache.delete = AsyncMock()
        mock_cache.make_key = MagicMock(return_value="key")
        file_mock = MagicMock()
        file_mock.content_type = "video/mp4"
        file_mock.filename = "dr_video.mp4"
        file_mock.read = AsyncMock(return_value=b"fake video bytes")
        request = MagicMock()
        result = await upload_media.__wrapped__(
            request=request, file=file_mock, db=db_session, current_user=test_user
        )
    assert result.media_type == "video"


async def test_list_media_direct_cache_miss(db_session: AsyncSession, test_user: User, test_media: MediaFile):
    from app.api.v1.media import list_media
    with patch("app.api.v1.media.cache_service") as mock_cache:
        mock_cache.make_key = MagicMock(return_value="media_key")
        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock()
        request = MagicMock()
        result = await list_media.__wrapped__(request=request, db=db_session, current_user=test_user)
    assert result.total >= 1


async def test_get_media_direct_success(db_session: AsyncSession, test_user: User, test_media: MediaFile):
    from app.api.v1.media import get_media
    request = MagicMock()
    result = await get_media.__wrapped__(
        request=request, media_id=test_media.id, db=db_session, current_user=test_user
    )
    assert result.id == test_media.id


async def test_get_media_direct_not_found(db_session: AsyncSession, test_user: User):
    from app.api.v1.media import get_media
    request = MagicMock()
    with pytest.raises(HTTPException) as exc:
        await get_media.__wrapped__(
            request=request, media_id=99999, db=db_session, current_user=test_user
        )
    assert exc.value.status_code == 404


async def test_delete_media_direct_success(db_session: AsyncSession, test_user: User, test_media: MediaFile):
    from app.api.v1.media import delete_media
    with patch("app.api.v1.media.transcription_service") as mock_ts, \
         patch("app.api.v1.media.vector_service") as mock_vs, \
         patch("app.api.v1.media.cache_service") as mock_cache:
        mock_ts.delete_file = MagicMock()
        mock_vs.delete_index = MagicMock()
        mock_cache.make_key = MagicMock(return_value="key")
        mock_cache.delete = AsyncMock()
        request = MagicMock()
        await delete_media.__wrapped__(
            request=request, media_id=test_media.id, db=db_session, current_user=test_user
        )


async def test_delete_media_direct_not_found(db_session: AsyncSession, test_user: User):
    from app.api.v1.media import delete_media
    request = MagicMock()
    with pytest.raises(HTTPException) as exc:
        await delete_media.__wrapped__(
            request=request, media_id=99999, db=db_session, current_user=test_user
        )
    assert exc.value.status_code == 404


async def test_delete_media_direct_with_vector(db_session: AsyncSession, test_user: User):
    from app.api.v1.media import delete_media
    from app.models.media import MediaFile as MF
    media = MF(
        user_id=test_user.id, filename="vec_m.mp3", original_filename="vec_m.mp3",
        file_path="/tmp/vec_m.mp3", file_size=100, content_type="audio/mpeg",
        media_type="audio", vector_index_path="/tmp/media_vec_index",
    )
    db_session.add(media)
    await db_session.commit()
    await db_session.refresh(media)
    with patch("app.api.v1.media.transcription_service") as mock_ts, \
         patch("app.api.v1.media.vector_service") as mock_vs, \
         patch("app.api.v1.media.cache_service") as mock_cache:
        mock_ts.delete_file = MagicMock()
        mock_vs.delete_index = MagicMock()
        mock_cache.make_key = MagicMock(return_value="key")
        mock_cache.delete = AsyncMock()
        request = MagicMock()
        await delete_media.__wrapped__(
            request=request, media_id=media.id, db=db_session, current_user=test_user
        )
    mock_vs.delete_index.assert_called_once_with("/tmp/media_vec_index")


# ── CHAT ──────────────────────────────────────────────────────────────────────

async def test_create_session_direct_with_document(
    db_session: AsyncSession, test_user: User, test_document: Document
):
    from app.api.v1.chat import create_session
    request = MagicMock()
    session_data = ChatSessionCreate(document_id=test_document.id, title="Direct Doc Chat")
    result = await create_session.__wrapped__(
        request=request, session_data=session_data, db=db_session, current_user=test_user
    )
    assert result.document_id == test_document.id
    assert result.title == "Direct Doc Chat"


async def test_create_session_direct_with_media(
    db_session: AsyncSession, test_user: User, test_media: MediaFile
):
    from app.api.v1.chat import create_session
    request = MagicMock()
    session_data = ChatSessionCreate(media_file_id=test_media.id, title="Direct Media Chat")
    result = await create_session.__wrapped__(
        request=request, session_data=session_data, db=db_session, current_user=test_user
    )
    assert result.media_file_id == test_media.id


async def test_create_session_direct_no_resource(db_session: AsyncSession, test_user: User):
    from app.api.v1.chat import create_session
    request = MagicMock()
    session_data = ChatSessionCreate(title="General Direct")
    result = await create_session.__wrapped__(
        request=request, session_data=session_data, db=db_session, current_user=test_user
    )
    assert result.title == "General Direct"


async def test_create_session_direct_invalid_document(db_session: AsyncSession, test_user: User):
    from app.api.v1.chat import create_session
    request = MagicMock()
    session_data = ChatSessionCreate(document_id=99999)
    with pytest.raises(HTTPException) as exc:
        await create_session.__wrapped__(
            request=request, session_data=session_data, db=db_session, current_user=test_user
        )
    assert exc.value.status_code == 404


async def test_create_session_direct_invalid_media(db_session: AsyncSession, test_user: User):
    from app.api.v1.chat import create_session
    request = MagicMock()
    session_data = ChatSessionCreate(media_file_id=99999)
    with pytest.raises(HTTPException) as exc:
        await create_session.__wrapped__(
            request=request, session_data=session_data, db=db_session, current_user=test_user
        )
    assert exc.value.status_code == 404


async def test_list_sessions_direct(
    db_session: AsyncSession, test_user: User, test_chat_session: ChatSession
):
    from app.api.v1.chat import list_sessions
    request = MagicMock()
    result = await list_sessions.__wrapped__(request=request, db=db_session, current_user=test_user)
    assert len(result) >= 1


async def test_get_session_direct_success(
    db_session: AsyncSession, test_user: User, test_chat_session: ChatSession
):
    from app.api.v1.chat import get_session
    request = MagicMock()
    result = await get_session.__wrapped__(
        request=request, session_id=test_chat_session.id, db=db_session, current_user=test_user
    )
    assert result.id == test_chat_session.id


async def test_get_session_direct_not_found(db_session: AsyncSession, test_user: User):
    from app.api.v1.chat import get_session
    request = MagicMock()
    with pytest.raises(HTTPException) as exc:
        await get_session.__wrapped__(
            request=request, session_id=99999, db=db_session, current_user=test_user
        )
    assert exc.value.status_code == 404


async def test_send_message_direct_basic(
    db_session: AsyncSession, test_user: User, test_chat_session: ChatSession
):
    from app.api.v1.chat import send_message
    with patch("app.api.v1.chat.vector_service") as mock_vs, \
         patch("app.api.v1.chat.llm_service") as mock_llm:
        mock_vs.search = AsyncMock(return_value=[])
        mock_llm.chat = AsyncMock(return_value="Direct AI answer")
        mock_llm.extract_keywords = MagicMock(return_value=[])
        chat_req = ChatRequest(session_id=test_chat_session.id, message="Hello direct", stream=False)
        request = MagicMock()
        result = await send_message.__wrapped__(
            request=request, chat_request=chat_req, db=db_session, current_user=test_user
        )
    assert result.message.content == "Direct AI answer"
    assert result.message.role == "assistant"


async def test_send_message_direct_not_found(db_session: AsyncSession, test_user: User):
    from app.api.v1.chat import send_message
    chat_req = ChatRequest(session_id=99999, message="Hello", stream=False)
    request = MagicMock()
    with pytest.raises(HTTPException) as exc:
        await send_message.__wrapped__(
            request=request, chat_request=chat_req, db=db_session, current_user=test_user
        )
    assert exc.value.status_code == 404


async def test_send_message_direct_with_document(
    db_session: AsyncSession, test_user: User, test_document: Document
):
    from app.api.v1.chat import create_session, send_message
    request = MagicMock()
    # Update test_document to have a vector_index_path
    result = await db_session.execute(
        select(Document).where(Document.id == test_document.id)
    )
    doc = result.scalar_one()
    doc.vector_index_path = "/tmp/dr_doc_index"
    await db_session.flush()

    session_data = ChatSessionCreate(document_id=test_document.id, title="DocDirect")
    session = await create_session.__wrapped__(
        request=request, session_data=session_data, db=db_session, current_user=test_user
    )
    with patch("app.api.v1.chat.vector_service") as mock_vs, \
         patch("app.api.v1.chat.llm_service") as mock_llm:
        mock_vs.search = AsyncMock(return_value=[{"text": "relevant chunk", "score": 0.9}])
        mock_llm.chat = AsyncMock(return_value="Document-based answer")
        mock_llm.extract_keywords = MagicMock(return_value=["test"])
        chat_req = ChatRequest(session_id=session.id, message="What is this?", stream=False)
        result = await send_message.__wrapped__(
            request=request, chat_request=chat_req, db=db_session, current_user=test_user
        )
    assert result.message.content == "Document-based answer"


async def test_send_message_direct_with_media_segments(
    db_session: AsyncSession, test_user: User, test_media: MediaFile
):
    from app.api.v1.chat import create_session, send_message
    request = MagicMock()
    session_data = ChatSessionCreate(media_file_id=test_media.id, title="MediaDirect")
    session = await create_session.__wrapped__(
        request=request, session_data=session_data, db=db_session, current_user=test_user
    )
    with patch("app.api.v1.chat.vector_service") as mock_vs, \
         patch("app.api.v1.chat.llm_service") as mock_llm, \
         patch("app.api.v1.chat.transcription_service") as mock_ts:
        mock_vs.search = AsyncMock(return_value=[])
        mock_llm.chat = AsyncMock(return_value="Media-based answer")
        mock_llm.extract_keywords = MagicMock(return_value=["python"])
        mock_ts.find_relevant_segments = MagicMock(return_value=[
            {"start": 5.0, "end": 10.0, "text": "Python functions", "relevance_score": 2.0}
        ])
        chat_req = ChatRequest(session_id=session.id, message="Python?", stream=False)
        result = await send_message.__wrapped__(
            request=request, chat_request=chat_req, db=db_session, current_user=test_user
        )
    assert result.relevant_timestamps is not None
    assert len(result.relevant_timestamps) > 0


async def test_send_message_direct_media_vector_fallback(
    db_session: AsyncSession, test_user: User, test_media: MediaFile
):
    from app.api.v1.chat import create_session, send_message
    from app.models.media import MediaFile as MF
    # Give media a vector_index_path
    result = await db_session.execute(select(MF).where(MF.id == test_media.id))
    media = result.scalar_one()
    media.vector_index_path = "/tmp/media_idx"
    await db_session.flush()
    request = MagicMock()
    session_data = ChatSessionCreate(media_file_id=test_media.id, title="MediaVec")
    session = await create_session.__wrapped__(
        request=request, session_data=session_data, db=db_session, current_user=test_user
    )
    with patch("app.api.v1.chat.vector_service") as mock_vs, \
         patch("app.api.v1.chat.llm_service") as mock_llm, \
         patch("app.api.v1.chat.transcription_service") as mock_ts:
        mock_vs.search = AsyncMock(return_value=[{"text": "vec chunk", "score": 0.8}])
        mock_llm.chat = AsyncMock(return_value="Vector fallback answer")
        mock_llm.extract_keywords = MagicMock(return_value=["hello"])
        # Return empty relevant segs → triggers vector fallback
        mock_ts.find_relevant_segments = MagicMock(return_value=[])
        chat_req = ChatRequest(session_id=session.id, message="Hello?", stream=False)
        result = await send_message.__wrapped__(
            request=request, chat_request=chat_req, db=db_session, current_user=test_user
        )
    assert result.message.content == "Vector fallback answer"


async def test_send_message_stream_direct(
    db_session: AsyncSession, test_user: User, test_chat_session: ChatSession
):
    from app.api.v1.chat import send_message_stream

    async def mock_stream(*args, **kwargs):
        for chunk in ["Hello", " world", "!"]:
            yield chunk

    with patch("app.api.v1.chat.vector_service") as mock_vs, \
         patch("app.api.v1.chat.llm_service") as mock_llm:
        mock_vs.search = AsyncMock(return_value=[])
        mock_llm.extract_keywords = MagicMock(return_value=[])
        mock_llm.chat_stream = mock_stream
        chat_req = ChatRequest(session_id=test_chat_session.id, message="Stream direct", stream=True)
        request = MagicMock()
        response = await send_message_stream.__wrapped__(
            request=request, chat_request=chat_req, db=db_session, current_user=test_user
        )
        # Consume inside patch context so the generator uses the mock
        chunks = []
        async for chunk in response.body_iterator:
            chunks.append(chunk)
    content = "".join(chunks)
    assert "data:" in content
    assert "done" in content


async def test_send_message_stream_direct_with_media(
    db_session: AsyncSession, test_user: User, test_media: MediaFile
):
    from app.api.v1.chat import create_session, send_message_stream

    request = MagicMock()
    session_data = ChatSessionCreate(media_file_id=test_media.id, title="StreamMedia")
    session = await create_session.__wrapped__(
        request=request, session_data=session_data, db=db_session, current_user=test_user
    )

    async def mock_stream(*args, **kwargs):
        yield "Media chunk"

    with patch("app.api.v1.chat.vector_service") as mock_vs, \
         patch("app.api.v1.chat.llm_service") as mock_llm, \
         patch("app.api.v1.chat.transcription_service") as mock_ts:
        mock_vs.search = AsyncMock(return_value=[])
        mock_llm.extract_keywords = MagicMock(return_value=["python"])
        mock_llm.chat_stream = mock_stream
        mock_ts.find_relevant_segments = MagicMock(return_value=[
            {"start": 0.0, "end": 5.0, "text": "Hello Python", "relevance_score": 1.5}
        ])
        chat_req = ChatRequest(session_id=session.id, message="Python?", stream=True)
        response = await send_message_stream.__wrapped__(
            request=request, chat_request=chat_req, db=db_session, current_user=test_user
        )
        # Consume inside patch context
        chunks = []
        async for chunk in response.body_iterator:
            chunks.append(chunk)
    content = "".join(chunks)
    assert "timestamps" in content


async def test_send_message_stream_direct_not_found(db_session: AsyncSession, test_user: User):
    from app.api.v1.chat import send_message_stream
    chat_req = ChatRequest(session_id=99999, message="Stream?", stream=True)
    request = MagicMock()
    with pytest.raises(HTTPException) as exc:
        await send_message_stream.__wrapped__(
            request=request, chat_request=chat_req, db=db_session, current_user=test_user
        )
    assert exc.value.status_code == 404


async def test_delete_session_direct_success(
    db_session: AsyncSession, test_user: User, test_document: Document
):
    from app.api.v1.chat import create_session, delete_session
    request = MagicMock()
    session_data = ChatSessionCreate(document_id=test_document.id, title="Delete Direct")
    session = await create_session.__wrapped__(
        request=request, session_data=session_data, db=db_session, current_user=test_user
    )
    await delete_session.__wrapped__(
        request=request, session_id=session.id, db=db_session, current_user=test_user
    )


async def test_delete_session_direct_not_found(db_session: AsyncSession, test_user: User):
    from app.api.v1.chat import delete_session
    request = MagicMock()
    with pytest.raises(HTTPException) as exc:
        await delete_session.__wrapped__(
            request=request, session_id=99999, db=db_session, current_user=test_user
        )
    assert exc.value.status_code == 404


# ── DATABASE ──────────────────────────────────────────────────────────────────

async def test_get_db_success():
    from app.database import get_db
    with patch("app.database.AsyncSessionLocal") as mock_factory:
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()
        mock_session.close = AsyncMock()
        mock_factory.return_value = mock_session

        gen = get_db()
        session = await gen.__anext__()
        assert session is mock_session
        # Send None to complete the generator normally (triggers commit path)
        try:
            await gen.asend(None)
        except StopAsyncIteration:
            pass
        mock_session.commit.assert_called_once()


async def test_get_db_exception_path():
    from app.database import get_db
    with patch("app.database.AsyncSessionLocal") as mock_factory:
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.commit = AsyncMock(side_effect=Exception("DB error"))
        mock_session.rollback = AsyncMock()
        mock_session.close = AsyncMock()
        mock_factory.return_value = mock_session

        gen = get_db()
        session = await gen.__anext__()
        assert session is mock_session
        try:
            await gen.asend(None)
        except (StopAsyncIteration, Exception):
            pass
        mock_session.rollback.assert_called_once()


async def test_create_tables_direct():
    from app.database import create_tables
    with patch("app.database.engine") as mock_engine:
        mock_conn = AsyncMock()
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=None)
        mock_conn.run_sync = AsyncMock()
        mock_engine.begin = MagicMock(return_value=mock_conn)
        await create_tables()
    mock_conn.run_sync.assert_called_once()


# ── MAIN ──────────────────────────────────────────────────────────────────────

async def test_global_exception_handler():
    from app.main import global_exception_handler
    request = MagicMock()
    exc = Exception("test error")
    response = await global_exception_handler(request, exc)
    assert response.status_code == 500


async def test_lifespan_create_tables():
    from app.main import lifespan
    with patch("app.main.create_tables", new_callable=AsyncMock) as mock_ct:
        app_mock = MagicMock()
        async with lifespan(app_mock):
            pass
        mock_ct.assert_called_once()


# ── EXTRA COVERAGE FOR REMAINING GAPS ────────────────────────────────────────

async def test_upload_media_direct_too_large(db_session: AsyncSession, test_user: User):
    from app.api.v1.media import upload_media
    import app.api.v1.media as media_module
    original = media_module.MAX_SIZE
    media_module.MAX_SIZE = 5  # 5 bytes
    try:
        file_mock = MagicMock()
        file_mock.content_type = "audio/mpeg"
        file_mock.filename = "big.mp3"
        file_mock.read = AsyncMock(return_value=b"this is too large content")
        request = MagicMock()
        with pytest.raises(HTTPException) as exc:
            await upload_media.__wrapped__(
                request=request, file=file_mock, db=db_session, current_user=test_user
            )
        assert exc.value.status_code == 400
        assert "too large" in exc.value.detail
    finally:
        media_module.MAX_SIZE = original


async def test_list_media_direct_with_db(db_session: AsyncSession, test_user: User, test_media: MediaFile):
    from app.api.v1.media import list_media
    from app.services.cache_service import CacheService
    import fakeredis.aioredis
    # Use real fake cache that returns None on get
    svc = CacheService()
    svc._client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    with patch("app.api.v1.media.cache_service", svc):
        request = MagicMock()
        result = await list_media.__wrapped__(request=request, db=db_session, current_user=test_user)
    assert result.total >= 1


async def test_send_message_stream_with_document_vector(
    db_session: AsyncSession, test_user: User, test_document: Document
):
    from app.api.v1.chat import create_session, send_message_stream
    from app.models.document import Document as Doc
    # Give test_document a vector_index_path
    result = await db_session.execute(select(Doc).where(Doc.id == test_document.id))
    doc = result.scalar_one()
    doc.vector_index_path = "/tmp/stream_doc_idx"
    await db_session.flush()
    request = MagicMock()
    session_data = ChatSessionCreate(document_id=test_document.id, title="StreamDocVec")
    session = await create_session.__wrapped__(
        request=request, session_data=session_data, db=db_session, current_user=test_user
    )

    async def mock_stream(*args, **kwargs):
        yield "stream chunk"

    with patch("app.api.v1.chat.vector_service") as mock_vs, \
         patch("app.api.v1.chat.llm_service") as mock_llm:
        mock_vs.search = AsyncMock(return_value=[{"text": "found chunk", "score": 0.9}])
        mock_llm.extract_keywords = MagicMock(return_value=[])
        mock_llm.chat_stream = mock_stream
        chat_req = ChatRequest(session_id=session.id, message="What is this?", stream=True)
        response = await send_message_stream.__wrapped__(
            request=request, chat_request=chat_req, db=db_session, current_user=test_user
        )
        chunks = []
        async for chunk in response.body_iterator:
            chunks.append(chunk)
    content = "".join(chunks)
    assert "done" in content