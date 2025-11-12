# cache.py
import time
import asyncio
from typing import Any, Dict, Tuple, Optional, Callable, Awaitable

class TTLCache:
    def __init__(self):
        self._store: Dict[str, Tuple[float, Any]] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        async with self._lock:
            item = self._store.get(key)
            if not item:
                return None
            exp, val = item
            if exp and exp < time.time():
                self._store.pop(key, None)
                return None
            return val

    async def set(self, key: str, value: Any, ttl: int = 0) -> None:
        async with self._lock:
            exp = time.time() + ttl if ttl else 0
            self._store[key] = (exp, value)

CACHE = TTLCache()

def aiorun_cached(ttl: int) -> Callable[[Callable[..., Awaitable[Any]]], Callable[..., Awaitable[Any]]]:
    """Decorator for caching async funcs by args+kwargs stringified key."""
    def wrap(func: Callable[..., Awaitable[Any]]):
        async def inner(*args, **kwargs):
            key = f"{func.__name__}|{args}|{sorted(kwargs.items())}"
            cached = await CACHE.get(key)
            if cached is not None:
                return cached
            result = await func(*args, **kwargs)
            await CACHE.set(key, result, ttl)
            return result
        return inner
    return wrap