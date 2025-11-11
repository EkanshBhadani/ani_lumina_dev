from typing import Iterable, Optional, Sequence, Tuple

import discord
from datetime import datetime
import pytz

# Visual theming
EMBED_COLOR = 0x1F8B4C  # change to any hex to change the colors
ERROR_COLOR = 0xE74C3C

def truncate(s: Optional[str], n: int = 256) -> str:
    if not s:
        return ""
    s = str(s)
    return s if len(s) <= n else s[: n - 1] + "…"

def _format_meta(obj: dict) -> str:
    """Build a compact meta line from available fields."""
    parts = []
    # handle both dict-like and attr objects
    get = lambda k: obj.get(k) if isinstance(obj, dict) else getattr(obj, k, None)

    mean = get("mean")
    rank = get("rank")
    episodes = get("episodes")
    chapters = get("chapters")
    volumes = get("volumes")
    status = get("status")

    if mean is not None:
        try:
            parts.append(f"⭐ {mean}")
        except Exception:
            parts.append(f"⭐ {truncate(mean)}")
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

def anime_embed_from_models(title: str, items: Sequence, kind: str = "anime") -> discord.Embed:
    """
    Build a clean embed listing multiple Anime/Manga items.
    items: sequence of objects with attributes: title, url, mean, rank, episodes/chapters, start_date, picture
    """
    embed = discord.Embed(title=truncate(title, 120), color=EMBED_COLOR)
    embed.description = f"Top {len(items)} results from MyAnimeList"

    # set thumbnail to first item's picture if available
    first_picture = None
    if items:
        first_picture = getattr(items[0], "picture", None) or (items[0].get("picture") if isinstance(items[0], dict) else None)
    if first_picture:
        embed.set_thumbnail(url=first_picture)


    for idx, item in enumerate(items, 1):
        name = truncate(getattr(item, "title", None) or (item.get("title") if isinstance(item, dict) else "—"), 80)
        url = getattr(item, "url", None) or (item.get("url") if isinstance(item, dict) else "")
        # meta built from attributes/dict
        objdict = item.__dict__ if hasattr(item, "__dict__") else (item if isinstance(item, dict) else {})
        meta = _format_meta(objdict)

        value_lines = []
        if url:
            value_lines.append(f"[Open on MAL]({url})")
        if meta:
            value_lines.append(meta)
        start_date = getattr(item, "start_date", None) or objdict.get("start_date")
        if start_date:
            value_lines.append(f"Started: {truncate(start_date, 40)}")

        value = "\n".join(value_lines) or "\u200b"
        embed.add_field(name=f"{idx}. {name}", value=value, inline=False)


    tz = pytz.timezone("Asia/Kolkata")
    embed.set_footer(text=f"Data from MyAnimeList • {datetime.now(tz).strftime('%Y-%m-%d %H:%M %Z')}")
    return embed

def single_item_embed(item, kind: str = "anime") -> discord.Embed:
    """
    Build a richer single-item embed (detailed card).
    """
    title = getattr(item, "title", None) or (item.get("title") if isinstance(item, dict) else "—")
    url = getattr(item, "url", None) or (item.get("url") if isinstance(item, dict) else None)
    embed = discord.Embed(title=truncate(title, 180), color=EMBED_COLOR)
    if url:
        embed.url = url

    # Set thumbnail (small) and main image (optional). Prefer thumbnail to keep messages compact.
    picture = getattr(item, "picture", None) or (item.get("picture") if isinstance(item, dict) else None)
    if picture:
        embed.set_thumbnail(url=picture)

    # Compose description lines
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

    tz = pytz.timezone("Asia/Kolkata")
    embed.set_footer(text=f"Data from MyAnimeList • {datetime.now(tz).strftime('%Y-%m-%d %H:%M %Z')}")
    return embed

def error_embed(message: str) -> discord.Embed:
    e = discord.Embed(title="❌ Error", description=message, color=ERROR_COLOR)
    tz = pytz.timezone("Asia/Kolkata")
    e.set_footer(text=f"{datetime.now(tz).strftime('%Y-%m-%d %H:%M %Z')}")
    return e

def get_current_season(dt: Optional[datetime] = None) -> Tuple[int, str]:
    """
    Return (year, season) where season is one of: 'winter', 'spring', 'summer', 'fall'.
    If dt is None uses current date in Asia/Kolkata timezone.
    """
    tz = pytz.timezone("Asia/Kolkata")
    now = dt.astimezone(tz) if dt else datetime.now(tz)
    month = now.month
    year = now.year

    # Define typical anime seasons:
    # Winter: Jan-Mar (1-3), Spring: Apr-Jun (4-6), Summer: Jul-Sep (7-9), Fall: Oct-Dec (10-12)
    if month in (1, 2, 3):
        season = "winter"
        # winter season is same calendar year (e.g., Jan 2025 => winter 2025)
    elif month in (4, 5, 6):
        season = "spring"
    elif month in (7, 8, 9):
        season = "summer"
    else:
        season = "fall"
    return year, season
