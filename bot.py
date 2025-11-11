import os
import asyncio
import logging
from dotenv import load_dotenv
from typing import Optional

import discord
from discord.ext import commands

from aiohttp import web

from mal_client import MALClient
from utils import (
    compact_list_item_embed,
    single_item_embed,
    chunk_items,
    EMBED_COLOR,
    error_embed as util_error_embed,
    get_current_season,
)

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    logging.critical("DISCORD_TOKEN environment variable is missing.")
    raise SystemExit(1)

GUILD_ID = os.getenv("GUILD_ID")  # optional

def mal_configured() -> bool:
    return bool(os.getenv("MAL_CLIENT_ID"))

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
        print(f"Command sync failed: {e}")

@bot.tree.command(name="anime", description="Search anime on MAL")
async def anime(interaction: discord.Interaction, query: str):
    if not mal_configured():
        await interaction.response.send_message(embed=util_error_embed("MAL client not configured."), ephemeral=True)
        return

    await interaction.response.defer()
    try:
        async with MALClient() as mal:
            items = await mal.search_anime(query, limit=15)
        if not items:
            await interaction.followup.send(embed=util_error_embed("No results found."), ephemeral=True)
            return

        item_embeds = [compact_list_item_embed(item, idx+1) for idx, item in enumerate(items)]
        await interaction.followup.send(embeds=item_embeds)
    except Exception as e:
        print("Error in /anime command:", e)
        await interaction.followup.send(embed=util_error_embed(str(e)))

@bot.tree.command(name="manga", description="Search manga on MAL")
async def manga(interaction: discord.Interaction, query: str):
    if not mal_configured():
        await interaction.response.send_message(embed=util_error_embed("MAL client not configured."), ephemeral=True)
        return

    await interaction.response.defer()
    try:
        async with MALClient() as mal:
            items = await mal.search_manga(query, limit=15)
        if not items:
            await interaction.followup.send(embed=util_error_embed("No results found."), ephemeral=True)
            return

        item_embeds = [compact_list_item_embed(item, idx+1) for idx, item in enumerate(items)]
        await interaction.followup.send(embeds=item_embeds)
    except Exception as e:
        print("Error in /manga command:", e)
        await interaction.followup.send(embed=util_error_embed(str(e)))

@bot.tree.command(name="season", description="Get current anime season list")
async def season(interaction: discord.Interaction):
    if not mal_configured():
        await interaction.response.send_message(embed=util_error_embed("MAL client not configured."), ephemeral=True)
        return

    await interaction.response.defer()
    try:
        year, season_name = get_current_season()
        async with MALClient() as mal:
            items = await mal.seasonal_anime(year, season_name)
        if not items:
            await interaction.followup.send(embed=util_error_embed("No seasonal anime found."), ephemeral=True)
            return

        item_embeds = [compact_list_item_embed(item, idx+1) for idx, item in enumerate(items)]
        await interaction.followup.send(embeds=item_embeds)
    except Exception as e:
        print("Error in /season command:", e)
        await interaction.followup.send(embed=util_error_embed(str(e)))

# Add more commands here as needed
# e.g. /trending, /top, /recommend etc.

async def health(_request):
    return web.Response(text="ok")

async def start_web_app(host: str = "0.0.0.0", port: int = 8080):
    app = web.Application()
    app.add_routes([web.get("/", health), web.get("/health", health)])
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    print(f"Health server started on http://{host}:{port}")

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