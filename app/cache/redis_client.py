import redis
import os
import json
from functools import wraps

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)

def cache_response(ttl_seconds=300):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # For simplicity, we create a cache key based on the function name
            cache_key = f"cache:{func.__name__}"
            cached_data = redis_client.get(cache_key)
            if cached_data:
                return json.loads(cached_data)
            
            # Execute the actual function
            response = await func(*args, **kwargs)
            
            # Convert response to dict for caching if it has dict() method (like pydantic models)
            # or handle it appropriately. Here we assume response is serializable.
            # In a real app we might need to handle specific serialization.
            try:
                redis_client.setex(cache_key, ttl_seconds, json.dumps(response))
            except Exception:
                pass
            return response
        return wrapper
    return decorator
