import pytest
import io
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient
from app.models.user import User
from app.models.document import Document


pytestmark = pytest.mark.asyncio


@pytest.fixture
def pdf_file():
    return ("test.pdf", io.BytesIO(b"%PDF-1.4 test content"), "application/pdf")


async def test_list_documents_empty(client: AsyncClient, auth_headers: dict):
    response = await client.get("/api/v1/documents/", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "documents" in data
    assert "total" in data


async def test_list_documents_unauthenticated(client: AsyncClient):
    response = await client.get("/api/v1/documents/")
    assert response.status_code == 403


async def test_upload_document_success(client: AsyncClient, auth_headers: dict):
    with patch("app.api.v1.documents.pdf_service") as mock_pdf, \
         patch("app.api.v1.documents.vector_service") as mock_vector, \
         patch("app.api.v1.documents.llm_service") as mock_llm:

        mock_pdf.save_file = AsyncMock(return_value=("uuid.pdf", "/tmp/uuid.pdf"))
        mock_pdf.extract_text = MagicMock(return_value=("Sample document text", 2))
        mock_pdf.chunk_text = MagicMock(return_value=["chunk1", "chunk2"])
        mock_pdf.delete_file = MagicMock()
        mock_vector.build_index = AsyncMock(return_value="/tmp/vectors/uuid")
        mock_llm.summarize = AsyncMock(return_value="This is a summary.")

        content = b"%PDF-1.4 fake pdf content"
        response = await client.post(
            "/api/v1/documents/upload",
            headers=auth_headers,
            files={"file": ("test.pdf", io.BytesIO(content), "application/pdf")},
        )
    assert response.status_code == 201
    data = response.json()
    assert data["original_filename"] == "test.pdf"
    assert data["summary"] == "This is a summary."


async def test_upload_document_wrong_type(client: AsyncClient, auth_headers: dict):
    response = await client.post(
        "/api/v1/documents/upload",
        headers=auth_headers,
        files={"file": ("test.txt", io.BytesIO(b"plain text"), "text/plain")},
    )
    assert response.status_code == 400


async def test_upload_document_too_large(client: AsyncClient, auth_headers: dict):
    with patch("app.api.v1.documents.MAX_SIZE", 10):
        response = await client.post(
            "/api/v1/documents/upload",
            headers=auth_headers,
            files={"file": ("test.pdf", io.BytesIO(b"x" * 100), "application/pdf")},
        )
    assert response.status_code == 400


async def test_get_document(client: AsyncClient, auth_headers: dict, test_document: Document):
    response = await client.get(f"/api/v1/documents/{test_document.id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_document.id
    assert data["original_filename"] == test_document.original_filename


async def test_get_document_not_found(client: AsyncClient, auth_headers: dict):
    response = await client.get("/api/v1/documents/99999", headers=auth_headers)
    assert response.status_code == 404


async def test_get_document_wrong_user(client: AsyncClient, auth_headers2: dict, test_document: Document):
    response = await client.get(f"/api/v1/documents/{test_document.id}", headers=auth_headers2)
    assert response.status_code == 404


async def test_delete_document(client: AsyncClient, auth_headers: dict, db_session):
    with patch("app.api.v1.documents.pdf_service") as mock_pdf, \
         patch("app.api.v1.documents.vector_service") as mock_vector, \
         patch("app.api.v1.documents.llm_service") as mock_llm:

        mock_pdf.save_file = AsyncMock(return_value=("uuid2.pdf", "/tmp/uuid2.pdf"))
        mock_pdf.extract_text = MagicMock(return_value=("text", 1))
        mock_pdf.chunk_text = MagicMock(return_value=["c"])
        mock_pdf.delete_file = MagicMock()
        mock_vector.build_index = AsyncMock(return_value="/tmp/vectors/uuid2")
        mock_vector.delete_index = MagicMock()
        mock_llm.summarize = AsyncMock(return_value="summary")

        upload_resp = await client.post(
            "/api/v1/documents/upload",
            headers=auth_headers,
            files={"file": ("del.pdf", io.BytesIO(b"%PDF del"), "application/pdf")},
        )
        doc_id = upload_resp.json()["id"]

        del_resp = await client.delete(f"/api/v1/documents/{doc_id}", headers=auth_headers)
    assert del_resp.status_code == 204


async def test_delete_document_not_found(client: AsyncClient, auth_headers: dict):
    response = await client.delete("/api/v1/documents/99999", headers=auth_headers)
    assert response.status_code == 404


async def test_list_documents_cached(client: AsyncClient, auth_headers: dict, test_document: Document):
    response1 = await client.get("/api/v1/documents/", headers=auth_headers)
    response2 = await client.get("/api/v1/documents/", headers=auth_headers)
    assert response1.status_code == 200
    assert response2.status_code == 200
    assert response1.json()["total"] == response2.json()["total"]
