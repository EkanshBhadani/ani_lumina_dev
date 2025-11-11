import os
import asyncio
from typing import Any, Dict, List, Optional, Tuple, Union
import aiohttp
from cache import AsyncTTLCache
from models import get_current_season, get_next_season

API_BASE_DEFAULT = "https://api.myanimelist.net/v2"
# fields commonly useful
COMMON_FIELDS = "id,title,main_picture,mean,rank,media_type,status,num_episodes,start_date"

class MALClient:
    def __init__(self, client_id: Optional[str] = None, base_url: Optional[str] = None, cache_ttl: int = 60):
        # If you didn't pass client_id, it will try from env
        # 👉 Add your MAL Client ID in your .env as MAL_CLIENT_ID
        self.client_id = client_id or os.getenv("7e437c417001602f040b6dd6dc7ea768")
        self.base_url = base_url or os.getenv("API_BASE", API_BASE_DEFAULT).rstrip("/")
        self._session: Optional[aiohttp.ClientSession] = None
        self._cache = AsyncTTLCache(default_ttl=cache_ttl)
        self._lock = asyncio.Lock()

    async def __aenter__(self):
        if not self._session:
            headers = {}
            if self.client_id:
                headers["X-MAL-CLIENT-ID"] = self.client_id
            self._session = aiohttp.ClientSession(headers=headers)
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self._session:
            await self._session.close()
            self._session = None

    async def _get(self, path: str, params: Optional[Dict[str, str]] = None) -> Any:
        url = f"{self.base_url}{path}"
        cache_key = f"GET:{url}:{params}"
        cached = await self._cache.get(cache_key)
        if cached is not None:
            return cached

        if not self._session:
            headers = {}
            if self.client_id:
                headers["X-MAL-CLIENT-ID"] = self.client_id
            self._session = aiohttp.ClientSession(headers=headers)

        async with self._lock:
            async with self._session.get(url, params=params, timeout=20) as resp:
                # handle non-200
                if resp.status == 200:
                    data = await resp.json()
                    await self._cache.set(cache_key, data)
                    return data
                elif resp.status == 204:
                    return None
                else:
                    text = await resp.text()
                    raise aiohttp.ClientResponseError(
                        request_info=resp.request_info,
                        history=resp.history,
                        status=resp.status,
                        message=f"Bad response ({resp.status}): {text}",
                        headers=resp.headers,
                    )

    # generic search for anime/manga
    async def search(self, kind: str, query: str, limit: int = 15, offset: int = 0, fields: str = COMMON_FIELDS) -> Dict[str, Any]:
        """
        kind: 'anime' or 'manga' or 'character' etc.
        returns raw JSON from MAL v2 search endpoint.
        """
        path = f"/{kind}"
        params = {"q": query, "limit": str(limit), "offset": str(offset), "fields": fields}
        return await self._get(path, params=params)

    async def search_anime(self, query: str, limit: int = 15, offset: int = 0) -> Dict[str, Any]:
        return await self.search("anime", query, limit=limit, offset=offset)

    async def search_manga(self, query: str, limit: int = 15, offset: int = 0) -> Dict[str, Any]:
        return await self.search("manga", query, limit=limit, offset=offset)

    async def search_character(self, query: str, limit: int = 15, offset: int = 0) -> Dict[str, Any]:
        return await self.search("characters", query, limit=limit, offset=offset, fields="id,name,character_name,about,main_picture")

    async def search_people(self, query: str, limit: int = 15, offset: int = 0) -> Dict[str, Any]:
        # people endpoint (voice actors)
        return await self.search("people", query, limit=limit, offset=offset, fields="id,name,main_picture")

    async def search_studio(self, query: str, limit: int = 15, offset: int = 0) -> Dict[str, Any]:
        # studios are available as 'producers' endpoint in some APIs, MAL v2 uses 'producers' or 'studios' depending
        # We'll try producers first
        return await self.search("producers", query, limit=limit, offset=offset, fields="id,name")

    async def info(self, identifier: Union[int, str], kind: str = "anime", fields: str = COMMON_FIELDS) -> Dict[str, Any]:
        """
        Fetch detailed info for an item.
        identifier: either numeric id or name (string). If string is not numeric, we do a search and return first match's full details.
        kind: 'anime' or 'manga' or 'characters' etc.
        """
        # If identifier looks like an id (int), fetch details by id
        if isinstance(identifier, int) or (isinstance(identifier, str) and identifier.isdigit()):
            item_id = int(identifier)
            path = f"/{kind}/{item_id}"
            params = {"fields": fields}
            return await self._get(path, params=params)

        # otherwise search and return first match's details
        search_res = await self.search(kind, identifier, limit=1, fields=fields)
        if not search_res:
            return {}
        if isinstance(search_res, dict) and search_res.get("data"):
            first = search_res["data"][0]
            # data item often contains node with id and more fields
            node = first.get("node") or first.get("id") and first  # fallback
            # MAL v2 search returns nodes where id is inside .node.id for some endpoints.
            item_id = None
            if isinstance(node, dict):
                item_id = node.get("id") or node.get("node", {}).get("id")
            else:
                # sometimes search result top-level contains id
                item_id = first.get("id")
            if item_id:
                return await self.info(item_id, kind=kind, fields=fields)
        return {}

    async def seasonal(self, year: int, season: str, limit: int = 15, offset: int = 0, fields: str = COMMON_FIELDS) -> Dict[str, Any]:
        """
        season: winter, spring, summer, fall (lowercase)
        """
        path = f"/anime/season/{year}/{season}"
        params = {"limit": str(limit), "offset": str(offset), "fields": fields}
        return await self._get(path, params=params)

    async def current_season(self, limit: int = 15, offset: int = 0, fields: str = COMMON_FIELDS) -> Dict[str, Any]:
        year, season = get_current_season()
        return await self.seasonal(year, season, limit=limit, offset=offset, fields=fields)

    async def next_season(self, limit: int = 15, offset: int = 0, fields: str = COMMON_FIELDS) -> Dict[str, Any]:
        year, season = get_next_season()
        return await self.seasonal(year, season, limit=limit, offset=offset, fields=fields)

    async def top(self, kind: str = "anime", limit: int = 15, offset: int = 0, fields: str = COMMON_FIELDS) -> Dict[str, Any]:
        path = f"/{kind}/ranking"
        params = {"limit": str(limit), "offset": str(offset), "fields": fields}
        return await self._get(path, params=params)

    async def trending(self, kind: str = "anime", limit: int = 15, offset: int = 0, fields: str = COMMON_FIELDS) -> Dict[str, Any]:
        # MAL doesn't have a single 'trending' v2 endpoint publicly documented; many use ranking by popularity
        # We'll attempt ranking by popularity (ranking_type=popularity)
        path = f"/{kind}/ranking"
        params = {"limit": str(limit), "offset": str(offset), "ranking_type": "popularity", "fields": fields}
        return await self._get(path, params=params)

    async def schedule(self, day: Optional[str] = None, limit: int = 50, fields: str = COMMON_FIELDS) -> Dict[str, Any]:
        """
        MAL v2 does not expose a simple schedule endpoint the same way. If you have schedule info, you might
        use seasonal endpoints or other endpoints. This method will fallback to seasonal data and filter by day if possible.
        day: 'monday', 'tuesday', ... or None for whole season
        """
        year, season = get_current_season()
        season_data = await self.seasonal(year, season, limit=limit, fields=fields)
        # schedule filtering is best-effort by looking at 'start_date' or 'broadcast' keys if available in fields
        if not day:
            return season_data
        day_low = day.lower()
        # filter items with "broadcast" or "aired" info - best effort
        filtered = {"data": []}
        for item in season_data.get("data", []):
            # some items may have 'node' or direct
            info = item.get("node") or item
            # Check for broadcast or start_date - MAL's v2 seasonal usually doesn't include weekday; so this is best-effort.
            # Here, just include everything (since accurate schedule requires another source)
            filtered["data"].append(item)
        return filtered

    async def recommend(self, kind: str = "anime", id_or_name: Union[int, str] = None, limit: int = 10, fields: str = COMMON_FIELDS) -> Dict[str, Any]:
        """
        MAL v2 recommendations endpoint is /anime/{id}/recommendations -- if you have an id, use that.
        If only name provided, will try to resolve to id and then fetch recommendations.
        """
        item = None
        if id_or_name is None:
            return {}
        if isinstance(id_or_name, str) and not id_or_name.isdigit():
            resolved = await self.info(id_or_name, kind=kind, fields="id")
            item_id = resolved.get("id") if isinstance(resolved, dict) else None
        else:
            item_id = int(id_or_name)
        if not item_id:
            return {}
        path = f"/{kind}/{item_id}/recommendations"
        params = {"limit": str(limit), "fields": fields}
        return await self._get(path, params=params)
