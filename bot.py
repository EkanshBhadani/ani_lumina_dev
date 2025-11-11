# bot.py
import os
import asyncio
import logging
from dotenv import load_dotenv
from typing import Optional

import discord
from discord.ext import commands

from aiohttp import web

import models  # ensure models imported
from mal_client import MALClient
from utils import error_embed, list_embeds, item_embed, EMBED_COLOR

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    logging.critical("DISCORD_TOKEN environment variable is missing.")
    raise SystemExit(1)

GUILD_ID = os.getenv("GUILD_ID")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (id={bot.user.id})")
    try:
        if GUILD_ID:
            guild_obj = discord.Object(id=int(GUILD_ID))
            synced = await bot.tree.sync(guild=guild_obj)
            print(f"Synced {len(synced)} commands to guild {GUILD_ID}.")
        else:
            synced = await bot.tree.sync()
            print(f"Synced {len(synced)} global commands.")
    except Exception as e:
        print("Command sync failed:", e)

# --- Command definitions ---

@bot.tree.command(name="anime", description="Search for an anime")
async def anime(interaction: discord.Interaction, query: str):
    async with MALClient() as client:
        try:
            results = await client.search_anime(query, limit=15)
        except Exception as e:
            await interaction.response.send_message(embed=error_embed(str(e)), ephemeral=True)
            return
    if not results:
        await interaction.response.send_message(embed=error_embed("No results found"), ephemeral=True)
        return
    await interaction.response.send_message(embeds=list_embeds(results, title="Anime results"))

@bot.tree.command(name="manga", description="Search for a manga")
async def manga(interaction: discord.Interaction, query: str):
    async with MALClient() as client:
        try:
            results = await client.search_manga(query, limit=15)
        except Exception as e:
            await interaction.response.send_message(embed=error_embed(str(e)), ephemeral=True)
            return
    if not results:
        await interaction.response.send_message(embed=error_embed("No results found"), ephemeral=True)
        return
    await interaction.response.send_message(embeds=list_embeds(results, title="Manga results"))

@bot.tree.command(name="season", description="Get current anime season list")
async def season(interaction: discord.Interaction):
    async with MALClient() as client:
        try:
            year, season_name = models.get_current_season()  # if you moved this to models
            results = await client.seasonal_anime(year, season_name)
        except Exception as e:
            await interaction.response.send_message(embed=error_embed(str(e)), ephemeral=True)
            return
    if not results:
        await interaction.response.send_message(embed=error_embed("No results found"), ephemeral=True)
        return
    await interaction.response.send_message(embeds=list_embeds(results, title=f"Season {season_name} {year}"))

@bot.tree.command(name="top", description="Get top ranked anime or manga")
async def top(interaction: discord.Interaction, kind: str = "anime", limit: int = 10):
    async with MALClient() as client:
        try:
            results = await client.top(kind=kind, limit=limit)
        except Exception as e:
            await interaction.response.send_message(embed=error_embed(str(e)), ephemeral=True)
            return
    if not results:
        await interaction.response.send_message(embed=error_embed("No results found"), ephemeral=True)
        return
    await interaction.response.send_message(embeds=list_embeds(results, title=f"Top {kind.capitalize()}"))

@bot.tree.command(name="trending", description="Get trending anime or manga")
async def trending(interaction: discord.Interaction, kind: str = "anime", limit: int = 10):
    async with MALClient() as client:
        try:
            results = await client.trending(kind=kind, limit=limit)
        except Exception as e:
            await interaction.response.send_message(embed=error_embed(str(e)), ephemeral=True)
            return
    if not results:
        await interaction.response.send_message(embed=error_embed("No results found"), ephemeral=True)
        return
    await interaction.response.send_message(embeds=list_embeds(results, title=f"Trending {kind.capitalize()}"))

@bot.tree.command(name="recommend", description="Get recommendations for anime or manga")
async def recommend(interaction: discord.Interaction, kind: str = "anime", query: Optional[str] = None):
    async with MALClient() as client:
        try:
            results = await client.recommend(kind=kind, query=query)
        except Exception as e:
            await interaction.response.send_message(embed=error_embed(str(e)), ephemeral=True)
            return
    if not results:
        await interaction.response.send_message(embed=error_embed("No results found"), ephemeral=True)
        return
    await interaction.response.send_message(embeds=list_embeds(results, title=f"Recommendations for {kind.capitalize()}"))

@bot.tree.command(name="info", description="Get detailed info for an anime or manga")
async def info(interaction: discord.Interaction, identifier: str, kind: str = "anime"):
    async with MALClient() as client:
        try:
            details = await client.info(kind=kind, identifier=identifier)
        except Exception as e:
            await interaction.response.send_message(embed=error_embed(str(e)), ephemeral=True)
            return
    if not details:
        await interaction.response.send_message(embed=error_embed("No details found"), ephemeral=True)
        return
    await interaction.response.send_message(embed=item_embed(details))

@bot.tree.command(name="character", description="Search for a character")
async def character(interaction: discord.Interaction, query: str, limit: int = 5):
    async with MALClient() as client:
        try:
            results = await client.search_character(query, limit=limit)
        except Exception as e:
            await interaction.response.send_message(embed=error_embed(str(e)), ephemeral=True)
            return
    if not results:
        await interaction.response.send_message(embed=error_embed("No character found"), ephemeral=True)
        return
    await interaction.response.send_message(embeds=list_embeds(results, title="Character Results"))

@bot.tree.command(name="voiceactor", description="Search for a voice actor (seiyuu)")
async def voiceactor(interaction: discord.Interaction, query: str, limit: int = 5):
    async with MALClient() as client:
        try:
            results = await client.search_voice_actor(query, limit=limit)
        except Exception as e:
            await interaction.response.send_message(embed=error_embed(str(e)), ephemeral=True)
            return
    if not results:
        await interaction.response.send_message(embed=error_embed("No voice actor found"), ephemeral=True)
        return
    await interaction.response.send_message(embeds=list_embeds(results, title="Voice Actor Results"))

@bot.tree.command(name="studio", description="Search for an anime studio / production house")
async def studio(interaction: discord.Interaction, query: str, limit: int = 5):
    async with MALClient() as client:
        try:
            results = await client.search_studio(query, limit=limit)
        except Exception as e:
            await interaction.response.send_message(embed=error_embed(str(e)), ephemeral=True)
            return
    if not results:
        await interaction.response.send_message(embed=error_embed("No studio found"), ephemeral=True)
        return
    await interaction.response.send_message(embeds=list_embeds(results, title="Studio Results"))

@bot.tree.command(name="schedule", description="Get anime airing schedule for a day")
async def schedule(interaction: discord.Interaction, day: Optional[str] = None):
    async with MALClient() as client:
        try:
            target_day = day if day else "today"
            schedule = await client.schedule(target_day)
        except Exception as e:
            await interaction.response.send_message(embed=error_embed(str(e)), ephemeral=True)
            return
    if not schedule.anime_list:
        await interaction.response.send_message(embed=error_embed("No schedule found"), ephemeral=True)
        return
    await interaction.response.send_message(embeds=list_embeds(schedule.anime_list, title=f"Schedule for {schedule.day}"))

@bot.tree.command(name="nextseason", description="List anime releases for next season")
async def nextseason(interaction: discord.Interaction):
    async with MALClient() as client:
        try:
            results = await client.next_season()
        except Exception as e:
            await interaction.response.send_message(embed=error_embed(str(e)), ephemeral=True)
            return
    if not results:
        await interaction.response.send_message(embed=error_embed("No upcoming releases found"), ephemeral=True)
        return
    await interaction.response.send_message(embeds=list_embeds(results, title="Next Season Releases"))

# — health server for readiness
async def health(_request):
    return web.Response(text="ok")

async def start_web_app(host: str = "0.0.0.0", port: int = 8080):
    app = web.Application()
    app.add_routes([web.get("/", health), web.get("/health", health)])
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    print(f"Health server started at http://{host}:{port}")

async def main():
    port = int(os.getenv("PORT", "8080"))
    web_task = asyncio.create_task(start_web_app(port=port))
    bot_task = asyncio.create_task(bot.start(TOKEN))
    done, pending = await asyncio.wait([web_task, bot_task], return_when=asyncio.FIRST_EXCEPTION)
    for t in pending:
        t.cancel()
    for t in done:
        if t.exception():
            raise t.exception()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Shutting down")
