# mal_client.py
import os
import aiohttp
from typing import List, Dict, Any, Optional
from cache import aiorun_cached
from models import parse_anime, parse_manga, Anime, Manga

BASE = "https://api.myanimelist.net/v2"
FIELDS_ANIME = "id,title,main_picture,mean,rank,status,num_episodes,start_date"
FIELDS_MANGA = "id,title,main_picture,mean,rank,status,num_chapters,num_volumes,start_date"

class MALClient:
    """
    Robust MAL API client:
      - Proper async context manager (async with MALClient() as mal:)
      - close() coroutine to explicitly release the aiohttp session
      - avoids leaking aiohttp.ClientSession objects
    """

    def __init__(self, client_id: Optional[str] = None, session: Optional[aiohttp.ClientSession] = None):
        self.client_id = client_id or os.getenv("MAL_CLIENT_ID")
        if not self.client_id:
            raise RuntimeError("MAL_CLIENT_ID is missing")
        self._session: Optional[aiohttp.ClientSession] = session
        # If session was provided externally we should not close it here
        self._own_session: bool = session is None

    # ---------- context manager ----------
    async def __aenter__(self):
        # create session if we don't already have one
        if self._session is None or getattr(self._session, "closed", False):
            # create a session with the required headers
            self._session = aiohttp.ClientSession(
                headers={"X-MAL-CLIENT-ID": self.client_id, "Accept": "application/json"}
            )
            self._own_session = True
        return self

    async def __aexit__(self, exc_type, exc, tb):
        # close the session if we created it
        if self._own_session and self._session is not None:
            try:
                if not self._session.closed:
                    await self._session.close()
            finally:
                self._session = None
                self._own_session = False

    # Defensive: if someone accidentally uses a sync `with MALClient()` raise a helpful error
    def __enter__(self):
        raise RuntimeError("MALClient must be used with 'async with MALClient()' (it is async-only).")

    def __exit__(self, exc_type, exc, tb):
        # never called for async usage
        return False

    # Allow explicit close when not using context manager
    async def close(self):
        if self._session is not None:
            try:
                if not self._session.closed:
                    await self._session.close()
            finally:
                self._session = None
                self._own_session = False

    @property
    def session(self) -> aiohttp.ClientSession:
        """
        Return a ClientSession. If one does not exist yet, create one.
        Note: this is synchronous; it constructs aiohttp.ClientSession without awaiting,
        which is acceptable here because creating the session is not an async coroutine.
        """
        if self._session is None or getattr(self._session, "closed", False):
            self._session = aiohttp.ClientSession(
                headers={"X-MAL-CLIENT-ID": self.client_id, "Accept": "application/json"}
            )
            self._own_session = True
        return self._session

    # ----------------- internal helper -----------------
    async def _get(self, path: str, **params) -> Dict[str, Any]:
        url = f"{BASE}{path}"
        # ensure we operate with an active session; if session was closed, property recreates it
        sess = self.session
        async with sess.get(url, params=params, timeout=aiohttp.ClientTimeout(total=20)) as r:
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
        data = await self._get("/anime/ranking", ranking_type="bypopularity", limit=min(limit, 10), fields=FIELDS_ANIME)
        return [parse_anime(n) for n in data.get("data", [])]

    @aiorun_cached(ttl=600)
    async def trending_manga(self, limit: int = 5) -> List[Manga]:
        data = await self._get("/manga/ranking", ranking_type="bypopularity", limit=min(limit, 10), fields=FIELDS_MANGA)
        return [parse_manga(n) for n in data.get("data", [])]

    # ---- Seasonals (current airing season) ----
    @aiorun_cached(ttl=600)
    async def seasonal(self, year: int, season: str, limit: int = 5) -> List[Anime]:
        data = await self._get(f"/anime/season/{year}/{season}", limit=min(limit, 10), fields=FIELDS_ANIME)
        return [parse_anime(n) for n in data.get("data", [])]
