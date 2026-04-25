import pytest
import fakeredis.aioredis
from app.services.cache_service import CacheService


@pytest.fixture
async def cache(fake_redis):
    svc = CacheService()
    svc._client = fake_redis
    return svc


@pytest.mark.asyncio
async def test_set_and_get_string(cache):
    await cache.set("key1", "value1")
    result = await cache.get("key1")
    assert result == "value1"


@pytest.mark.asyncio
async def test_set_and_get_dict(cache):
    data = {"name": "test", "value": 42}
    await cache.set("key2", data)
    result = await cache.get("key2")
    assert result == data


@pytest.mark.asyncio
async def test_get_nonexistent(cache):
    result = await cache.get("nonexistent_key_xyz")
    assert result is None


@pytest.mark.asyncio
async def test_delete(cache):
    await cache.set("key3", "value3")
    await cache.delete("key3")
    result = await cache.get("key3")
    assert result is None


@pytest.mark.asyncio
async def test_exists_true(cache):
    await cache.set("key4", "value4")
    assert await cache.exists("key4") is True


@pytest.mark.asyncio
async def test_exists_false(cache):
    assert await cache.exists("key_does_not_exist_abc") is False


@pytest.mark.asyncio
async def test_set_ttl(cache):
    await cache.set("ttl_key", "value", ttl=1)
    result = await cache.get("ttl_key")
    assert result == "value"


def test_make_key(cache):
    key = cache.make_key("user", "123", "docs")
    assert key == "docqa:user:123:docs"


def test_hash_key(cache):
    key1 = cache.hash_key("user", "123", "query text here")
    key2 = cache.hash_key("user", "123", "query text here")
    key3 = cache.hash_key("user", "456", "query text here")
    assert key1 == key2
    assert key1 != key3
    assert key1.startswith("docqa:hash:")


@pytest.mark.asyncio
async def test_set_list(cache):
    data = [1, 2, 3, "four"]
    await cache.set("list_key", data)
    result = await cache.get("list_key")
    assert result == data


@pytest.mark.asyncio
async def test_close(cache):
    await cache.close()
    # After close, client should be reset
    assert cache._client is None


@pytest.mark.asyncio
async def test_get_client_returns_existing(fake_redis):
    svc = CacheService()
    svc._client = fake_redis
    client = await svc.get_client()
    assert client is fake_redis
