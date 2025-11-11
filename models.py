from dataclasses import dataclass
from typing import Optional, Dict, Any

@dataclass
class Anime:
    id: int
    title: str
    url: str
    mean: Optional[float]
    rank: Optional[int]
    status: Optional[str]
    episodes: Optional[int]
    start_date: Optional[str]
    picture: Optional[str]

@dataclass
class Manga:
    id: int
    title: str
    url: str
    mean: Optional[float]
    rank: Optional[int]
    status: Optional[str]
    chapters: Optional[int]
    volumes: Optional[int]
    start_date: Optional[str]
    picture: Optional[str]

def parse_anime(node: Dict[str, Any]) -> Anime:
    main = node.get("node", node)  # ranking endpoints wrap with {"node": {...}}
    stats = main.get("statistics") or {}
    return Anime(
        id=main["id"],
        title=main.get("title"),
        url=main.get("main_picture", {}).get("medium") and f"https://myanimelist.net/anime/{main['id']}",
        mean=main.get("mean"),
        rank=main.get("rank"),
        status=main.get("status"),
        episodes=main.get("num_episodes"),
        start_date=main.get("start_date"),
        picture=(main.get("main_picture") or {}).get("medium") or (main.get("main_picture") or {}).get("large"),
    )

def parse_manga(node: Dict[str, Any]) -> Manga:
    main = node.get("node", node)
    return Manga(
        id=main["id"],
        title=main.get("title"),
        url=main.get("main_picture", {}).get("medium") and f"https://myanimelist.net/manga/{main['id']}",
        mean=main.get("mean"),
        rank=main.get("rank"),
        status=main.get("status"),
        chapters=main.get("num_chapters"),
        volumes=main.get("num_volumes"),
        start_date=main.get("start_date"),
        picture=(main.get("main_picture") or {}).get("medium") or (main.get("main_picture") or {}).get("large"),
    )
