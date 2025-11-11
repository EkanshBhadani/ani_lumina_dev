from typing import Optional, List

class Anime:
    def __init__(self, id: int, title: str, url: str, picture: Optional[str], mean: Optional[float], rank: Optional[int], episodes: Optional[int], start_date: Optional[str], synopsis: Optional[str]):
        self.id = id
        self.title = title
        self.url = url
        self.picture = picture
        self.mean = mean
        self.rank = rank
        self.episodes = episodes
        self.start_date = start_date
        self.synopsis = synopsis

class Manga:
    def __init__(self, id: int, title: str, url: str, picture: Optional[str], mean: Optional[float], rank: Optional[int], chapters: Optional[int], volumes: Optional[int], start_date: Optional[str], synopsis: Optional[str]):
        self.id = id
        self.title = title
        self.url = url
        self.picture = picture
        self.mean = mean
        self.rank = rank
        self.chapters = chapters
        self.volumes = volumes
        self.start_date = start_date
        self.synopsis = synopsis

class Character:
    def __init__(self, id: int, name: str, url: str, picture: Optional[str], anime_appearances: List[str]):
        self.id = id
        self.name = name
        self.url = url
        self.picture = picture
        self.anime_appearances = anime_appearances

class VoiceActor:
    def __init__(self, id: int, name: str, url: str, picture: Optional[str], roles: List[str]):
        self.id = id
        self.name = name
        self.url = url
        self.picture = picture
        self.roles = roles

class Studio:
    def __init__(self, id: int, name: str, url: str, picture: Optional[str], anime_list: List[str]):
        self.id = id
        self.name = name
        self.url = url
        self.picture = picture
        self.anime_list = anime_list

class ScheduleEntry:
    def __init__(self, day: str, anime_list: List[Anime]):
        self.day = day
        self.anime_list = anime_list