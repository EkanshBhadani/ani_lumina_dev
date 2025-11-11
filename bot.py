import os
import asyncio
import logging
from typing import Optional, List, Dict, Any

import discord
from discord import app_commands
from discord.ext import commands

from mal_client import MALClient
from utils import format_item_embed, friendly_error_embed

# --- logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("ani_lumina")

# --- environment / secrets
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")  # put your discord bot token here
MAL_CLIENT_ID = os.getenv("MAL_CLIENT_ID")  # put your MAL client id here (required for MAL queries)

if not DISCORD_TOKEN:
    log.warning("DISCORD_TOKEN not set in environment. The bot won't be able to login until you set it.")

# Intents: we don't need privileged message content for slash commands
intents = discord.Intents.default()

# Bot client
bot = commands.Bot(command_prefix="/", intents=intents, application_id=None)  # application_id optional
tree = bot.tree

# default config for searches
DEFAULT_LIMIT = 15

# Utility to run MAL queries safely (single shared client)
_mal_client_singleton_lock = asyncio.Lock()
_mal_client_singleton: Optional[MALClient] = None

async def get_mal_client() -> MALClient:
    global _mal_client_singleton
    async with _mal_client_singleton_lock:
        if _mal_client_singleton is None:
            _mal_client_singleton = MALClient(client_id=MAL_CLIENT_ID, cache_ttl=60)
            await _mal_client_singleton.__aenter__()
        return _mal_client_singleton

# On ready: sync commands
@bot.event
async def on_ready():
    log.info(f"Logged in as {bot.user} (id: {bot.user.id})")
    # sync with guilds if needed; here global sync
    try:
        await tree.sync()
        log.info("Slash commands synced.")
    except Exception as e:
        log.exception("Failed to sync commands: %s", e)

# --- Common helper to run a MAL call and return uniform error embed if needed
async def safe_mal_call(coro, *, interaction: Optional[discord.Interaction] = None):
    try:
        return await coro
    except Exception as exc:
        log.exception("MAL call failed: %s", exc)
        if interaction:
            await interaction.response.send_message(embed=friendly_error_embed(str(exc)), ephemeral=True)
        return None

# ------------------------
# Slash commands
# ------------------------

@tree.command(name="anime", description="Search anime by name (returns up to 15 results).")
@app_commands.describe(query="Anime name to search", limit="Maximum results (max 15)")
async def anime(interaction: discord.Interaction, query: str, limit: Optional[int] = 15):
    await interaction.response.defer()
    if limit is None:
        limit = DEFAULT_LIMIT
    limit = max(1, min(15, limit))
    if not MAL_CLIENT_ID:
        await interaction.followup.send(embed=friendly_error_embed("MAL_CLIENT_ID not configured. Add it to your .env."), ephemeral=True)
        return

    client = await get_mal_client()
    data = await safe_mal_call(client.search_anime(query, limit=limit), interaction=interaction)
    if not data:
        return
    items = data.get("data", []) if isinstance(data, dict) else []
    if not items:
        await interaction.followup.send(embed=friendly_error_embed("No anime found."), ephemeral=True)
        return

    # Send consistent embeds for each result (up to limit)
    sent = 0
    for entry in items[:limit]:
        # MAL v2 search returns 'node' inside each data element for anime endpoint
        node = entry.get("node") if isinstance(entry, dict) else entry
        # fetch detailed info if possible (to get larger set of fields)
        anime_id = None
        if isinstance(node, dict):
            anime_id = node.get("id") or node.get("node", {}).get("id")
        if not anime_id and isinstance(entry, dict):
            anime_id = entry.get("id")
        # Try to get detailed info for the item (to have main_picture etc.)
        info = await safe_mal_call(client.info(anime_id, kind="anime"), interaction=interaction) if anime_id else node
        embed = format_item_embed(info or node, kind="anime")
        await interaction.followup.send(embed=embed)
        sent += 1

    if sent == 0:
        await interaction.followup.send(embed=friendly_error_embed("No results to display."), ephemeral=True)

@tree.command(name="manga", description="Search manga by name (returns up to 15 results).")
@app_commands.describe(query="Manga name to search", limit="Maximum results (max 15)")
async def manga(interaction: discord.Interaction, query: str, limit: Optional[int] = 15):
    await interaction.response.defer()
    limit = max(1, min(15, limit if limit is not None else DEFAULT_LIMIT))
    if not MAL_CLIENT_ID:
        await interaction.followup.send(embed=friendly_error_embed("MAL_CLIENT_ID not configured."), ephemeral=True)
        return

    client = await get_mal_client()
    data = await safe_mal_call(client.search_manga(query, limit=limit), interaction=interaction)
    if not data:
        return
    items = data.get("data", []) if isinstance(data, dict) else []
    if not items:
        await interaction.followup.send(embed=friendly_error_embed("No manga found."), ephemeral=True)
        return

    for entry in items[:limit]:
        node = entry.get("node") if isinstance(entry, dict) else entry
        manga_id = node.get("id") if isinstance(node, dict) else None
        info = await safe_mal_call(client.info(manga_id, kind="manga"), interaction=interaction) if manga_id else node
        embed = format_item_embed(info or node, kind="manga")
        await interaction.followup.send(embed=embed)

@tree.command(name="info", description="Get detailed info on an anime/manga by id or name.")
@app_commands.describe(kind="anime or manga", identifier="ID or exact name")
async def info(interaction: discord.Interaction, kind: str = "anime", identifier: str = ""):
    await interaction.response.defer()
    kind = (kind or "anime").lower()
    if kind not in ("anime", "manga"):
        await interaction.followup.send(embed=friendly_error_embed("kind must be 'anime' or 'manga'."), ephemeral=True)
        return
    if not identifier:
        await interaction.followup.send(embed=friendly_error_embed("Please provide an id or name."), ephemeral=True)
        return
    client = await get_mal_client()
    # identifier might be numeric id
    id_value = int(identifier) if identifier.isdigit() else identifier
    data = await safe_mal_call(client.info(id_value, kind=kind), interaction=interaction)
    if not data:
        return
    embed = format_item_embed(data, kind=kind)
    await interaction.followup.send(embed=embed)

@tree.command(name="top", description="Get top ranked anime or manga.")
@app_commands.describe(kind="anime or manga", limit="Number of results (max 15)")
async def top(interaction: discord.Interaction, kind: str = "anime", limit: Optional[int] = 10):
    await interaction.response.defer()
    kind = kind.lower()
    limit = max(1, min(15, limit if limit is not None else 10))
    client = await get_mal_client()
    data = await safe_mal_call(client.top(kind=kind, limit=limit), interaction=interaction)
    if not data:
        return
    items = data.get("data", []) if isinstance(data, dict) else []
    if not items:
        await interaction.followup.send(embed=friendly_error_embed("No results."), ephemeral=True)
        return
    for entry in items[:limit]:
        node = entry.get("node") if isinstance(entry, dict) else entry
        item_id = node.get("id") if isinstance(node, dict) else None
        info = await safe_mal_call(client.info(item_id, kind=kind), interaction=interaction) if item_id else node
        await interaction.followup.send(embed=format_item_embed(info or node, kind=kind))

@tree.command(name="trending", description="Get trending (popular) anime or manga.")
@app_commands.describe(kind="anime or manga", limit="Number of results (max 15)")
async def trending(interaction: discord.Interaction, kind: str = "anime", limit: Optional[int] = 10):
    await interaction.response.defer()
    kind = kind.lower()
    limit = max(1, min(15, limit if limit is not None else 10))
    client = await get_mal_client()
    data = await safe_mal_call(client.trending(kind=kind, limit=limit), interaction=interaction)
    if not data:
        return
    items = data.get("data", []) if isinstance(data, dict) else []
    for entry in items[:limit]:
        node = entry.get("node") if isinstance(entry, dict) else entry
        item_id = node.get("id") if isinstance(node, dict) else None
        info = await safe_mal_call(client.info(item_id, kind=kind), interaction=interaction) if item_id else node
        await interaction.followup.send(embed=format_item_embed(info or node, kind=kind))

@tree.command(name="season", description="Get current season anime.")
@app_commands.describe(limit="Max results (max 15)")
async def season(interaction: discord.Interaction, limit: Optional[int] = 15):
    await interaction.response.defer()
    limit = max(1, min(15, limit if limit is not None else DEFAULT_LIMIT))
    client = await get_mal_client()
    data = await safe_mal_call(client.current_season(limit=limit), interaction=interaction)
    if not data:
        return
    items = data.get("data", []) if isinstance(data, dict) else []
    for entry in items[:limit]:
        node = entry.get("node") if isinstance(entry, dict) else entry
        item_id = node.get("id") if isinstance(node, dict) else None
        info = await safe_mal_call(client.info(item_id, kind="anime"), interaction=interaction) if item_id else node
        await interaction.followup.send(embed=format_item_embed(info or node, kind="anime"))

@tree.command(name="nextseason", description="Show anime planned for next season.")
@app_commands.describe(limit="Max results (max 15)")
async def nextseason(interaction: discord.Interaction, limit: Optional[int] = 15):
    await interaction.response.defer()
    limit = max(1, min(15, limit if limit is not None else DEFAULT_LIMIT))
    client = await get_mal_client()
    data = await safe_mal_call(client.next_season(limit=limit), interaction=interaction)
    if not data:
        return
    items = data.get("data", []) if isinstance(data, dict) else []
    for entry in items[:limit]:
        node = entry.get("node") if isinstance(entry, dict) else entry
        item_id = node.get("id") if isinstance(node, dict) else None
        info = await safe_mal_call(client.info(item_id, kind="anime"), interaction=interaction) if item_id else node
        await interaction.followup.send(embed=format_item_embed(info or node, kind="anime"))

@tree.command(name="recommend", description="Get recommendations related to an anime/manga (by id or name).")
@app_commands.describe(kind="anime or manga", identifier="ID or exact name", limit="Max results")
async def recommend(interaction: discord.Interaction, kind: str = "anime", identifier: str = "", limit: Optional[int] = 10):
    await interaction.response.defer()
    if not identifier:
        await interaction.followup.send(embed=friendly_error_embed("Provide an id or name to recommend for."), ephemeral=True)
        return
    client = await get_mal_client()
    id_val = int(identifier) if identifier.isdigit() else identifier
    data = await safe_mal_call(client.recommend(kind=kind, id_or_name=id_val, limit=limit), interaction=interaction)
    if not data:
        return
    items = data.get("data", []) if isinstance(data, dict) else []
    if not items:
        await interaction.followup.send(embed=friendly_error_embed("No recommendations found."), ephemeral=True)
        return
    for entry in items[:max(1, limit or 1)]:
        # recommendation structures vary; try to extract node
        rec = entry.get("node") if isinstance(entry, dict) else entry
        await interaction.followup.send(embed=format_item_embed(rec, kind=kind))

# ----- additional search commands -----
@tree.command(name="character", description="Search characters by name.")
@app_commands.describe(query="Character name", limit="Max results (max 15)")
async def character(interaction: discord.Interaction, query: str, limit: Optional[int] = 10):
    await interaction.response.defer()
    client = await get_mal_client()
    data = await safe_mal_call(client.search_character(query, limit=limit), interaction=interaction)
    if not data:
        return
    items = data.get("data", []) if isinstance(data, dict) else []
    if not items:
        await interaction.followup.send(embed=friendly_error_embed("No characters found."), ephemeral=True)
        return
    for entry in items[:limit]:
        node = entry.get("node") if isinstance(entry, dict) else entry
        await interaction.followup.send(embed=format_item_embed(node, kind="character"))

@tree.command(name="voiceactor", description="Search voice actors / people.")
@app_commands.describe(query="Voice actor name", limit="Max results (max 15)")
async def voiceactor(interaction: discord.Interaction, query: str, limit: Optional[int] = 10):
    await interaction.response.defer()
    client = await get_mal_client()
    data = await safe_mal_call(client.search_people(query, limit=limit), interaction=interaction)
    if not data:
        return
    items = data.get("data", []) if isinstance(data, dict) else []
    for entry in items[:limit]:
        node = entry.get("node") if isinstance(entry, dict) else entry
        await interaction.followup.send(embed=format_item_embed(node, kind="person"))

@tree.command(name="studio", description="Search production house / studio.")
@app_commands.describe(query="Studio or producer name", limit="Max results (max 15)")
async def studio(interaction: discord.Interaction, query: str, limit: Optional[int] = 10):
    await interaction.response.defer()
    client = await get_mal_client()
    data = await safe_mal_call(client.search_studio(query, limit=limit), interaction=interaction)
    if not data:
        return
    items = data.get("data", []) if isinstance(data, dict) else []
    for entry in items[:limit]:
        node = entry.get("node") if isinstance(entry, dict) else entry
        await interaction.followup.send(embed=format_item_embed(node, kind="studio"))

@tree.command(name="schedule", description="Show anime schedule (best-effort from seasonal data).")
@app_commands.describe(day="Optional weekday to filter (monday..sunday)", limit="Max results (max 50)")
async def schedule(interaction: discord.Interaction, day: Optional[str] = None, limit: Optional[int] = 50):
    await interaction.response.defer()
    client = await get_mal_client()
    data = await safe_mal_call(client.schedule(day=day, limit=limit), interaction=interaction)
    if not data:
        return
    items = data.get("data", []) if isinstance(data, dict) else []
    if not items:
        await interaction.followup.send(embed=friendly_error_embed("No schedule data found."), ephemeral=True)
        return
    for entry in items[:limit]:
        node = entry.get("node") if isinstance(entry, dict) else entry
        info = await safe_mal_call(client.info(node.get("id"), kind="anime"), interaction=interaction) if isinstance(node, dict) else node
        await interaction.followup.send(embed=format_item_embed(info or node, kind="anime"))

# fallback error handler
@bot.event
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    log.exception("App command error: %s", error)
    try:
        await interaction.response.send_message(embed=friendly_error_embed(str(error)), ephemeral=True)
    except Exception:
        log.exception("Failed to send error message to user.")

# run
if __name__ == "__main__":
    if not DISCORD_TOKEN:
        log.error("DISCORD_TOKEN missing — cannot start bot.")
    else:
        bot.run(DISCORD_TOKEN)
