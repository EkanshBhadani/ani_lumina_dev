from __future__ import annotations
import os
import aiohttp
import asyncio
from typing import Any, Dict, List, Optional
from datetime import date
import logging

API_BASE = "https://api.myanimelist.net/v2"
_LOG = logging.getLogger(__name__)

# -------------------------------
# MALClient class (core client)
# -------------------------------
class MALClient:
    """
    Minimal MAL v2 client.
    Create with MALClient(client_id="...") or allow the module-level singleton to read env.
    """

    # Optional fallback: you may set this here for quick local testing (not for public repos)
    # CLIENT_ID = "ADD_YOUR_CLIENT_ID_HERE"  # <-- not recommended

    def __init__(self, client_id: Optional[str] = None, session: Optional[aiohttp.ClientSession] = None):
        self.client_id = client_id or getattr(self, "CLIENT_ID", None) or os.environ.get("MAL_CLIENT_ID")
        self._own_session = False
        if session is None:
            self._session = aiohttp.ClientSession()
            self._own_session = True
        else:
            self._session = session

    async def close(self) -> None:
        if self._own_session and not self._session.closed:
            await self._session.close()

    def _headers(self) -> Dict[str, str]:
        if not self.client_id:
            raise RuntimeError(
                "MAL Client ID not set. Set MAL_CLIENT_ID environment variable or pass client_id to MALClient."
            )
        return {"X-MAL-CLIENT-ID": self.client_id, "Accept": "application/json"}

    async def _get(self, path: str, params: Optional[Dict[str, Any]] = None, timeout: int = 15) -> Optional[Dict[str, Any]]:
        url = API_BASE.rstrip("/") + "/" + path.lstrip("/")
        headers = self._headers()
        try:
            async with self._session.get(url, headers=headers, params=params, timeout=timeout) as resp:
                if resp.status == 200:
                    return await resp.json()
                if resp.status == 204:
                    return {}
                if resp.status == 400:
                    txt = await resp.text()
                    raise RuntimeError(f"MAL API 400 Bad Request: {txt}")
                if resp.status == 401:
                    raise RuntimeError("MAL API 401 Unauthorized - check your Client ID.")
                if resp.status == 404:
                    return None
                txt = await resp.text()
                raise RuntimeError(f"MAL API unexpected status {resp.status}: {txt}")
        except asyncio.TimeoutError:
            raise RuntimeError("MAL API request timed out")
        except aiohttp.ClientError as e:
            raise RuntimeError(f"MAL API client error: {e}")

    # --- search endpoint wrapper ---
    async def search(
        self,
        kind: str,
        q: str,
        limit: int = 15,
        offset: int = 0,
        fields: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        kind = kind.lower()
        if kind not in ("anime", "manga", "character", "producer", "staff"):
            raise ValueError("Unsupported kind for search: " + kind)

        params: Dict[str, Any] = {"q": q, "limit": limit, "offset": offset}
        if fields:
            params["fields"] = fields

        path = f"{kind}"
        data = await self._get(path, params=params)
        if not data:
            return []
        # MAL typically returns {'data': [...]}
        if isinstance(data, dict) and "data" in data:
            results = []
            for item in data.get("data", []):
                node = item.get("node") or item
                results.append(node)
            return results
        if isinstance(data, list):
            return data
        return []

    # --- info endpoint wrapper (identifier first) ---
    async def info(self, identifier: str, kind: str = "anime") -> Optional[Dict[str, Any]]:
        kind = kind.lower()
        if kind not in ("anime", "manga", "character", "producer", "staff"):
            raise ValueError("Unsupported kind for info: " + kind)

        common_fields = ",".join(
            [
                "id",
                "title",
                "main_picture",
                "alternative_titles",
                "start_date",
                "end_date",
                "num_episodes",
                "mean",
                "rank",
                "popularity",
                "status",
                "media_type",
                "genres",
                "studios",
                "synopsis",
                "num_volumes",
                "num_chapters",
            ]
        )

        if identifier.isdigit():
            path = f"{kind}/{identifier}"
            params = {"fields": common_fields}
            return await self._get(path, params=params)

        # fallback: search and then request by id
        results = await self.search(kind=kind, q=identifier, limit=1, fields=common_fields)
        if not results:
            return None
        first = results[0]
        mal_id = first.get("id")
        if mal_id:
            return await self.info(str(mal_id), kind=kind)
        return first

    # --- seasonal listing ---
    async def season(self, year: int, season_name: str, fields: Optional[str] = None) -> List[Dict[str, Any]]:
        season_name = season_name.lower()
        if season_name == "autumn":
            season_name = "fall"
        if season_name not in ("winter", "spring", "summer", "fall"):
            raise ValueError("Invalid season. Use winter/spring/summer/fall")

        params: Dict[str, Any] = {}
        if fields:
            params["fields"] = fields
        path = f"anime/season/{year}/{season_name}"
        data = await self._get(path, params=params)
        if not data:
            return []
        if isinstance(data, dict) and "data" in data:
            return [item.get("node") or item for item in data.get("data", [])]
        return []

    # --- utility: paginate list ---
    @staticmethod
    def paginate_list(items: List[Any], page: int = 1, per_page: int = 5) -> List[Any]:
        start = (page - 1) * per_page
        end = start + per_page
        return items[start:end]

# -------------------------------
# Module-level singleton + helpers
# -------------------------------
_GLOBAL_CLIENT: Optional[MALClient] = None

def _ensure_client() -> MALClient:
    global _GLOBAL_CLIENT
    if _GLOBAL_CLIENT is None:
        # Build client from env if available; prefer env over hardcoded class value.
        cid = os.environ.get("MAL_CLIENT_ID")
        _GLOBAL_CLIENT = MALClient(client_id=cid)
    return _GLOBAL_CLIENT

async def close_client() -> None:
    global _GLOBAL_CLIENT
    if _GLOBAL_CLIENT is not None:
        try:
            await _GLOBAL_CLIENT.close()
        finally:
            _GLOBAL_CLIENT = None

# Backwards-compatible module-level wrappers
async def search(kind: str, q: str, limit: int = 15, offset: int = 0, fields: Optional[str] = None):
    """
    Module-level search wrapper for backward compatibility.
    Usage: await mal_client.search("anime", "naruto", limit=10)
    """
    client = _ensure_client()
    return await client.search(kind=kind, q=q, limit=limit, offset=offset, fields=fields)

async def info(identifier: str, kind: str = "anime"):
    """
    Module-level info wrapper.
    Usage: await mal_client.info("naruto", kind="anime") or await mal_client.info("1735")
    """
    client = _ensure_client()
    return await client.info(identifier=identifier, kind=kind)

async def season(year: int, season_name: str, fields: Optional[str] = None):
    client = _ensure_client()
    return await client.season(year=year, season_name=season_name, fields=fields)

async def next_season(fields: Optional[str] = None):
    """
    Compute the next season from today and fetch that season's listing.

    Example: If today is November 2025 (fall), the next season is winter 2026.
    """
    today = date.today()
    m = today.month
    # determine current season index:
    # winter: Dec(12) Jan(1) Feb(2)
    # spring: Mar(3) Apr(4) May(5)
    # summer: Jun(6) Jul(7) Aug(8)
    # fall: Sep(9) Oct(10) Nov(11)
    if m in (12, 1, 2):
        curr = "winter"
    elif m in (3, 4, 5):
        curr = "spring"
    elif m in (6, 7, 8):
        curr = "summer"
    else:
        curr = "fall"

    order = ["winter", "spring", "summer", "fall"]
    idx = order.index(curr)
    next_idx = (idx + 1) % 4
    next_season_name = order[next_idx]
    next_year = today.year + (1 if next_season_name == "winter" and curr == "fall" else 0)
    client = _ensure_client()
    return await client.season(year=next_year, season_name=next_season_name, fields=fields)

# expose class too if callers want to instantiate directly
__all__ = ["MALClient", "search", "info", "season", "next_season", "close_client"]
