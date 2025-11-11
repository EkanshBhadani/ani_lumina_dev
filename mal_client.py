import os
import aiohttp
from typing import List, Dict, Any, Optional
from cache import aiorun_cached
from models import parse_anime, parse_manga, Anime, Manga

BASE = "https://api.myanimelist.net/v2"
FIELDS_ANIME = "id,title,main_picture,mean,rank,status,num_episodes,start_date"
FIELDS_MANGA = "id,title,main_picture,mean,rank,status,num_chapters,num_volumes,start_date"

class MALClient:
    def __init__(self, client_id: Optional[str] = None, session: Optional[aiohttp.ClientSession] = None):
        self.client_id = client_id or os.getenv("MAL_CLIENT_ID")
        if not self.client_id:
            raise RuntimeError("MAL_CLIENT_ID is missing")
        self._session = session
        self._own_session = session is None

    async def __aenter__(self):
        if not self._session:
            self._session = aiohttp.ClientSession(
                headers={"X-MAL-CLIENT-ID": self.client_id, "Accept": "application/json"}
            )
        return self

    async def __aexit__(self, *exc):
        if self._own_session and self._session:
            await self._session.close()

    @property
    def session(self) -> aiohttp.ClientSession:
        if not self._session:
            self._session = aiohttp.ClientSession(
                headers={"X-MAL-CLIENT-ID": self.client_id, "Accept": "application/json"}
            )
            self._own_session = True
        return self._session

    async def _get(self, path: str, **params) -> Dict[str, Any]:
        url = f"{BASE}{path}"
        async with self.session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=20)) as r:
            if r.status == 429:
                raise RuntimeError("MAL rate limited. Try again shortly.")
            if r.status >= 400:
                text = await r.text()
                raise RuntimeError(f"MAL error {r.status}: {text}")
            return await r.json()

    # ---- Search ----
    @aiorun_cached(ttl=300)
    async def search_anime(self, query: str, limit: int = 5) -> List[Anime]:
        data = await self._get("/anime", q=query, limit=min(limit, 10), fields=FIELDS_ANIME)
        return [parse_anime(n) for n in data.get("data", [])]

    @aiorun_cached(ttl=300)
    async def search_manga(self, query: str, limit: int = 5) -> List[Manga]:
        data = await self._get("/manga", q=query, limit=min(limit, 10), fields=FIELDS_MANGA)
        return [parse_manga(n) for n in data.get("data", [])]

    # ---- Rankings ----
    @aiorun_cached(ttl=600)
    async def top_airing_anime(self, limit: int = 5) -> List[Anime]:
        data = await self._get("/anime/ranking", ranking_type="airing", limit=min(limit, 10), fields=FIELDS_ANIME)
        return [parse_anime(n) for n in data.get("data", [])]

    @aiorun_cached(ttl=600)
    async def trending_anime(self, limit: int = 5) -> List[Anime]:
        # MAL doesn't have "trending"; use "bypopularity" as a practical proxy.
        data = await self._get("/anime/ranking", ranking_type="bypopularity", limit=min(limit, 10), fields=FIELDS_ANIME)
        return [parse_anime(n) for n in data.get("data", [])]

    @aiorun_cached(ttl=600)
    async def trending_manga(self, limit: int = 5) -> List[Manga]:
        data = await self._get("/manga/ranking", ranking_type="bypopularity", limit=min(limit, 10), fields=FIELDS_MANGA)
        return [parse_manga(n) for n in data.get("data", [])]

    # ---- Seasonals (current airing season) ----
    @aiorun_cached(ttl=600)
    async def seasonal(self, year: int, season: str, limit: int = 5) -> List[Anime]:
        # MAL seasonal endpoint:
        data = await self._get(f"/anime/season/{year}/{season}", limit=min(limit, 10), fields=FIELDS_ANIME)
        return [parse_anime(n) for n in data.get("data", [])]
