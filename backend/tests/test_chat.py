import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch, AsyncMock
from httpx import AsyncClient
from app.models.user import User
from app.models.document import Document
from app.models.media import MediaFile
from app.models.chat import ChatSession


pytestmark = pytest.mark.asyncio


async def test_create_session_with_document(
    client: AsyncClient, auth_headers: dict, test_document: Document
):
    response = await client.post(
        "/api/v1/chat/sessions",
        headers=auth_headers,
        json={"document_id": test_document.id, "title": "Doc Chat"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["document_id"] == test_document.id
    assert data["title"] == "Doc Chat"


async def test_create_session_with_media(
    client: AsyncClient, auth_headers: dict, test_media: MediaFile
):
    response = await client.post(
        "/api/v1/chat/sessions",
        headers=auth_headers,
        json={"media_file_id": test_media.id, "title": "Media Chat"},
    )
    assert response.status_code == 201
    assert response.json()["media_file_id"] == test_media.id


async def test_create_session_no_resource(client: AsyncClient, auth_headers: dict):
    response = await client.post(
        "/api/v1/chat/sessions",
        headers=auth_headers,
        json={"title": "General Chat"},
    )
    assert response.status_code == 201


async def test_create_session_invalid_document(client: AsyncClient, auth_headers: dict):
    response = await client.post(
        "/api/v1/chat/sessions",
        headers=auth_headers,
        json={"document_id": 99999},
    )
    assert response.status_code == 404


async def test_create_session_invalid_media(client: AsyncClient, auth_headers: dict):
    response = await client.post(
        "/api/v1/chat/sessions",
        headers=auth_headers,
        json={"media_file_id": 99999},
    )
    assert response.status_code == 404


async def test_list_sessions(client: AsyncClient, auth_headers: dict, test_chat_session: ChatSession):
    response = await client.get("/api/v1/chat/sessions", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


async def test_get_session(client: AsyncClient, auth_headers: dict, test_chat_session: ChatSession):
    response = await client.get(f"/api/v1/chat/sessions/{test_chat_session.id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_chat_session.id


async def test_get_session_not_found(client: AsyncClient, auth_headers: dict):
    response = await client.get("/api/v1/chat/sessions/99999", headers=auth_headers)
    assert response.status_code == 404


async def test_send_message_document_chat(
    client: AsyncClient, auth_headers: dict, test_chat_session: ChatSession, test_document: Document
):
    with patch("app.api.v1.chat.vector_service") as mock_vs, \
         patch("app.api.v1.chat.llm_service") as mock_llm:

        mock_vs.search = AsyncMock(return_value=[{"text": "relevant chunk", "score": 0.9}])
        mock_llm.chat = AsyncMock(return_value="The document discusses machine learning.")
        mock_llm.extract_keywords = MagicMock(return_value=["machine", "learning"])

        response = await client.post(
            "/api/v1/chat/message",
            headers=auth_headers,
            json={"session_id": test_chat_session.id, "message": "What is this about?", "stream": False},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["message"]["role"] == "assistant"
    assert "machine learning" in data["message"]["content"]


async def test_send_message_media_chat(
    client: AsyncClient, auth_headers: dict, test_media: MediaFile, db_session
):
    session_resp = await client.post(
        "/api/v1/chat/sessions",
        headers=auth_headers,
        json={"media_file_id": test_media.id, "title": "Media QA"},
    )
    session_id = session_resp.json()["id"]

    with patch("app.api.v1.chat.vector_service") as mock_vs, \
         patch("app.api.v1.chat.llm_service") as mock_llm, \
         patch("app.api.v1.chat.transcription_service") as mock_ts:

        mock_vs.search = AsyncMock(return_value=[])
        mock_llm.chat = AsyncMock(return_value="Python functions are covered at 5 seconds.")
        mock_llm.extract_keywords = MagicMock(return_value=["Python", "functions"])
        mock_ts.find_relevant_segments = MagicMock(return_value=[
            {"start": 5.0, "end": 10.0, "text": "Today we cover functions.", "relevance_score": 2}
        ])

        response = await client.post(
            "/api/v1/chat/message",
            headers=auth_headers,
            json={"session_id": session_id, "message": "Where are Python functions?", "stream": False},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["relevant_timestamps"] is not None
    assert len(data["relevant_timestamps"]) > 0
    assert data["relevant_timestamps"][0]["start"] == 5.0


async def test_send_message_session_not_found(client: AsyncClient, auth_headers: dict):
    response = await client.post(
        "/api/v1/chat/message",
        headers=auth_headers,
        json={"session_id": 99999, "message": "hello", "stream": False},
    )
    assert response.status_code == 404


async def test_send_message_stream(
    client: AsyncClient, auth_headers: dict, test_chat_session: ChatSession
):
    async def mock_stream(*args, **kwargs):
        for chunk in ["Hello", " world", "!"]:
            yield chunk

    with patch("app.api.v1.chat.vector_service") as mock_vs, \
         patch("app.api.v1.chat.llm_service") as mock_llm:

        mock_vs.search = AsyncMock(return_value=[])
        mock_llm.extract_keywords = MagicMock(return_value=[])
        mock_llm.chat_stream = mock_stream

        response = await client.post(
            "/api/v1/chat/message/stream",
            headers=auth_headers,
            json={"session_id": test_chat_session.id, "message": "Stream test", "stream": True},
        )
    assert response.status_code == 200
    content = response.text
    assert "data:" in content


async def test_delete_session(
    client: AsyncClient, auth_headers: dict, test_document: Document
):
    session_resp = await client.post(
        "/api/v1/chat/sessions",
        headers=auth_headers,
        json={"document_id": test_document.id, "title": "Delete Me"},
    )
    session_id = session_resp.json()["id"]

    del_resp = await client.delete(f"/api/v1/chat/sessions/{session_id}", headers=auth_headers)
    assert del_resp.status_code == 204


async def test_delete_session_not_found(client: AsyncClient, auth_headers: dict):
    response = await client.delete("/api/v1/chat/sessions/99999", headers=auth_headers)
    assert response.status_code == 404
