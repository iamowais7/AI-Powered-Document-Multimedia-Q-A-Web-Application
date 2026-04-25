import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
from app.services.pdf_service import PDFService


@pytest.fixture
def pdf_svc(tmp_path):
    return PDFService(upload_dir=str(tmp_path))


@pytest.fixture
def sample_pdf(tmp_path):
    """Create a minimal real PDF for testing."""
    pdf_content = b"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<<>>>>endobj
xref
0 4
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
trailer<</Size 4/Root 1 0 R>>
startxref
190
%%EOF"""
    pdf_path = tmp_path / "test.pdf"
    pdf_path.write_bytes(pdf_content)
    return str(pdf_path)


@pytest.mark.asyncio
async def test_save_file(pdf_svc, tmp_path):
    content = b"fake pdf content"
    filename, path = await pdf_svc.save_file(content, "test.pdf")
    assert filename.endswith(".pdf")
    assert os.path.exists(path)
    with open(path, "rb") as f:
        assert f.read() == content


def test_chunk_text_basic(pdf_svc):
    text = "A" * 3000
    chunks = pdf_svc.chunk_text(text, chunk_size=1000, overlap=200)
    assert len(chunks) > 1
    assert all(len(c) <= 1000 for c in chunks)


def test_chunk_text_empty(pdf_svc):
    assert pdf_svc.chunk_text("") == []


def test_chunk_text_short(pdf_svc):
    text = "short text"
    chunks = pdf_svc.chunk_text(text, chunk_size=1000)
    assert len(chunks) == 1
    assert chunks[0] == text


def test_chunk_text_overlap(pdf_svc):
    text = "A" * 500
    chunks = pdf_svc.chunk_text(text, chunk_size=300, overlap=100)
    assert len(chunks) >= 2


def test_delete_file_existing(pdf_svc, tmp_path):
    f = tmp_path / "todel.pdf"
    f.write_bytes(b"x")
    pdf_svc.delete_file(str(f))
    assert not f.exists()


def test_delete_file_nonexistent(pdf_svc):
    pdf_svc.delete_file("/nonexistent/path/file.pdf")  # Should not raise


def test_extract_text_with_pdfplumber(pdf_svc, tmp_path):
    with patch("app.services.pdf_service.pdfplumber") as mock_plumber:
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Page text content"
        mock_pdf = MagicMock()
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=False)
        mock_pdf.pages = [mock_page]
        mock_plumber.open.return_value = mock_pdf

        text, pages = pdf_svc.extract_text("/fake/path.pdf")
        assert "Page text content" in text
        assert pages == 1


def test_extract_text_fallback_to_pymupdf(pdf_svc, tmp_path):
    with patch("app.services.pdf_service.pdfplumber") as mock_plumber, \
         patch("app.services.pdf_service.fitz") as mock_fitz:

        mock_plumber.open.side_effect = Exception("pdfplumber failed")

        mock_page = MagicMock()
        mock_page.get_text.return_value = "PyMuPDF text"
        mock_doc = MagicMock()
        mock_doc.__iter__ = MagicMock(return_value=iter([mock_page]))
        mock_doc.__len__ = MagicMock(return_value=1)
        mock_fitz.open.return_value = mock_doc

        text, pages = pdf_svc.extract_text("/fake/path.pdf")
        assert "PyMuPDF text" in text


def test_extract_text_no_content(pdf_svc):
    with patch("app.services.pdf_service.pdfplumber") as mock_plumber:
        mock_page = MagicMock()
        mock_page.extract_text.return_value = None
        mock_pdf = MagicMock()
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=False)
        mock_pdf.pages = [mock_page]
        mock_plumber.open.return_value = mock_pdf

        text, pages = pdf_svc.extract_text("/fake/path.pdf")
        assert text == ""
        assert pages == 1
