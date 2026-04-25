from typing import AsyncIterator
from openai import AsyncOpenAI
from app.config import settings


SYSTEM_PROMPT = """You are an intelligent assistant that answers questions based on provided document or media content.
Always ground your answers in the provided context. If the context doesn't contain enough information to answer the question, say so clearly.
When answering questions about media files, reference specific timestamps when relevant."""

SUMMARY_PROMPT = """Provide a concise, well-structured summary of the following content.
Focus on key topics, main points, and important details.
Format the summary with clear sections if the content warrants it."""


class LLMService:
    def __init__(self):
        self._client: AsyncOpenAI | None = None

    @property
    def client(self) -> AsyncOpenAI:
        if self._client is None:
            self._client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        return self._client

    def _build_context_message(self, context_chunks: list[dict]) -> str:
        if not context_chunks:
            return ""
        parts = ["Relevant context from the document:\n"]
        for i, chunk in enumerate(context_chunks, 1):
            parts.append(f"[{i}] {chunk['text']}\n")
        return "\n".join(parts)

    def _build_media_context(self, segments: list[dict], relevant_segments: list[dict]) -> str:
        if not relevant_segments:
            return ""
        parts = ["Relevant transcript segments with timestamps:\n"]
        for seg in relevant_segments:
            start = seg.get("start", 0)
            end = seg.get("end", 0)
            text = seg.get("text", "")
            parts.append(f"[{start:.1f}s - {end:.1f}s]: {text}")
        return "\n".join(parts)

    async def chat(
        self,
        message: str,
        history: list[dict],
        context_chunks: list[dict] | None = None,
        media_segments: list[dict] | None = None,
        relevant_segments: list[dict] | None = None,
    ) -> str:
        messages = self._build_messages(
            message, history, context_chunks, media_segments, relevant_segments
        )
        response = await self.client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.3,
            max_tokens=2048,
        )
        return response.choices[0].message.content

    async def chat_stream(
        self,
        message: str,
        history: list[dict],
        context_chunks: list[dict] | None = None,
        media_segments: list[dict] | None = None,
        relevant_segments: list[dict] | None = None,
    ) -> AsyncIterator[str]:
        messages = self._build_messages(
            message, history, context_chunks, media_segments, relevant_segments
        )
        stream = await self.client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.3,
            max_tokens=2048,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                yield delta.content

    def _build_messages(
        self,
        message: str,
        history: list[dict],
        context_chunks: list[dict] | None,
        media_segments: list[dict] | None,
        relevant_segments: list[dict] | None,
    ) -> list[dict]:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        context_str = ""
        if context_chunks:
            context_str = self._build_context_message(context_chunks)
        if relevant_segments:
            context_str += "\n\n" + self._build_media_context(media_segments or [], relevant_segments)

        for msg in history[-10:]:  # last 10 messages
            messages.append({"role": msg["role"], "content": msg["content"]})

        user_content = message
        if context_str:
            user_content = f"{context_str}\n\nQuestion: {message}"

        messages.append({"role": "user", "content": user_content})
        return messages

    async def summarize(self, text: str, max_length: int = 500) -> str:
        truncated = text[:8000] if len(text) > 8000 else text
        response = await self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SUMMARY_PROMPT},
                {"role": "user", "content": f"Content to summarize:\n\n{truncated}"},
            ],
            temperature=0.3,
            max_tokens=max_length,
        )
        return response.choices[0].message.content

    def extract_keywords(self, text: str) -> list[str]:
        words = text.lower().split()
        stop_words = {"the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
                      "have", "has", "had", "do", "does", "did", "will", "would", "could",
                      "should", "may", "might", "shall", "can", "need", "dare", "ought",
                      "used", "to", "of", "in", "on", "at", "by", "for", "with", "about",
                      "against", "between", "into", "through", "during", "before", "after",
                      "above", "below", "from", "up", "down", "out", "off", "over", "under",
                      "and", "or", "but", "if", "because", "as", "until", "while", "that",
                      "this", "these", "those", "what", "which", "who", "how", "when", "where"}
        keywords = [w.strip(".,!?;:\"'()[]{}") for w in words if w not in stop_words and len(w) > 3]
        return list(dict.fromkeys(keywords))[:20]


llm_service = LLMService()
