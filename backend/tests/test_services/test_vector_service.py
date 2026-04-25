import pytest
import numpy as np
import pickle
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from app.services.vector_service import VectorService


@pytest.fixture
def vs(tmp_path):
    svc = VectorService()
    svc._model = MagicMock()
    # Return normalized unit vectors for each input
    svc._model.encode = MagicMock(side_effect=lambda texts, **kw: np.random.rand(len(texts), 384).astype("float32"))
    return svc, tmp_path


@pytest.mark.asyncio
async def test_build_and_search(vs):
    svc, tmp_path = vs
    chunks = ["Python is great", "Java is verbose", "Machine learning rocks"]

    index_path = await svc.build_index(chunks, "test_idx")
    assert Path(index_path).exists()
    assert (Path(index_path) / "index.faiss").exists()
    assert (Path(index_path) / "chunks.pkl").exists()

    results = await svc.search("Python programming", index_path, top_k=2)
    assert isinstance(results, list)
    assert len(results) <= 2
    for r in results:
        assert "text" in r
        assert "score" in r


@pytest.mark.asyncio
async def test_search_missing_index(vs, tmp_path):
    svc, _ = vs
    results = await svc.search("query", "/nonexistent/path", top_k=5)
    assert results == []


@pytest.mark.asyncio
async def test_search_top_k_limit(vs):
    svc, tmp_path = vs
    chunks = [f"chunk {i}" for i in range(10)]
    index_path = await svc.build_index(chunks, "topk_test")
    results = await svc.search("query", index_path, top_k=3)
    assert len(results) <= 3


def test_delete_index_existing(vs, tmp_path):
    svc, _ = vs
    test_dir = tmp_path / "to_delete"
    test_dir.mkdir()
    (test_dir / "file.txt").write_text("hello")
    svc.delete_index(str(test_dir))
    assert not test_dir.exists()


def test_delete_index_nonexistent(vs):
    svc, _ = vs
    svc.delete_index("/nonexistent/path")  # Should not raise


def test_model_lazy_init():
    svc = VectorService()
    assert svc._model is None


@pytest.mark.asyncio
async def test_build_index_creates_correct_files(vs):
    svc, tmp_path = vs
    chunks = ["text a", "text b"]
    index_path = await svc.build_index(chunks, "verify_test")

    with open(Path(index_path) / "chunks.pkl", "rb") as f:
        saved_chunks = pickle.load(f)
    assert saved_chunks == chunks


@pytest.mark.asyncio
async def test_search_returns_all_if_fewer_than_k(vs):
    svc, tmp_path = vs
    chunks = ["only one chunk"]
    index_path = await svc.build_index(chunks, "one_chunk")
    results = await svc.search("query", index_path, top_k=10)
    assert len(results) == 1
