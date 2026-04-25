import os
import uuid
import aiofiles
from pathlib import Path
from typing import BinaryIO
import pdfplumber
import fitz  # PyMuPDF
from app.config import settings


class PDFService:
    def __init__(self, upload_dir: str = settings.UPLOAD_DIR):
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    async def save_file(self, file_content: bytes, original_filename: str) -> tuple[str, str]:
        ext = Path(original_filename).suffix
        unique_filename = f"{uuid.uuid4()}{ext}"
        file_path = self.upload_dir / unique_filename
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(file_content)
        return unique_filename, str(file_path)

    def extract_text(self, file_path: str) -> tuple[str, int]:
        text_parts = []
        page_count = 0
        try:
            with pdfplumber.open(file_path) as pdf:
                page_count = len(pdf.pages)
                for page in pdf.pages:
                    extracted = page.extract_text()
                    if extracted:
                        text_parts.append(extracted)
        except Exception:
            # Fallback to PyMuPDF
            doc = fitz.open(file_path)
            page_count = len(doc)
            for page in doc:
                text_parts.append(page.get_text())
            doc.close()
        return "\n\n".join(text_parts), page_count

    def chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> list[str]:
        if not text:
            return []
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            chunks.append(chunk)
            start += chunk_size - overlap
        return chunks

    def delete_file(self, file_path: str) -> None:
        path = Path(file_path)
        if path.exists():
            path.unlink()


pdf_service = PDFService()
