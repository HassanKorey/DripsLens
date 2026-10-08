from unittest.mock import MagicMock, patch

import pytest

from app.cache.redis_client import cache_response


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
