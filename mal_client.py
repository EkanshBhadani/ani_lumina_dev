# mal_client.py
# MAL API client helper for Ani Lumina
#
# IMPORTANT: put your MyAnimeList Client ID (from dev portal) in the CLIENT_ID variable
#            OR pass it when creating MALClient(client_id="YOUR_CLIENT_ID")
#
# API docs: https://api.myanimelist.net/v2

from __future__ import annotations
import aiohttp
import asyncio
from typing import Any, Dict, List, Optional, Union

API_BASE = "https://api.myanimelist.net/v2"


class MALClient:
    """
    Minimal MyAnimeList v2 API client.

    Usage:
        # Option A: set CLIENT_ID below in the file (not recommended for public repos)
        client = MALClient()

        # Option B (recommended): pass it from environment / secrets at runtime
        client = MALClient(client_id=os.environ.get("MAL_CLIENT_ID"))

    NOTE: Do not publish your Client ID in a public repo. Use environment variables on your host.
    """

    # --- Put client id here if you insist on hardcoding (NOT recommended) ---
    # CLIENT_ID = "ADD_YOUR_CLIENT_ID_HERE"
    # ----------------------------------------------------------------------

    def __init__(self, client_id: Optional[str] = None, session: Optional[aiohttp.ClientSession] = None):
        # prefer explicit parameter; fallback to class constant if set
        self.client_id = client_id or getattr(self, "CLIENT_ID", None)
        self._own_session = False
        if session is None:
            self._session = aiohttp.ClientSession()
            self._own_session = True
        else:
            self._session = session

    async def close(self) -> None:
        if self._own_session:
            await self._session.close()

    def _headers(self) -> Dict[str, str]:
        if not self.client_id:
            # We keep a clear message rather than implicitly failing later
            # Your code should set MAL_CLIENT_ID in env and pass to MALClient.
            raise RuntimeError("MAL Client ID not set. Add it via MALClient(client_id=...) or set CLIENT_ID in this file.")
        return {
            "X-MAL-CLIENT-ID": self.client_id,
            "Accept": "application/json",
        }

    async def _get(self, path: str, params: Optional[Dict[str, Any]] = None, timeout: int = 15) -> Optional[Dict[str, Any]]:
        url = API_BASE.rstrip("/") + "/" + path.lstrip("/")
        headers = self._headers()
        try:
            async with self._session.get(url, headers=headers, params=params, timeout=timeout) as resp:
                if resp.status == 200:
                    return await resp.json()
                elif resp.status == 204:
                    return {}
                elif resp.status == 400:
                    text = await resp.text()
                    raise RuntimeError(f"MAL API 400: {text}")
                elif resp.status == 401:
                    raise RuntimeError("MAL API 401 Unauthorized - check Client ID")
                elif resp.status == 404:
                    return None
                else:
                    text = await resp.text()
                    raise RuntimeError(f"MAL API unexpected status {resp.status}: {text}")
        except asyncio.TimeoutError:
            raise RuntimeError("MAL API request timed out")
        except aiohttp.ClientError as e:
            raise RuntimeError(f"MAL API client error: {e}")

    async def search(
        self,
        kind: str,
        q: str,
        limit: int = 15,
        offset: int = 0,
        fields: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search (anime/manga/character/staff/producer) on MAL.

        Returns a list of result objects (may be empty).
        """
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
        # MAL returns {'data': [ { 'node': {...} }, ... ]} for many endpoints
        if isinstance(data, dict) and "data" in data:
            results = []
            for item in data.get("data", []):
                node = item.get("node") or item
                results.append(node)
            return results
        # otherwise try best-effort
        if isinstance(data, list):
            return data
        return []

    async def info(self, identifier: str, kind: str = "anime") -> Optional[Dict[str, Any]]:
        """
        Get detailed info for an anime/manga/character/producer/staff.
        Signature deliberately uses (identifier, kind) so identifier is positional.

        - If identifier is numeric (digits only) we treat it as the MAL id: /{kind}/{id}
        - If identifier is non-numeric we try searching with q=identifier and return the first match

        Returns:
            dict (detailed object) or None if not found.
        """
        kind = kind.lower()
        if kind not in ("anime", "manga", "character", "producer", "staff"):
            raise ValueError("Unsupported kind for info: " + kind)

        # fields we commonly want; you can add more if your UI needs them
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
            data = await self._get(path, params=params)
            return data

        # otherwise try search and return the first item
        results = await self.search(kind=kind, q=identifier, limit=1, fields=common_fields)
        if not results:
            return None
        # results are nodes; get detailed info by id where possible
        first = results[0]
        mal_id = first.get("id")
        if mal_id:
            return await self.info(str(mal_id), kind=kind)
        # fallback: return the raw search node
        return first

    async def season(self, year: int, season: str, fields: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Return season listing for a specific season+year.
        season should be one of: winter, spring, summer, fall (case-insensitive)
        """
        season = season.lower()
        if season not in ("winter", "spring", "summer", "fall", "autumn"):
            raise ValueError("Invalid season. Use winter/spring/summer/fall")
        # MAL exposes seasonal endpoint: /anime/season/{year}/{season}
        params = {}
        if fields:
            params["fields"] = fields
        path = f"anime/season/{year}/{season}"
        data = await self._get(path, params=params)
        if not data:
            return []
        if isinstance(data, dict) and "data" in data:
            return [item.get("node") or item for item in data.get("data", [])]
        return []

    # convenience helper for paging
    @staticmethod
    def paginate_list(items: List[Any], page: int = 1, per_page: int = 5) -> List[Any]:
        start = (page - 1) * per_page
        end = start + per_page
        return items[start:end]
