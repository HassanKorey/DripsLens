"""Cache layer: Redis when REDIS_URL is set, in-process TTL dict otherwise.

The API stays fast (and GitHub-friendly) either way — Redis is recommended in
docker-compose, but the app must not hard-require it.
"""

import json
import logging
import time
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)

# In-process fallback: {key: (expires_at_monotonic, value)}
_memory_cache: dict[str, tuple[float, Any]] = {}

try:
    import redis.asyncio as aioredis

    _REDIS_AVAILABLE = True
except ImportError:  # pragma: no cover
    aioredis = None
    _REDIS_AVAILABLE = False

_redis: Any | None = None
_redis_started = False
_redis_retry_after = 0.0  # monotonic time before the next reconnection attempt

# When Redis is unreachable, back off before trying to reconnect so each
# request doesn't pay a connection timeout.
_REDIS_RETRY_COOLDOWN_SECONDS = 30.0


async def get_redis() -> Any | None:
    """Lazily connect to Redis; returns None when unavailable.

    Never raises: if the connection attempt fails (server down, bad URL,
    auth error, DNS failure...), the exception is swallowed and None is
    returned so callers fall back to the in-process cache (or skip caching
    entirely). Failed attempts trigger a cooldown during which None is
    returned without retrying, so the app keeps running — just without
    the Redis cache layer.
    """
    global _redis, _redis_started, _redis_retry_after
    if not _REDIS_AVAILABLE or not settings.redis_url:
        return None
    if _redis is not None:
        return _redis
    if _redis_started:
        # No client yet: either still connecting or cooling down after a
        # failed attempt.
        if time.monotonic() < _redis_retry_after:
            return None
    _redis_started = True
    try:
        client = aioredis.from_url(settings.redis_url, decode_responses=True)
        await client.ping()
    except Exception as exc:
        logger.warning(
            "Redis unavailable (%s); continuing without cache layer", exc
        )
        _redis = None
        _redis_retry_after = time.monotonic() + _REDIS_RETRY_COOLDOWN_SECONDS
        return None
    _redis = client
    _redis_retry_after = 0.0
    logger.info("Redis cache connected at %s", settings.redis_url)
    return _redis


async def cache_get(key: str) -> Any | None:
    r = await get_redis()
    if r is not None:
        try:
            raw = await r.get(key)
            return json.loads(raw) if raw is not None else None
        except Exception as exc:
            logger.warning("cache_get failed for %s: %s", key, exc)
            return None
    entry = _memory_cache.get(key)
    if not entry:
        return None
    expires_at, value = entry
    if time.monotonic() > expires_at:
        _memory_cache.pop(key, None)
        return None
    return value


async def cache_set(key: str, value: Any, ttl: int | None = None) -> None:
    ttl = ttl if ttl is not None else settings.cache_ttl_seconds
    r = await get_redis()
    if r is not None:
        try:
            await r.set(key, json.dumps(value, default=str), ex=ttl)
            return
        except Exception as exc:
            logger.warning("cache_set failed for %s: %s", key, exc)
    _memory_cache[key] = (time.monotonic() + ttl, value)


async def cache_delete(prefix: str) -> None:
    """Invalidate keys starting with `prefix`."""
    r = await get_redis()
    if r is not None:
        try:
            keys = [k async for k in r.scan_iter(f"{prefix}*")]
            if keys:
                await r.delete(*keys)
            return
        except Exception as exc:
            logger.warning("cache_delete failed for %s: %s", prefix, exc)
    for key in [k for k in _memory_cache if k.startswith(prefix)]:
        _memory_cache.pop(key, None)


def invalidate_prefix_sync(prefix: str) -> None:
    """Synchronous cache invalidation — safe to call from worker threads
    (e.g. APScheduler jobs). Redis uses a short-lived client; the in-process
    fallback is cleaned directly."""
    if _REDIS_AVAILABLE and settings.redis_url:
        try:
            sync_redis = __import__("redis").Redis.from_url(
                settings.redis_url, decode_responses=True, socket_connect_timeout=3
            )
            keys = list(sync_redis.scan_iter(f"{prefix}*"))
            if keys:
                sync_redis.delete(*keys)
            sync_redis.close()
            return
        except Exception as exc:
            logger.warning("sync cache invalidation failed for %s: %s", prefix, exc)
    for key in [k for k in list(_memory_cache) if k.startswith(prefix)]:
        _memory_cache.pop(key, None)


async def close_redis() -> None:
    global _redis, _redis_started, _redis_retry_after
    if _redis is not None:
        try:
            await _redis.close()
        except Exception:
            pass
    _redis = None
    _redis_started = False
    _redis_retry_after = 0.0
