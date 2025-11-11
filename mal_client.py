import aiohttp
from typing import List
from models import Anime, Manga, Character, VoiceActor, Studio, ScheduleEntry

class MALClient:
    BASE_URL = "https://api.myanimelist.net/v2"

    def __init__(self):
        self._session = None

    async def __aenter__(self):
        self._session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self._session.close()

    async def search_anime(self, query: str, limit: int = 15) -> List[Anime]:
        # TODO: implement search anime logic via API
        return []

    async def search_manga(self, query: str, limit: int = 15) -> List[Manga]:
        # TODO
        return []

    async def seasonal_anime(self, year: int, season: str) -> List[Anime]:
        # TODO
        return []

    async def top(self, kind: str = "anime", limit: int = 10) -> List:
        # TODO: top anime/manga logic
        return []

    async def trending(self, kind: str = "anime", limit: int = 10) -> List:
        # TODO: trending logic
        return []

    async def recommend(self, kind: str = "anime", query: str = None) -> List:
        # TODO: recommendations logic
        return []

    async def info(self, identifier: str, kind: str = "anime") -> object:
        # TODO: fetch detailed info for anime/manga
        return None

    async def search_character(self, query: str, limit: int = 5) -> List[Character]:
        # TODO: character search logic
        return []

    async def search_voice_actor(self, query: str, limit: int = 5) -> List[VoiceActor]:
        # TODO: voice actor logic
        return []

    async def search_studio(self, query: str, limit: int = 5) -> List[Studio]:
        # TODO: studio logic
        return []

    async def schedule(self, day: str) -> ScheduleEntry:
        # TODO: schedule logic for a given day
        return ScheduleEntry(day=day, anime_list=[])

    async def next_season(self) -> List[Anime]:
        # TODO: logic for next season releases
        return []