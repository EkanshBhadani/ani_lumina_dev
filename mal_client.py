# mal_client.py
import os
import aiohttp
from typing import List, Optional, Union
from models import Anime, Manga, Character, VoiceActor, Studio, ScheduleEntry

class MALClient:
    BASE_URL = "https://api.myanimelist.net/v2"
    CLIENT_ID = os.getenv("7e437c417001602f040b6dd6dc7ea768")
    # Note: For public info endpoints, MAL documentation states you pass X-MAL-CLIENT-ID header. :contentReference[oaicite:1]{index=1}

    def __init__(self):
        self._session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        self._session = aiohttp.ClientSession(
            headers={"X-MAL-CLIENT-ID": self.CLIENT_ID}
        )
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self._session:
            await self._session.close()

    async def search_anime(self, query: str, limit: int = 15) -> List[Anime]:
        url = f"{self.BASE_URL}/anime?q={query}&limit={limit}"
        async with self._session.get(url) as resp:
            resp.raise_for_status()
            data = await resp.json()
        items = data.get("data", [])
        results: List[Anime] = []
        for item in items:
            node = item.get("node", item)  # check if node wrapper present
            anime = Anime(
                id=node.get("id"),
                title=node.get("title"),
                url=node.get("url"),
                picture=node.get("main_picture", {}).get("medium"),
                mean=node.get("mean"),
                rank=node.get("rank"),
                episodes=node.get("num_episodes"),
                start_date=node.get("start_season", {}).get("year"),
                synopsis=node.get("synopsis")
            )
            results.append(anime)
        return results

    async def search_manga(self, query: str, limit: int = 15) -> List[Manga]:
        url = f"{self.BASE_URL}/manga?q={query}&limit={limit}"
        async with self._session.get(url) as resp:
            resp.raise_for_status()
            data = await resp.json()
        items = data.get("data", [])
        results: List[Manga] = []
        for item in items:
            node = item.get("node", item)
            manga = Manga(
                id=node.get("id"),
                title=node.get("title"),
                url=node.get("url"),
                picture=node.get("main_picture", {}).get("medium"),
                mean=node.get("mean"),
                rank=node.get("rank"),
                chapters=node.get("num_chapters"),
                volumes=node.get("num_volumes"),
                start_date=node.get("published", {}).get("start"),
                synopsis=node.get("synopsis")
            )
            results.append(manga)
        return results

    async def info(self, kind: str, identifier: Union[int,str]) -> Union[Anime, Manga]:
        """
        kind: "anime" or "manga"
        identifier: ID or slug of item
        """
        url = f"{self.BASE_URL}/{kind}/{identifier}"
        async with self._session.get(url) as resp:
            resp.raise_for_status()
            data = await resp.json()
        node = data.get("data", {}).get("node", data.get("data", {}))
        if kind == "anime":
            return Anime(
                id=node.get("id"),
                title=node.get("title"),
                url=node.get("url"),
                picture=node.get("main_picture", {}).get("medium"),
                mean=node.get("mean"),
                rank=node.get("rank"),
                episodes=node.get("num_episodes"),
                start_date=node.get("start_season", {}).get("year"),
                synopsis=node.get("synopsis")
            )
        else:
            return Manga(
                id=node.get("id"),
                title=node.get("title"),
                url=node.get("url"),
                picture=node.get("main_picture", {}).get("medium"),
                mean=node.get("mean"),
                rank=node.get("rank"),
                chapters=node.get("num_chapters"),
                volumes=node.get("num_volumes"),
                start_date=node.get("published", {}).get("start"),
                synopsis=node.get("synopsis")
            )

    # Stub methods for other features — you’ll need to flesh these out similarly:
    async def top(self, kind: str = "anime", limit: int = 10) -> List:
        # Implementation will likely call: /{kind}/ranking
        url = f"{self.BASE_URL}/{kind}/ranking?ranking_type=all&limit={limit}"
        async with self._session.get(url) as resp:
            resp.raise_for_status()
            data = await resp.json()
        items = data.get("data", [])
        # Map items into Anime/Manga accordingly
        return []  # placeholder

    async def trending(self, kind: str = "anime", limit: int = 10) -> List:
        # Implementation will likely call: /{kind}/ranking?ranking_type=favorite or similar
        url = f"{self.BASE_URL}/{kind}/ranking?ranking_type=favorite&limit={limit}"
        async with self._session.get(url) as resp:
            resp.raise_for_status()
            data = await resp.json()
        items = data.get("data", [])
        return []  # placeholder

    async def seasonal_anime(self, year: int, season: str) -> List[Anime]:
        url = f"{self.BASE_URL}/anime/season/{year}/{season}?limit=15"
        async with self._session.get(url) as resp:
            resp.raise_for_status()
            data = await resp.json()
        items = data.get("data", [])
        results: List[Anime] = []
        for it in items:
            node = it.get("node", it)
            anime = Anime(
                id=node.get("id"),
                title=node.get("title"),
                url=node.get("url"),
                picture=node.get("main_picture", {}).get("medium"),
                mean=node.get("mean"),
                rank=node.get("rank"),
                episodes=node.get("num_episodes"),
                start_date=node.get("start_season", {}).get("year"),
                synopsis=node.get("synopsis")
            )
            results.append(anime)
        return results

    async def search_character(self, query: str, limit: int = 5) -> List[Character]:
        url = f"{self.BASE_URL}/characters?q={query}&limit={limit}"
        async with self._session.get(url) as resp:
            resp.raise_for_status()
            data = await resp.json()
        items = data.get("data", [])
        results: List[Character] = []
        for item in items:
            node = item.get("node", item)
            character = Character(
                id=node.get("id"),
                name=node.get("name"),
                url=node.get("url"),
                picture=node.get("images", {}).get("jpg", {}).get("image_url"),
                anime_appearances=[anime.get("name") for anime in node.get("anime", [])]
            )
            results.append(character)
        return results

    async def search_voice_actor(self, query: str, limit: int = 5) -> List[VoiceActor]:
        url = f"{self.BASE_URL}/people?q={query}&limit={limit}"
        async with self._session.get(url) as resp:
            resp.raise_for_status()
            data = await resp.json()
        items = data.get("data", [])
        results: List[VoiceActor] = []
        for item in items:
            node = item.get("node", item)
            va = VoiceActor(
                id=node.get("id"),
                name=node.get("name"),
                url=node.get("url"),
                picture=node.get("images", {}).get("jpg", {}).get("image_url"),
                roles=[role.get("role") for role in node.get("voice_acting_roles", [])]
            )
            results.append(va)
        return results

    async def search_studio(self, query: str, limit: int = 5) -> List[Studio]:
        url = f"{self.BASE_URL}/producers?q={query}&limit={limit}"
        async with self._session.get(url) as resp:
            resp.raise_for_status()
            data = await resp.json()
        items = data.get("data", [])
        results: List[Studio] = []
        for item in items:
            node = item.get("node", item)
            studio = Studio(
                id=node.get("id"),
                name=node.get("name"),
                url=node.get("url"),
                picture=None,
                anime_list=[anime.get("name") for anime in node.get("anime", [])]
            )
            results.append(studio)
        return results

    async def schedule(self, day: str) -> ScheduleEntry:
        # MAL v2 may not directly support day-based schedule endpoint publicly; this may require external logic or different endpoint
        # Here’s a placeholder:
        return ScheduleEntry(day=day, anime_list=[])

    async def next_season(self) -> List[Anime]:
        # Placeholder: determine next season year/season_word then call seasonal endpoint
        return []