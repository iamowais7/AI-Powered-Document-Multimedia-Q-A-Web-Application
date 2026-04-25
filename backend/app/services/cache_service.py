import json
import hashlib
from typing import Any
import redis.asyncio as aioredis
from app.config import settings


class CacheService:
    def __init__(self, redis_url: str = settings.REDIS_URL):
        self.redis_url = redis_url
        self._client: aioredis.Redis | None = None

    async def get_client(self) -> aioredis.Redis:
        if self._client is None:
            self._client = await aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
        return self._client

    async def get(self, key: str) -> Any | None:
        client = await self.get_client()
        value = await client.get(key)
        if value is None:
            return None
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value

    async def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        client = await self.get_client()
        serialized = json.dumps(value) if not isinstance(value, str) else value
        await client.setex(key, ttl, serialized)

    async def delete(self, key: str) -> None:
        client = await self.get_client()
        await client.delete(key)

    async def exists(self, key: str) -> bool:
        client = await self.get_client()
        return bool(await client.exists(key))

    def make_key(self, *parts: str) -> str:
        combined = ":".join(str(p) for p in parts)
        return f"docqa:{combined}"

    def hash_key(self, *parts: str) -> str:
        combined = ":".join(str(p) for p in parts)
        hashed = hashlib.md5(combined.encode()).hexdigest()
        return f"docqa:hash:{hashed}"

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None


cache_service = CacheService()
