# utils.py
from typing import Iterable, Optional, Sequence
import discord
from datetime import datetime
import pytz

EMBED_COLOR = 0x1F8B4C  # pleasant greenish; pick any hex you like

def truncate(s: Optional[str], n: int = 256) -> str:
    if not s:
        return ""
    return s if len(s) <= n else s[: n - 1] + "…"

def _format_meta(obj: dict) -> str:
    parts = []
    if obj.get("mean") is not None:
        parts.append(f"⭐ {obj['mean']}")
    if obj.get("rank"):
        parts.append(f"#{obj['rank']}")
    if obj.get("episodes"):
        parts.append(f"EP: {obj['episodes']}")
    if obj.get("chapters"):
        parts.append(f"CH: {obj['chapters']}")
    if obj.get("status"):
        parts.append(obj["status"].capitalize())
    return " • ".join(parts) if parts else "—"

def anime_embed_from_models(title: str, items: Sequence, kind: str = "anime") -> discord.Embed:
    """
    items: sequence of dataclass-like objects (Anime or Manga) with attributes:
      - title, url, mean, rank, episodes/chapters, start_date, picture
    """
    embed = discord.Embed(title=truncate(title, 120), color=EMBED_COLOR)
    embed.description = f"Top {len(items)} results from MyAnimeList"

    # set the thumbnail to the first item's picture (if available)
    if items and getattr(items[0], "picture", None):
        embed.set_thumbnail(url=getattr(items[0], "picture"))

    # add fields for each item
    for idx, item in enumerate(items, 1):
        name = truncate(getattr(item, "title", "—"), 80)
        url = getattr(item, "url", "")
        meta = _format_meta(item.__dict__ if hasattr(item, "__dict__") else item)
        # Use markdown link in field name for clickable title (Discord supports markdown links in embed values, not names; put link in value)
        value_lines = []
        if url:
            value_lines.append(f"[Open on MAL]({url})")
        if meta:
            value_lines.append(meta)
        # include start date if present
        if getattr(item, "start_date", None):
            value_lines.append(f"Started: {item.start_date}")
        value = "\n".join(value_lines) or "\u200b"
        embed.add_field(name=f"{idx}. {name}", value=value, inline=False)

    # nicer footer with timezone-aware timestamp
    tz = pytz.timezone("Asia/Kolkata")
    embed.set_footer(text=f"Updated {datetime.now(tz).strftime('%Y-%m-%d %H:%M %Z')}")
    return embed

def single_item_embed(item, kind: str = "anime") -> discord.Embed:
    """
    Build a richer embed for a single Anime/Manga (detailed view).
    """
    title = getattr(item, "title", "—")
    embed = discord.Embed(title=title, color=EMBED_COLOR)
    url = getattr(item, "url", "")
    if url:
        embed.url = url

    # thumbnail or main image
    if getattr(item, "picture", None):
        embed.set_thumbnail(url=getattr(item, "picture"))

    # Compose a concise description from available fields
    lines = []
    if getattr(item, "mean", None) is not None:
        lines.append(f"**Score:** {getattr(item, 'mean')}")
    if getattr(item, "rank", None):
        lines.append(f"**Rank:** #{getattr(item, 'rank')}")
    if getattr(item, "episodes", None):
        lines.append(f"**Episodes:** {getattr(item, 'episodes')}")
    if getattr(item, "chapters", None):
        lines.append(f"**Chapters:** {getattr(item, 'chapters')}")
    if getattr(item, "volumes", None):
        lines.append(f"**Volumes:** {getattr(item, 'volumes')}")
    if getattr(item, "status", None):
        lines.append(f"**Status:** {getattr(item, 'status').capitalize()}")
    if getattr(item, "start_date", None):
        lines.append(f"**Started:** {getattr(item, 'start_date')}")

    if lines:
        embed.description = "\n".join(lines)

    tz = pytz.timezone("Asia/Kolkata")
    embed.set_footer(text=f"Data from MyAnimeList • {datetime.now(tz).strftime('%Y-%m-%d %H:%M %Z')}")
    return embed
