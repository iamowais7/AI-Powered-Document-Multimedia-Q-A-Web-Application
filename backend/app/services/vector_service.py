import os
import json
import pickle
import asyncio
import numpy as np
from pathlib import Path
from typing import Any
from sentence_transformers import SentenceTransformer
import faiss
from app.config import settings

VECTOR_DIR = Path(settings.UPLOAD_DIR) / "vectors"
VECTOR_DIR.mkdir(parents=True, exist_ok=True)


class VectorService:
    def __init__(self, model_name: str = settings.EMBEDDING_MODEL):
        self._model: SentenceTransformer | None = None
        self.model_name = model_name

    @property
    def model(self) -> SentenceTransformer:
        if self._model is None:
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def _embed(self, texts: list[str]) -> np.ndarray:
        return self.model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)

    async def build_index(self, chunks: list[str], index_id: str) -> str:
        """Build a FAISS index for the given text chunks and persist it."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._build_index_sync, chunks, index_id)

    def _build_index_sync(self, chunks: list[str], index_id: str) -> str:
        embeddings = self._embed(chunks)
        dim = embeddings.shape[1]
        index = faiss.IndexFlatIP(dim)  # Inner Product (cosine on normalized vectors)
        index.add(embeddings)

        index_dir = VECTOR_DIR / index_id
        index_dir.mkdir(parents=True, exist_ok=True)

        faiss.write_index(index, str(index_dir / "index.faiss"))
        with open(index_dir / "chunks.pkl", "wb") as f:
            pickle.dump(chunks, f)

        return str(index_dir)

    async def search(self, query: str, index_path: str, top_k: int = 5) -> list[dict[str, Any]]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._search_sync, query, index_path, top_k)

    def _search_sync(self, query: str, index_path: str, top_k: int) -> list[dict[str, Any]]:
        index_dir = Path(index_path)
        index_file = index_dir / "index.faiss"
        chunks_file = index_dir / "chunks.pkl"

        if not index_file.exists() or not chunks_file.exists():
            return []

        index = faiss.read_index(str(index_file))
        with open(chunks_file, "rb") as f:
            chunks = pickle.load(f)

        query_embedding = self._embed([query])
        k = min(top_k, index.ntotal)
        scores, indices = index.search(query_embedding, k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx >= 0:
                results.append({"text": chunks[idx], "score": float(score), "index": int(idx)})
        return results

    def delete_index(self, index_path: str) -> None:
        import shutil
        path = Path(index_path)
        if path.exists():
            shutil.rmtree(path)


vector_service = VectorService()
