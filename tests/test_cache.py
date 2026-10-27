import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.cache.redis_client import (
    build_cache_key,
    cache_response,
    get_cached_json,
    invalidate_cache,
    set_cached_json,
)
from app.scheduler.tasks import sync_wave_repositories


@pytest.mark.asyncio
async def test_cache_response_decorator_miss_and_hit():
    mock_redis = MagicMock()
    mock_redis.get.return_value = None  # Cache miss

    call_count = 0

    @cache_response(ttl_seconds=60)
    async def sample_func(param: str):
        nonlocal call_count
        call_count += 1
        return {"data": param}

    with patch("app.cache.redis_client.redis_client", mock_redis):
        res1 = await sample_func("hello")
        assert res1 == {"data": "hello"}
        assert call_count == 1
        mock_redis.setex.assert_called_once()

        # Cache hit
        mock_redis.get.return_value = '{"data": "hello"}'
        res2 = await sample_func("hello")
        assert res2 == {"data": "hello"}
        assert call_count == 1  # Not executed again


@pytest.mark.asyncio
async def test_cache_response_handles_redis_error():
    mock_redis = MagicMock()
    mock_redis.get.side_effect = Exception("Redis error")
    mock_redis.setex.side_effect = Exception("Redis error")

    @cache_response(ttl_seconds=60)
    async def sample_func_error():
        return {"status": "ok"}

    with patch("app.cache.redis_client.redis_client", mock_redis):
        res = await sample_func_error()
        assert res == {"status": "ok"}


@pytest.mark.asyncio
async def test_cache_key_includes_query_parameters_and_ignores_db_session(db_session):
    key_py = build_cache_key("list_repos", language="Python", multiplier=2, skip=0, limit=10, db=db_session)
    key_rs = build_cache_key("list_repos", language="Rust", multiplier=1, skip=0, limit=10, db=db_session)

    assert key_py != key_rs
    assert "language=Python" in key_py
    assert "db=" not in key_py


@pytest.mark.asyncio
async def test_in_memory_fallback_ttl_expiration_and_sub_10ms_hit():
    invalidate_cache()
    with patch("app.cache.redis_client.redis_client", None):
        set_cached_json("cache:fast_key", [{"id": 1, "name": "repo"}], ttl_seconds=60)

        t0 = time.perf_counter()
        hit = get_cached_json("cache:fast_key")
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        assert hit == [{"id": 1, "name": "repo"}]
        assert elapsed_ms < 10.0

        # Expired TTL entry returns None
        set_cached_json("cache:expired_key", {"stale": True}, ttl_seconds=-1)
        assert get_cached_json("cache:expired_key") is None


@pytest.mark.asyncio
async def test_invalidate_cache_clears_redis_and_fallback_entries():
    mock_redis = MagicMock()
    mock_redis.keys.return_value = ["cache:list_repos:limit=10"]
    mock_redis.delete.return_value = 1

    set_cached_json("cache:list_repos:limit=10", [{"id": 1}], ttl_seconds=60)
    set_cached_json("cache:get_leaderboard:limit=10", [{"id": 2}], ttl_seconds=60)

    with patch("app.cache.redis_client.redis_client", mock_redis):
        removed = invalidate_cache("list_repos")
        assert removed >= 1
        mock_redis.keys.assert_called_once_with("cache:list_repos*")
        mock_redis.delete.assert_called_once_with("cache:list_repos:limit=10")

    with patch("app.cache.redis_client.redis_client", None):
        assert get_cached_json("cache:list_repos:limit=10") is None
        assert get_cached_json("cache:get_leaderboard:limit=10") == [{"id": 2}]


@pytest.mark.asyncio
async def test_repos_and_leaderboard_endpoints_cache_and_sync_invalidation(
    async_client: AsyncClient,
    seed_drips_data,
):
    invalidate_cache()

    # First call populates cache
    r1 = await async_client.get("/repos?language=Python")
    assert r1.status_code == 200
    assert len(r1.json()) == 1

    # Second call hits cache under 10ms even when Redis is disconnected
    t0 = time.perf_counter()
    r2 = await async_client.get("/repos?language=Python")
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    assert r2.status_code == 200
    assert r2.json() == r1.json()
    assert elapsed_ms < 10.0

    # Leaderboard endpoint also caches and differentiates limit parameter
    lb1 = await async_client.get("/leaderboard?limit=1")
    lb2 = await async_client.get("/leaderboard?limit=2")
    assert len(lb1.json()) == 1
    assert len(lb2.json()) == 2

    # Background sync task invalidates cached entries
    with patch("app.scheduler.tasks.fetch_issues_for_repo", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = [{"id": 10}, {"id": 11}, {"id": 12}]
        await sync_wave_repositories()

    with patch("app.cache.redis_client.redis_client", None):
        assert get_cached_json("cache:list_repos:language=Python:limit=10:multiplier=None:skip=0") is None
