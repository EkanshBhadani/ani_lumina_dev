# utils.py
from typing import Iterable, Optional, Sequence, Tuple, List
import discord
from datetime import datetime
import pytz

# Visual theming
EMBED_COLOR = 0x1F8B4C  # change if you prefer
ERROR_COLOR = 0xE74C3C

def truncate(s: Optional[str], n: int = 256) -> str:
    if not s:
        return ""
    s = str(s)
    return s if len(s) <= n else s[: n - 1] + "…"

def _format_meta(obj: dict) -> str:
    parts = []
    mean = obj.get("mean")
    rank = obj.get("rank")
    episodes = obj.get("episodes")
    chapters = obj.get("chapters")
    volumes = obj.get("volumes")
    status = obj.get("status")

    if mean is not None:
        parts.append(f"⭐ {mean}")
    if rank:
        parts.append(f"#{rank}")
    if episodes:
        parts.append(f"EP: {episodes}")
    if chapters:
        parts.append(f"CH: {chapters}")
    if volumes:
        parts.append(f"VOL: {volumes}")
    if status:
        parts.append(str(status).capitalize())
    return " • ".join(parts) if parts else "—"

def get_footer_time() -> str:
    tz = pytz.timezone("Asia/Kolkata")
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M %Z")

def compact_list_item_embed(item, idx: int) -> discord.Embed:
    """
    Compact embed used for listing results on a page. Each item gives its own embed with thumbnail.
    idx: 1-based index (for numbering)
    """
    title = getattr(item, "title", None) or (item.get("title") if isinstance(item, dict) else "—")
    url = getattr(item, "url", None) or (item.get("url") if isinstance(item, dict) else None)
    objdict = item.__dict__ if hasattr(item, "__dict__") else (item if isinstance(item, dict) else {})
    embed = discord.Embed(title=f"{idx}. {truncate(title, 80)}", color=EMBED_COLOR)
    if url:
        embed.url = url

    picture = objdict.get("picture")
    if picture:
        embed.set_thumbnail(url=picture)

    meta = _format_meta(objdict)
    lines = []
    if meta:
        lines.append(meta)
    if objdict.get("start_date"):
        lines.append(f"Started: {truncate(objdict.get('start_date'), 30)}")
    synopsis = objdict.get("synopsis")
    if synopsis:
        lines.append(truncate(synopsis, 200))

    embed.description = "\n".join(lines) if lines else "\u200b"
    embed.set_footer(text=f"Data from MyAnimeList • {get_footer_time()}")
    return embed

def single_item_embed(item, kind: str = "anime") -> discord.Embed:
    """
    Detailed embed for a single result.
    """
    title = getattr(item, "title", None) or (item.get("title") if isinstance(item, dict) else "—")
    url = getattr(item, "url", None) or (item.get("url") if isinstance(item, dict) else None)
    embed = discord.Embed(title=truncate(title, 180), color=EMBED_COLOR)
    if url:
        embed.url = url

    picture = getattr(item, "picture", None) or (item.get("picture") if isinstance(item, dict) else None)
    if picture:
        embed.set_thumbnail(url=picture)

    objdict = item.__dict__ if hasattr(item, "__dict__") else (item if isinstance(item, dict) else {})
    lines = []
    mean = objdict.get("mean")
    if mean is not None:
        lines.append(f"**Score:** {mean}")
    if objdict.get("rank"):
        lines.append(f"**Rank:** #{objdict.get('rank')}")
    if objdict.get("episodes"):
        lines.append(f"**Episodes:** {objdict.get('episodes')}")
    if objdict.get("chapters"):
        lines.append(f"**Chapters:** {objdict.get('chapters')}")
    if objdict.get("volumes"):
        lines.append(f"**Volumes:** {objdict.get('volumes')}")
    if objdict.get("status"):
        lines.append(f"**Status:** {str(objdict.get('status')).capitalize()}")
    if objdict.get("start_date"):
        lines.append(f"**Started:** {truncate(objdict.get('start_date'), 30)}")

    synopsis = objdict.get("synopsis") or getattr(item, "synopsis", None)
    if synopsis:
        lines.append("\n" + truncate(synopsis, 700))

    if lines:
        embed.description = "\n".join(lines)

    embed.set_footer(text=f"Data from MyAnimeList • {get_footer_time()}")
    return embed

def error_embed(message: str) -> discord.Embed:
    e = discord.Embed(title="❌ Error", description=message, color=ERROR_COLOR)
    e.set_footer(text=f"{get_footer_time()}")
    return e

def get_current_season(dt: Optional[datetime] = None) -> Tuple[int, str]:
    tz = pytz.timezone("Asia/Kolkata")
    now = dt.astimezone(tz) if dt else datetime.now(tz)
    month = now.month
    year = now.year

    if month in (1, 2, 3):
        season = "winter"
    elif month in (4, 5, 6):
        season = "spring"
    elif month in (7, 8, 9):
        season = "summer"
    else:
        season = "fall"
    return year, season

def chunk_items(items: Sequence, per_page: int = 5) -> List[List]:
    """Split sequence into pages (list of lists)."""
    pages = []
    for i in range(0, len(items), per_page):
        pages.append(list(items[i:i+per_page]))
    return pages