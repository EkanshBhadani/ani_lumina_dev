from typing import Iterable, Optional
import discord
from datetime import datetime
import pytz

def truncate(s: Optional[str], n: int = 256) -> str:
    if not s:
        return ""
    return s if len(s) <= n else s[: n - 1] + "…"

def anime_embed(title: str, rows: Iterable[dict], kind: str = "anime") -> discord.Embed:
    embed = discord.Embed(title=title)
    for idx, row in enumerate(rows, 1):
        name = row.get("title") or "—"
        score = row.get("mean")
        extra = []
        if score is not None:
            extra.append(f"⭐ {score}")
        if row.get("rank"):
            extra.append(f"#{row['rank']}")
        if row.get("episodes"):
            extra.append(f"EP: {row['episodes']}")
        if row.get("chapters"):
            extra.append(f"CH: {row['chapters']}")
        extras = " | ".join(extra)
        url = row.get("url") or ""
        line = f"{extras}" if extras else ""
        embed.add_field(
            name=f"{idx}. {truncate(name, 60)}",
            value=f"{line}\n{url}",
            inline=False,
        )
    tz = pytz.timezone("Asia/Kolkata")
    embed.set_footer(text=f"Updated {datetime.now(tz).strftime('%Y-%m-%d %H:%M %Z')}")
    return embed

def get_current_season(dt: Optional[datetime] = None):
    dt = dt or datetime.utcnow()
    m = dt.month
    if m in (1, 2, 3):
        return dt.year, "winter"
    if m in (4, 5, 6):
        return dt.year, "spring"
    if m in (7, 8, 9):
        return dt.year, "summer"
    return dt.year, "fall"
