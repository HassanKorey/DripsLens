"""Asynchronous Redis caching layer with TTL expiration and in-memory fallback.

Caches JSON serialization of repository and contributor leaderboard queries,
transparently falling back to in-memory storage and database execution when Redis
is unavailable, and providing cache invalidation triggers for background sync tasks.
"""

import json
import logging
import os
import time
from collections.abc import Callable
from functools import wraps
from typing import Any

import redis

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "")
redis_client: redis.Redis | None = None
if REDIS_URL:
    try:
        redis_client = redis.Redis.from_url(
            REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=0.5,
            socket_timeout=0.5,
        )
    except Exception:
        redis_client = None

# In-memory TTL fallback cache: key -> (expires_at_monotonic, json_payload)
_fallback_cache: dict[str, tuple[float, str]] = {}


def _is_db_session(value: Any) -> bool:
    """Return True if value looks like a SQLAlchemy session dependency."""
    return hasattr(value, "execute") and hasattr(value, "commit")


def build_cache_key(prefix: str, *args: Any, **kwargs: Any) -> str:
    """Construct a deterministic cache key from function name and query parameters."""
    parts: list[str] = [f"cache:{prefix}"]

    for arg in args:
        if not _is_db_session(arg):
            parts.append(str(arg))

    for key in sorted(kwargs.keys()):
        if key == "db" or _is_db_session(kwargs[key]):
            continue
        parts.append(f"{key}={kwargs[key]}")

    return ":".join(parts)


def get_cached_json(cache_key: str) -> Any | None:
    """Retrieve and deserialize cached JSON from Redis or in-memory fallback."""
    if redis_client is not None:
        try:
            cached_data = redis_client.get(cache_key)
            if cached_data is not None:
                return json.loads(str(cached_data))
            return None
        except Exception as e:
            logger.warning("Redis cache get error: %s", e)

    entry = _fallback_cache.get(cache_key)
    if entry is not None:
        expires_at, payload = entry
        if time.monotonic() < expires_at:
            try:
                return json.loads(payload)
            except Exception:
                _fallback_cache.pop(cache_key, None)
        else:
            _fallback_cache.pop(cache_key, None)

    return None


def set_cached_json(cache_key: str, value: Any, ttl_seconds: int = 300) -> None:
    """Serialize and store JSON payload in Redis and in-memory fallback with TTL."""
    try:
        serialized = json.dumps(value)
    except (TypeError, ValueError) as e:
        logger.warning("Failed to serialize response for cache key %s: %s", cache_key, e)
        return

    _fallback_cache[cache_key] = (time.monotonic() + ttl_seconds, serialized)

    if redis_client is not None:
        try:
            redis_client.setex(cache_key, ttl_seconds, serialized)
        except Exception as e:
            logger.warning("Redis cache set error: %s", e)


def invalidate_cache(prefix: str | None = None) -> int:
    """Invalidate cached entries matching prefix (or all cache entries if None)."""
    target_prefix = f"cache:{prefix}" if prefix else "cache:"
    removed = 0

    keys_to_drop = [k for k in _fallback_cache if k.startswith(target_prefix)]
    for k in keys_to_drop:
        _fallback_cache.pop(k, None)
        removed += 1

    if redis_client is not None:
        try:
            redis_keys = list(redis_client.keys(f"{target_prefix}*"))
            if redis_keys:
                deleted = redis_client.delete(*redis_keys)
                if isinstance(deleted, int):
                    removed += deleted
        except Exception as e:
            logger.warning("Redis cache invalidation error: %s", e)

    return removed


def cache_response(ttl_seconds: int = 300) -> Callable:
    """Decorator to cache async endpoint responses with Redis + in-memory TTL fallback."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            cache_key = build_cache_key(func.__name__, *args, **kwargs)
            cached = get_cached_json(cache_key)
            if cached is not None:
                return cached

            response = await func(*args, **kwargs)
            set_cached_json(cache_key, response, ttl_seconds=ttl_seconds)
            return response

        return wrapper

    return decorator
