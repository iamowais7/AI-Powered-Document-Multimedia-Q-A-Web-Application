import os
import uuid
import aiofiles
import asyncio
from pathlib import Path
from openai import OpenAI
from app.config import settings


class TranscriptionService:
    def __init__(self, upload_dir: str = settings.UPLOAD_DIR):
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self._client: OpenAI | None = None

    @property
    def client(self) -> OpenAI:
        if self._client is None:
            self._client = OpenAI(api_key=settings.OPENAI_API_KEY)
        return self._client

    async def save_file(self, file_content: bytes, original_filename: str) -> tuple[str, str]:
        ext = Path(original_filename).suffix
        unique_filename = f"{uuid.uuid4()}{ext}"
        file_path = self.upload_dir / unique_filename
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(file_content)
        return unique_filename, str(file_path)

    async def transcribe(self, file_path: str) -> dict:
        """Transcribe audio/video file using Whisper API.
        Returns dict with 'text', 'segments', and 'duration'.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._transcribe_sync, file_path)

    def _transcribe_sync(self, file_path: str) -> dict:
        with open(file_path, "rb") as audio_file:
            response = self.client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="verbose_json",
                timestamp_granularities=["segment"],
            )

        segments = []
        if hasattr(response, "segments") and response.segments:
            for seg in response.segments:
                segments.append({
                    "start": seg.start,
                    "end": seg.end,
                    "text": seg.text.strip(),
                })

        duration = 0.0
        if segments:
            duration = segments[-1]["end"]

        return {
            "text": response.text,
            "segments": segments,
            "duration": duration,
        }

    def find_relevant_segments(
        self, segments: list[dict], query_terms: list[str], top_k: int = 5
    ) -> list[dict]:
        """Find segments most relevant to the query terms by keyword matching."""
        if not segments or not query_terms:
            return []

        scored = []
        query_lower = [t.lower() for t in query_terms]
        for seg in segments:
            text_lower = seg["text"].lower()
            score = sum(1 for term in query_lower if term in text_lower)
            if score > 0:
                scored.append({**seg, "relevance_score": score})

        scored.sort(key=lambda x: x["relevance_score"], reverse=True)
        return scored[:top_k]

    def delete_file(self, file_path: str) -> None:
        path = Path(file_path)
        if path.exists():
            path.unlink()


transcription_service = TranscriptionService()
