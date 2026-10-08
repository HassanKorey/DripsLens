import json
import logging
import os
from collections.abc import Callable
from functools import wraps
from typing import Any

import redis

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL") or "redis://localhost:6379/0"
redis_client: redis.Redis | None = None
try:
    redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
except Exception:
    redis_client = None


def cache_response(ttl_seconds: int = 300) -> Callable:
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            cache_key = f"cache:{func.__name__}"
            if redis_client:
                try:
                    cached_data = redis_client.get(cache_key)
                    if cached_data:
                        return json.loads(str(cached_data))
                except Exception as e:
                    logger.warning("Redis cache get error: %s", e)

            response = await func(*args, **kwargs)

            if redis_client:
                try:
                    redis_client.setex(cache_key, ttl_seconds, json.dumps(response))
                except Exception as e:
                    logger.warning("Redis cache set error: %s", e)
            return response

        return wrapper

    return decorator
