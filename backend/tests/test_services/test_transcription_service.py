import pytest
import os
from unittest.mock import MagicMock, AsyncMock
from app.services.transcription_service import TranscriptionService


@pytest.fixture
def ts(tmp_path):
    svc = TranscriptionService(upload_dir=str(tmp_path))
    svc._client = MagicMock()
    return svc


@pytest.mark.asyncio
async def test_save_file(ts, tmp_path):
    content = b"fake audio bytes"
    filename, path = await ts.save_file(content, "test.mp3")
    assert filename.endswith(".mp3")
    assert os.path.exists(path)


@pytest.mark.asyncio
async def test_transcribe_success(ts, tmp_path):
    audio_file = tmp_path / "audio.mp3"
    audio_file.write_bytes(b"fake audio")

    mock_segment = MagicMock()
    mock_segment.start = 0.0
    mock_segment.end = 5.0
    mock_segment.text = " Hello world"

    mock_response = MagicMock()
    mock_response.text = "Hello world"
    mock_response.segments = [mock_segment]

    ts._client.audio.transcriptions.create.return_value = mock_response

    result = await ts.transcribe(str(audio_file))
    assert result["text"] == "Hello world"
    assert len(result["segments"]) == 1
    assert result["segments"][0]["start"] == 0.0
    assert result["segments"][0]["text"] == "Hello world"
    assert result["duration"] == 5.0


@pytest.mark.asyncio
async def test_transcribe_no_segments(ts, tmp_path):
    audio_file = tmp_path / "audio.mp3"
    audio_file.write_bytes(b"fake audio")

    mock_response = MagicMock()
    mock_response.text = "Hello"
    mock_response.segments = None

    ts._client.audio.transcriptions.create.return_value = mock_response

    result = await ts.transcribe(str(audio_file))
    assert result["text"] == "Hello"
    assert result["segments"] == []
    assert result["duration"] == 0.0


def test_find_relevant_segments_match(ts):
    segments = [
        {"start": 0.0, "end": 5.0, "text": "Hello world Python"},
        {"start": 5.0, "end": 10.0, "text": "Java programming"},
        {"start": 10.0, "end": 15.0, "text": "Python is great"},
    ]
    results = ts.find_relevant_segments(segments, ["python"], top_k=5)
    assert len(results) == 2
    assert results[0]["relevance_score"] >= results[-1]["relevance_score"]


def test_find_relevant_segments_no_match(ts):
    segments = [{"start": 0.0, "end": 5.0, "text": "Hello world"}]
    results = ts.find_relevant_segments(segments, ["python"], top_k=5)
    assert results == []


def test_find_relevant_segments_empty_segments(ts):
    assert ts.find_relevant_segments([], ["python"]) == []


def test_find_relevant_segments_empty_query(ts):
    segments = [{"start": 0.0, "end": 5.0, "text": "Hello"}]
    assert ts.find_relevant_segments(segments, []) == []


def test_find_relevant_segments_top_k(ts):
    segments = [{"start": float(i), "end": float(i + 1), "text": f"python {i}"} for i in range(10)]
    results = ts.find_relevant_segments(segments, ["python"], top_k=3)
    assert len(results) == 3


def test_delete_file_existing(ts, tmp_path):
    f = tmp_path / "audio.mp3"
    f.write_bytes(b"x")
    ts.delete_file(str(f))
    assert not f.exists()


def test_delete_file_nonexistent(ts):
    ts.delete_file("/nonexistent/audio.mp3")


def test_client_lazy_init(tmp_path):
    svc = TranscriptionService(upload_dir=str(tmp_path))
    assert svc._client is None
    # The client property creates an OpenAI instance on first access
    # We just verify _client is None until accessed