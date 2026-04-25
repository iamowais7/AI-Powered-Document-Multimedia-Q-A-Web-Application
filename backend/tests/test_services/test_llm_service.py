import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.llm_service import LLMService


@pytest.fixture
def llm():
    svc = LLMService()
    svc._client = MagicMock()
    return svc


@pytest.mark.asyncio
async def test_chat_success(llm):
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "AI response here"
    llm._client.chat.completions.create = AsyncMock(return_value=mock_response)

    result = await llm.chat(
        message="What is ML?",
        history=[],
        context_chunks=[{"text": "ML is machine learning", "score": 0.9}],
    )
    assert result == "AI response here"


@pytest.mark.asyncio
async def test_chat_with_history(llm):
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "Follow-up answer"
    llm._client.chat.completions.create = AsyncMock(return_value=mock_response)

    history = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there"},
    ]
    result = await llm.chat(message="Next question", history=history)
    assert result == "Follow-up answer"


@pytest.mark.asyncio
async def test_chat_with_media_context(llm):
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "Media answer"
    llm._client.chat.completions.create = AsyncMock(return_value=mock_response)

    segments = [{"start": 0.0, "end": 5.0, "text": "Hello world"}]
    relevant = [{"start": 0.0, "end": 5.0, "text": "Hello world", "relevance_score": 1.0}]
    result = await llm.chat(
        message="What is said?",
        history=[],
        media_segments=segments,
        relevant_segments=relevant,
    )
    assert result == "Media answer"


@pytest.mark.asyncio
async def test_chat_stream(llm):
    async def mock_aiter(self):
        for text in ["Hello", " world", "!"]:
            delta = MagicMock()
            delta.content = text
            choice = MagicMock()
            choice.delta = delta
            chunk = MagicMock()
            chunk.choices = [choice]
            yield chunk

    mock_stream = MagicMock()
    mock_stream.__aiter__ = mock_aiter
    llm._client.chat.completions.create = AsyncMock(return_value=mock_stream)

    result = []
    async for chunk in llm.chat_stream("Hello?", []):
        result.append(chunk)
    assert "".join(result) == "Hello world!"


@pytest.mark.asyncio
async def test_chat_stream_empty_delta(llm):
    async def mock_aiter(self):
        delta = MagicMock()
        delta.content = None
        choice = MagicMock()
        choice.delta = delta
        chunk = MagicMock()
        chunk.choices = [choice]
        yield chunk

    mock_stream = MagicMock()
    mock_stream.__aiter__ = mock_aiter
    llm._client.chat.completions.create = AsyncMock(return_value=mock_stream)

    result = []
    async for chunk in llm.chat_stream("Hello?", []):
        result.append(chunk)
    assert result == []


@pytest.mark.asyncio
async def test_summarize(llm):
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "This is a summary"
    llm._client.chat.completions.create = AsyncMock(return_value=mock_response)

    result = await llm.summarize("Long text to summarize...")
    assert result == "This is a summary"


@pytest.mark.asyncio
async def test_summarize_truncates_long_text(llm):
    long_text = "x" * 10000
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "Summary"
    llm._client.chat.completions.create = AsyncMock(return_value=mock_response)

    result = await llm.summarize(long_text)
    assert result == "Summary"
    call_args = llm._client.chat.completions.create.call_args
    user_content = call_args.kwargs["messages"][1]["content"]
    assert len(user_content) < len(long_text) + 100


def test_extract_keywords(llm):
    text = "machine learning algorithms data science Python programming"
    keywords = llm.extract_keywords(text)
    assert "machine" in keywords
    assert "learning" in keywords


def test_extract_keywords_removes_stop_words(llm):
    text = "the quick brown fox"
    keywords = llm.extract_keywords(text)
    assert "the" not in keywords


def test_extract_keywords_max_20(llm):
    text = " ".join([f"keyword{i}" for i in range(50)])
    keywords = llm.extract_keywords(text)
    assert len(keywords) <= 20


def test_build_context_empty(llm):
    msgs = llm._build_messages("q", [], context_chunks=None, media_segments=None, relevant_segments=None)
    assert msgs[-1]["content"] == "q"


def test_build_context_with_chunks(llm):
    chunks = [{"text": "relevant info", "score": 0.9}]
    msgs = llm._build_messages("q", [], context_chunks=chunks, media_segments=None, relevant_segments=None)
    assert "relevant info" in msgs[-1]["content"]


def test_history_truncated_to_last_10(llm):
    history = [{"role": "user" if i % 2 == 0 else "assistant", "content": f"msg{i}"} for i in range(30)]
    msgs = llm._build_messages("new msg", history, None, None, None)
    assert len(msgs) <= 12