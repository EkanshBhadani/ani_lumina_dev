from typing import Dict, Any, Optional, Tuple, List
import datetime
import discord

def human_readable_kind(kind: str) -> str:
    m = {
        "anime": "Anime",
        "manga": "Manga",
        "people": "Person",
        "character": "Character",
        "studio": "Studio",
        "schedule": "Schedule",
        "next_season": "Next season",
        "top": "Top",
        "trending": "Trending",
    }
    return m.get(kind, kind.title())


def error_embed(message: str) -> discord.Embed:
    embed = discord.Embed(title="❌ Error", description=message, color=0xE74C3C,
                          timestamp=datetime.datetime.now(datetime.timezone.utc))
    return embed


def extract_image_url(data: Dict[str, Any]) -> Optional[str]:
    """
    Try to extract a small thumbnail URL from the MAL response item.
    The actual MAL response shape depends on mal_client. This function should be adapted if necessary.
    """
    if not data:
        return None
    # common keys: 'image_url', 'images' etc
    if "image_url" in data and data["image_url"]:
        return data["image_url"]
    if "images" in data:
        # may have images['jpg']['image_url']
        imgs = data["images"]
        if isinstance(imgs, dict):
            # try common MAL v2 json structure
            for k in ("jpg", "webp"):
                if k in imgs and isinstance(imgs[k], dict) and imgs[k].get("image_url"):
                    return imgs[k]["image_url"]
    # fallback
    return None


def _format_title_and_url(data: Dict[str, Any], kind: str) -> Tuple[str, Optional[str]]:
    """
    Return (title_text, mal_url) for a search result item.
    Keep title_text short.
    """
    if not data:
        return ("Unknown", None)

    # possible shapes: data['title'], data['name']
    title = data.get("title") or data.get("name") or data.get("alternative_title") or "Unknown"

    # MAL v2: may contain 'url' or 'node' etc
    url = data.get("url") or data.get("mal_url")
    # sometimes MAL search returns 'node' or 'entry' with 'url' inside
    if not url:
        for key in ("node", "entry", "anime", "manga"):
            if data.get(key) and isinstance(data[key], dict) and data[key].get("url"):
                url = data[key]["url"]
                break

    # trim extremely long titles
    if len(title) > 80:
        title = title[:77] + "..."
    return (title, url)


def _format_meta_line(data: Dict[str, Any]) -> str:
    """
    Build a compact single-line metadata string (rating, rank, episodes, status, start date).
    Example: "⭐ 8.28 • #325 • EP: 500 • Finished_airing • Started: 2007-02-15"
    """
    parts = []
    # score / rating
    score = data.get("score") or data.get("mean") or data.get("rating")
    if score is not None:
        try:
            parts.append(f"⭐ {float(score):.2f}")
        except Exception:
            parts.append(f"⭐ {score}")

    # rank
    rank = data.get("rank") or data.get("ranking")
    if rank:
        parts.append(f"#{rank}")

    # episodes / volumes / chapters
    eps = data.get("episodes") or data.get("episodes_count") or data.get("ep")
    if eps:
        parts.append(f"EP: {eps}")

    # status
    status = data.get("status") or data.get("publication_status")
    if status:
        parts.append(str(status))

    # started / aired
    started = None
    if "start_date" in data and data["start_date"]:
        started = data["start_date"]
    elif "aired" in data and isinstance(data["aired"], dict) and data["aired"].get("from"):
        started = data["aired"]["from"]
    if started:
        # keep only date part if iso datetime
        if isinstance(started, str) and "T" in started:
            started = started.split("T", 1)[0]
        parts.append(f"Started: {started}")

    return " • ".join(parts)


def embed_from_info(data: Dict[str, Any], kind: str = "anime") -> discord.Embed:
    """
    Build a richer embed for /info command.
    """
    if not data:
        return error_embed("No data returned")

    title = data.get("title") or data.get("name") or "Info"
    url = data.get("url") or data.get("mal_url")
    description = data.get("synopsis") or data.get("summary") or ""
    embed = discord.Embed(title=title, url=url, description=(description[:400] + "..." if description and len(description) > 400 else description),
                          color=0x2E86C1, timestamp=datetime.datetime.now(datetime.timezone.utc))
    thumb = extract_image_url(data)
    if thumb:
        embed.set_thumbnail(url=thumb)

    # add some fields compactly
    score = data.get("score")
    rank = data.get("rank")
    episodes = data.get("episodes")
    status = data.get("status")
    started = None
    if "start_date" in data:
        started = data.get("start_date")
    elif "aired" in data and isinstance(data["aired"], dict):
        started = data["aired"].get("from")
    if score:
        embed.add_field(name="Score", value=str(score), inline=True)
    if rank:
        embed.add_field(name="Rank", value=str(rank), inline=True)
    if episodes:
        embed.add_field(name="Episodes", value=str(episodes), inline=True)
    if status:
        embed.add_field(name="Status", value=str(status), inline=True)
    if started:
        embed.add_field(name="Started", value=str(started), inline=True)

    return embed
