# mal_client.py
import os
import aiohttp
from urllib.parse import urlencode

MAL_BASE = os.getenv("MAL_BASE_URL", "https://api.myanimelist.net/v2")

class MALClient:
    def __init__(self, session: aiohttp.ClientSession):
        self.s = session
        self.base = MAL_BASE.rstrip('/')

    async def _get(self, path: str, params: dict = None):
        url = f"{self.base}/{path.lstrip('/')}"
        if params:
            url += "?" + urlencode(params)
        async with self.s.get(url, timeout=20) as resp:
            resp.raise_for_status()
            return await resp.json()

    async def search_anime(self, query: str, limit: int = 5):
        data = await self._get("anime", {"q": query, "limit": limit})
        return data.get("data", [])

    async def get_anime(self, mal_id: int):
        data = await self._get(f"anime/{mal_id}")
        return data.get("data")
