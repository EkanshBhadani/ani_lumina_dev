from typing import Sequence, Optional, List, Tuple
import discord
from datetime import datetime
import pytz

EMBED_COLOR = 0x1F8B4C
ERROR_COLOR = 0xE74C3C

def truncate(s: Optional[str], n: int = 256) -> str:
    if not s:
        return ""
    s = str(s)
    return s if len(s) <= n else s[: n - 1] + "…"

def get_footer_time() -> str:
    tz = pytz.timezone("Asia/Kolkata")
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M %Z")

def error_embed(message: str) -> discord.Embed:
    e = discord.Embed(title="❌ Error", description=message, color=ERROR_COLOR)
    e.set_footer(text=get_footer_time())
    return e

def item_embed(item, idx: int = None) -> discord.Embed:
    """
    Generic embed builder for Anime/Manga.
    If idx provided, prefix numbering.
    """
    title = getattr(item, "title", None) or (item.name if hasattr(item, "name") else "")
    url = getattr(item, "url", None)
    picture = getattr(item, "picture", None)
    embed = discord.Embed(
        title=f"{idx}. {title}" if idx is not None else title,
        color=EMBED_COLOR
    )
    if url:
        embed.url = url
    if picture:
        embed.set_thumbnail(url=picture)

    meta_lines = []
    if hasattr(item, "mean") and item.mean is not None:
        meta_lines.append(f"⭐ {item.mean}")
    if hasattr(item, "rank") and item.rank is not None:
        meta_lines.append(f"#{item.rank}")
    if hasattr(item, "episodes") and item.episodes is not None:
        meta_lines.append(f"Eps: {item.episodes}")
    if hasattr(item, "chapters") and item.chapters is not None:
        meta_lines.append(f"Ch: {item.chapters}")
    if hasattr(item, "volumes") and item.volumes is not None:
        meta_lines.append(f"Vol: {item.volumes}")
    if hasattr(item, "roles") and item.roles:
        meta_lines.append("Roles: " + ", ".join(item.roles))
    if hasattr(item, "anime_appearances") and item.anime_appearances:
        meta_lines.append("Appears In: " + ", ".join(item.anime_appearances))
    embed.description = "\n".join(meta_lines) if meta_lines else "\u200b"
    embed.set_footer(text=get_footer_time())
    return embed

def list_embeds(items: Sequence, title: str, limit: int = 10) -> List[discord.Embed]:
    """
    Build a list of embeds from items with numbering up to limit.
    """
    embeds = []
    for idx, item in enumerate(items[:limit], start=1):
        embeds.append(item_embed(item, idx))
    return embeds