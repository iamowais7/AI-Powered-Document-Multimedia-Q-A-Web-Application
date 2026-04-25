import pytest
import io
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient
from app.models.media import MediaFile


pytestmark = pytest.mark.asyncio


async def test_list_media_empty(client: AsyncClient, auth_headers: dict):
    response = await client.get("/api/v1/media/", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "media_files" in data
    assert "total" in data


async def test_upload_media_success(client: AsyncClient, auth_headers: dict):
    with patch("app.api.v1.media.transcription_service") as mock_ts, \
         patch("app.api.v1.media.vector_service") as mock_vs, \
         patch("app.api.v1.media.llm_service") as mock_llm, \
         patch("app.api.v1.media.pdf_service") as mock_pdf:

        mock_ts.save_file = AsyncMock(return_value=("uuid.mp3", "/tmp/uuid.mp3"))
        mock_ts.transcribe = AsyncMock(return_value={
            "text": "Hello world test transcription",
            "segments": [{"start": 0.0, "end": 3.0, "text": "Hello world"}],
            "duration": 3.0,
        })
        mock_ts.delete_file = MagicMock()
        mock_pdf.chunk_text = MagicMock(return_value=["chunk"])
        mock_vs.build_index = AsyncMock(return_value="/tmp/vectors/uuid")
        mock_vs.delete_index = MagicMock()
        mock_llm.summarize = AsyncMock(return_value="Audio summary here.")

        response = await client.post(
            "/api/v1/media/upload",
            headers=auth_headers,
            files={"file": ("audio.mp3", io.BytesIO(b"fake audio data"), "audio/mpeg")},
        )
    assert response.status_code == 201
    data = response.json()
    assert data["original_filename"] == "audio.mp3"
    assert data["media_type"] == "audio"
    assert data["transcription"] == "Hello world test transcription"
    assert data["duration"] == 3.0


async def test_upload_media_wrong_type(client: AsyncClient, auth_headers: dict):
    response = await client.post(
        "/api/v1/media/upload",
        headers=auth_headers,
        files={"file": ("test.pdf", io.BytesIO(b"pdf data"), "application/pdf")},
    )
    assert response.status_code == 400


async def test_upload_video_success(client: AsyncClient, auth_headers: dict):
    with patch("app.api.v1.media.transcription_service") as mock_ts, \
         patch("app.api.v1.media.vector_service") as mock_vs, \
         patch("app.api.v1.media.llm_service") as mock_llm, \
         patch("app.api.v1.media.pdf_service") as mock_pdf:

        mock_ts.save_file = AsyncMock(return_value=("uuid.mp4", "/tmp/uuid.mp4"))
        mock_ts.transcribe = AsyncMock(return_value={
            "text": "Video content",
            "segments": [],
            "duration": 60.0,
        })
        mock_ts.delete_file = MagicMock()
        mock_pdf.chunk_text = MagicMock(return_value=["chunk"])
        mock_vs.build_index = AsyncMock(return_value="/tmp/vectors/uuid_v")
        mock_vs.delete_index = MagicMock()
        mock_llm.summarize = AsyncMock(return_value="Video summary.")

        response = await client.post(
            "/api/v1/media/upload",
            headers=auth_headers,
            files={"file": ("video.mp4", io.BytesIO(b"fake video"), "video/mp4")},
        )
    assert response.status_code == 201
    assert response.json()["media_type"] == "video"


async def test_get_media(client: AsyncClient, auth_headers: dict, test_media: MediaFile):
    response = await client.get(f"/api/v1/media/{test_media.id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_media.id
    assert data["segments"] is not None
    assert len(data["segments"]) == 3


async def test_get_media_not_found(client: AsyncClient, auth_headers: dict):
    response = await client.get("/api/v1/media/99999", headers=auth_headers)
    assert response.status_code == 404


async def test_get_media_wrong_user(client: AsyncClient, auth_headers2: dict, test_media: MediaFile):
    response = await client.get(f"/api/v1/media/{test_media.id}", headers=auth_headers2)
    assert response.status_code == 404


async def test_delete_media(client: AsyncClient, auth_headers: dict):
    with patch("app.api.v1.media.transcription_service") as mock_ts, \
         patch("app.api.v1.media.vector_service") as mock_vs, \
         patch("app.api.v1.media.llm_service") as mock_llm, \
         patch("app.api.v1.media.pdf_service") as mock_pdf:

        mock_ts.save_file = AsyncMock(return_value=("del.mp3", "/tmp/del.mp3"))
        mock_ts.transcribe = AsyncMock(return_value={"text": "x", "segments": [], "duration": 1.0})
        mock_ts.delete_file = MagicMock()
        mock_pdf.chunk_text = MagicMock(return_value=[])
        mock_vs.build_index = AsyncMock(return_value="/tmp/v")
        mock_vs.delete_index = MagicMock()
        mock_llm.summarize = AsyncMock(return_value="s")

        upload_resp = await client.post(
            "/api/v1/media/upload",
            headers=auth_headers,
            files={"file": ("del.mp3", io.BytesIO(b"audio"), "audio/mpeg")},
        )
        media_id = upload_resp.json()["id"]

        del_resp = await client.delete(f"/api/v1/media/{media_id}", headers=auth_headers)
    assert del_resp.status_code == 204


async def test_delete_media_not_found(client: AsyncClient, auth_headers: dict):
    response = await client.delete("/api/v1/media/99999", headers=auth_headers)
    assert response.status_code == 404
