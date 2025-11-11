from typing import Any, Dict, Optional, Tuple
import discord

def _safe_get_picture(data: Dict[str, Any]) -> Optional[str]:
    """
    MAL v2 often provides pictures under 'main_picture': {"medium": "...", "large": "..."}
    But depending on endpoint, shape may vary. Try common keys.
    """
    if not isinstance(data, dict):
        return None
    pic = data.get("main_picture") or data.get("image") or data.get("picture") or data.get("images")
    if isinstance(pic, dict):
        for k in ("large", "medium", "small", "image_url", "jpg", "webp"):
            if isinstance(pic.get(k), str):
                return pic.get(k)
        for val in pic.values():
            if isinstance(val, dict):
                for sub in ("large", "medium", "url"):
                    if isinstance(val.get(sub), str):
                        return val.get(sub)
    if isinstance(pic, str):
        return pic
    return None

def _format_title_and_url(data: Dict[str, Any], kind: str) -> Tuple[str, Optional[str]]:
    """Return (display_title, url)"""
    if not data:
        return ("Unknown", None)
    title = data.get("title") or data.get("name") or data.get("node", {}).get("title") or data.get("node", {}).get("name")
    item_id = data.get("id") or (data.get("node") and data.get("node").get("id"))
    url = None
    if item_id:
        if kind == "anime" or kind == "manga":
            url = f"https://myanimelist.net/{kind}/{item_id}"
        elif kind == "character":
            url = f"https://myanimelist.net/character/{item_id}"
        elif kind in ("person", "voiceactor"):
            url = f"https://myanimelist.net/people/{item_id}"
        elif kind in ("studio", "producer"):
            url = f"https://myanimelist.net/anime/producer/{item_id}"
        else:
            url = f"https://myanimelist.net/{kind}/{item_id}"
    return (title or "Unknown", url)

def format_item_embed(data: Dict[str, Any], kind: str = "anime") -> discord.Embed:
    """
    Build a clean embed for any MAL item type. Works for anime, manga, character, person, studio.
    """
    title, url = _format_title_and_url(data or {}, kind)
    description = data.get("synopsis") or data.get("about") or data.get("description") or ""
    embed = discord.Embed(title=title, description=(description[:400] + "...") if description and len(description) > 400 else description, color=0x7C3AED)
    if url:
        embed.url = url

    pic = _safe_get_picture(data or {})
    if pic:
        embed.set_thumbnail(url=pic)

    def add_field_if(keyname, value):
        if value:
            embed.add_field(name=keyname, value=str(value), inline=True)

    if kind in ("anime",):
        add_field_if("Type", data.get("media_type") or data.get("type"))
        add_field_if("Episodes", data.get("num_episodes"))
        add_field_if("Status", data.get("status"))
        add_field_if("Score", data.get("mean") or data.get("score"))
        add_field_if("Rank", data.get("rank"))
        add_field_if("Start", data.get("start_date"))
    elif kind in ("manga",):
        add_field_if("Type", data.get("media_type") or data.get("type"))
        add_field_if("Chapters", data.get("num_chapters"))
        add_field_if("Volumes", data.get("num_volumes"))
        add_field_if("Status", data.get("status"))
        add_field_if("Score", data.get("mean") or data.get("score"))
        add_field_if("Rank", data.get("rank"))
    elif kind in ("character",):
        add_field_if("Japanese", data.get("name"))
    elif kind in ("person", "voiceactor"):
        add_field_if("Name", data.get("name"))
    elif kind in ("studio", "producer"):
        add_field_if("Name", data.get("name"))

    item_id = data.get("id") or (data.get("node") and data.get("node").get("id"))
    if item_id:
        embed.set_footer(text=f"ID: {item_id} • Powered by MyAnimeList")
    else:
        embed.set_footer(text="Powered by MyAnimeList")

    return embed

def friendly_error_embed(message: str) -> discord.Embed:
    em = discord.Embed(title="Error", description=message, color=0xE11D48)
    return em
