import asyncio
import time
from typing import Any, Dict, Optional

class AsyncTTLCache:
    def __init__(self, default_ttl: int = 60):
        self._data: Dict[str, Any] = {}
        self._expiry: Dict[str, float] = {}
        self._ttl = default_ttl
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        async with self._lock:
            exp = self._expiry.get(key)
            if exp is None:
                return None
            if exp < time.time():
                # expired
                self._data.pop(key, None)
                self._expiry.pop(key, None)
                return None
            return self._data.get(key)

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        async with self._lock:
            self._data[key] = value
            self._expiry[key] = time.time() + (ttl if ttl is not None else self._ttl)

    async def clear(self) -> None:
        async with self._lock:
            self._data.clear()
            self._expiry.clear()
