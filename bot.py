import os
import logging
import datetime
import asyncio
from typing import List, Dict, Any, Optional

import discord
from discord import app_commands

# local modules — assumed in repo
import mal_client
import utils

# logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ani_lumina")

# Load env (if using python-dotenv locally)
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
MAL_CLIENT_ID = os.getenv("MAL_CLIENT_ID")  # recommended to set in env

# If you want to hardcode MAL client id for quick testing (not recommended):
# os.environ["MAL_CLIENT_ID"] = "PASTE_CLIENT_ID_HERE"  # <-- add client id here (not recommended)

if not DISCORD_TOKEN:
    logger.error("DISCORD_TOKEN is not set. Put your Discord bot token in DISCORD_TOKEN env var.")
    raise SystemExit("Missing DISCORD_TOKEN environment variable")

intents = discord.Intents.none()  # minimal intents for slash commands
# if you need message content or member intents, enable here and in Discord Developer Portal
# intents.message_content = True

bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)


def compact_embed_for_results(kind: str, query: str, results: List[Dict[str, Any]]) -> discord.Embed:
    """
    Build a compact embed listing up to len(results) items. Small thumbnail (first result).
    Each result becomes an embed field with short lines.
    """
    title = f"{utils.human_readable_kind(kind)} results for “{query}”"
    embed = discord.Embed(title=title, color=0x1DB954, timestamp=datetime.datetime.now(datetime.timezone.utc))
    embed.set_footer(text="Data from MyAnimeList")
    if not results:
        embed.description = f"❌ No results found."
        return embed

    # first result thumbnail (small)
    first_img = utils.extract_image_url(results[0])
    if first_img:
        # use thumbnail (small)
        embed.set_thumbnail(url=first_img)

    # Add up to 15 results — each as a field (compact)
    for idx, item in enumerate(results[:15], start=1):
        # name and URL
        title_line, mal_url = utils._format_title_and_url(item, kind)
        # meta lines: rating, rank, episodes, status, start date
        meta = utils._format_meta_line(item)
        # short description lines
        value_lines = []
        if meta:
            value_lines.append(meta)
        if mal_url:
            value_lines.append(f"[Open on MAL]({mal_url})")
        # ensure short field values
        field_value = "\n".join(value_lines) or "\u200b"
        # field name: "1. Title"
        field_name = f"{idx}. {title_line}"
        embed.add_field(name=field_name, value=field_value, inline=False)

    return embed


@tree.command(name="anime", description="Search anime on MAL (compact results)")
@app_commands.describe(query="Anime name to search", limit="Max results to fetch (max 15)")
async def anime(interaction: discord.Interaction, query: str, limit: Optional[int] = 15):
    await interaction.response.defer(thinking=True)
    try:
        limit = max(1, min(15, limit or 15))
        results = await mal_client.search("anime", query, limit=limit)
        embed = compact_embed_for_results("anime", query, results)
        await interaction.followup.send(embed=embed)
    except Exception as e:
        logger.exception("Error in /anime")
        await interaction.followup.send(embed=utils.error_embed(str(e)))


@tree.command(name="manga", description="Search manga on MAL (compact results)")
@app_commands.describe(query="Manga name to search", limit="Max results to fetch (max 15)")
async def manga(interaction: discord.Interaction, query: str, limit: Optional[int] = 15):
    await interaction.response.defer(thinking=True)
    try:
        limit = max(1, min(15, limit or 15))
        results = await mal_client.search("manga", query, limit=limit)
        embed = compact_embed_for_results("manga", query, results)
        await interaction.followup.send(embed=embed)
    except Exception as e:
        logger.exception("Error in /manga")
        await interaction.followup.send(embed=utils.error_embed(str(e)))


@tree.command(name="info", description="Get info about an anime or manga by id or url")
@app_commands.describe(kind="Kind (anime/manga)", identifier="id or url or title")
async def info(interaction: discord.Interaction, identifier: str, kind: str = "anime"):
    """
    NOTE: signature uses identifier first to avoid positional/default mismatch.
    """
    await interaction.response.defer(thinking=True)
    try:
        data = await mal_client.info(identifier, kind=kind)
        embed = utils.embed_from_info(data, kind=kind)
        await interaction.followup.send(embed=embed)
    except Exception as e:
        logger.exception("Error in /info")
        await interaction.followup.send(embed=utils.error_embed(str(e)))


# Additional commands you requested (character, staff/voice actor, studio, schedule, nextseason)
@tree.command(name="character", description="Search character on MAL")
@app_commands.describe(query="Character name to search", limit="Max results to fetch (max 10)")
async def character(interaction: discord.Interaction, query: str, limit: Optional[int] = 5):
    await interaction.response.defer(thinking=True)
    try:
        limit = max(1, min(10, limit or 5))
        results = await mal_client.search("character", query, limit=limit)
        embed = compact_embed_for_results("character", query, results)
        await interaction.followup.send(embed=embed)
    except Exception as e:
        logger.exception("Error in /character")
        await interaction.followup.send(embed=utils.error_embed(str(e)))


@tree.command(name="voiceactor", description="Search voice actor / seiyuu on MAL")
@app_commands.describe(query="Voice actor name to search", limit="Max results to fetch (max 10)")
async def voiceactor(interaction: discord.Interaction, query: str, limit: Optional[int] = 5):
    await interaction.response.defer(thinking=True)
    try:
        limit = max(1, min(10, limit or 5))
        results = await mal_client.search("people", query, limit=limit)
        embed = compact_embed_for_results("people", query, results)
        await interaction.followup.send(embed=embed)
    except Exception as e:
        logger.exception("Error in /voiceactor")
        await interaction.followup.send(embed=utils.error_embed(str(e)))


@tree.command(name="studio", description="Search studios / production houses on MAL")
@app_commands.describe(query="Studio name to search", limit="Max results to fetch (max 10)")
async def studio(interaction: discord.Interaction, query: str, limit: Optional[int] = 5):
    await interaction.response.defer(thinking=True)
    try:
        limit = max(1, min(10, limit or 5))
        results = await mal_client.search("studio", query, limit=limit)
        embed = compact_embed_for_results("studio", query, results)
        await interaction.followup.send(embed=embed)
    except Exception as e:
        logger.exception("Error in /studio")
        await interaction.followup.send(embed=utils.error_embed(str(e)))


@tree.command(name="schedule", description="Show anime schedule for a day (e.g. monday)")
@app_commands.describe(day="Day name (monday, tuesday, ...)")
async def schedule(interaction: discord.Interaction, day: str = "today"):
    await interaction.response.defer(thinking=True)
    try:
        results = await mal_client.schedule(day)
        embed = compact_embed_for_results("schedule", day, results)
        await interaction.followup.send(embed=embed)
    except Exception as e:
        logger.exception("Error in /schedule")
        await interaction.followup.send(embed=utils.error_embed(str(e)))


@tree.command(name="nextseason", description="List animes planned for the next season")
async def nextseason(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    try:
        results = await mal_client.next_season()
        embed = compact_embed_for_results("next_season", "next season", results)
        await interaction.followup.send(embed=embed)
    except Exception as e:
        logger.exception("Error in /nextseason")
        await interaction.followup.send(embed=utils.error_embed(str(e)))


@bot.event
async def on_ready():
    logger.info(f"Logged in as {bot.user} (id: {bot.user.id})")
    # Sync commands to your application (global). For development, consider syncing to a guild.
    try:
        await tree.sync()
        logger.info("Slash commands synced.")
    except Exception:
        logger.exception("Failed to sync commands.")


if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
