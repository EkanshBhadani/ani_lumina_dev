# bot.py
import os
import asyncio
import logging
from dotenv import load_dotenv

import discord
from discord.ext import commands
from aiohttp import web

from mal_client import MALClient
from utils import (
    get_current_season,
    EMBED_COLOR,
    build_item_card_embed,     # NEW: per-item card builder
    error_embed as utils_error # keep local alias if you want to use the utils one
)

# load for local; on Render/host, env vars are injected
load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    logging.critical("DISCORD_TOKEN environment variable is missing.")
    raise SystemExit(1)


def mal_configured() -> bool:
    return bool(os.getenv("MAL_CLIENT_ID"))


# (Optional) small helper to build consistent error embeds locally
def error_embed(message: str) -> discord.Embed:
    try:
        return utils_error(message)
    except Exception:
        e = discord.Embed(title="❌ Error", description=message, color=0xE74C3C)
        return e


intents = discord.Intents.default()
# enable only what you need; Message Content is ON in Dev Portal per your setup
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


# --------- BOT EVENTS ----------
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (id={bot.user.id})")
    # try syncing slash commands (safe to call; if already synced this is quick)
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} application commands.")
    except Exception as e:
        print(f"Command sync failed: {e}")


# --------- helpers for the new layout ----------
def _header_embed(title: str, description: str, thumb_url: str | None = None) -> discord.Embed:
    """Create a clean header embed that sits above the per-item cards."""
    embed = discord.Embed(title=title, description=description, color=EMBED_COLOR)
    if thumb_url:
        embed.set_thumbnail(url=thumb_url)
    return embed


async def _send_cards(interaction: discord.Interaction, header: discord.Embed, items, page_label: str | None = None):
    """
    Sends a header embed + up to 10 item-card embeds in a single message
    (Discord limit: 10 embeds per message; if you ever raise limit, split messages).
    """
    embeds = [header]
    # Start indices at 1; if you implement pagination later, bump the start.
    for i, item in enumerate(items[:10], start=1):
        card = build_item_card_embed(item, index=i, source_label=("Data from MyAnimeList" + (f" • {page_label}" if page_label else "")))
        embeds.append(card)
    await interaction.followup.send(embeds=embeds)


# --------- SLASH COMMANDS ----------
@bot.tree.command(name="ping", description="Check bot latency")
async def ping(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Pong!",
        description=f"Latency: **{round(bot.latency * 1000)} ms**",
        color=EMBED_COLOR,
    )
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="anime", description="Search anime on MAL")
async def anime(interaction: discord.Interaction, query: str):
    if not mal_configured():
        await interaction.response.send_message(
            embed=error_embed(
                "MAL client not configured. Ask the bot admin to set MAL_CLIENT_ID in the host environment."
            ),
            ephemeral=True,
        )
        return

    await interaction.response.defer()
    try:
        async with MALClient() as mal:
            items = await mal.search_anime(query, limit=5)

        if not items:
            await interaction.followup.send(embed=error_embed("No results found."), ephemeral=True)
            return

        # if only one result, show detailed card
        if len(items) == 1:
            await interaction.followup.send(embed=build_item_card_embed(items[0], index=1))
            return

        first_pic = getattr(items[0], "picture", None)
        header = _header_embed(
            title=f"Anime results for “{query}”",
            description=f"Showing {len(items)} result{'s' if len(items)!=1 else ''} from MyAnimeList",
            thumb_url=first_pic,
        )
        await _send_cards(interaction, header, items)
    except Exception as e:
        await interaction.followup.send(embed=error_embed(str(e)))


@bot.tree.command(name="manga", description="Search manga on MAL")
async def manga(interaction: discord.Interaction, query: str):
    if not mal_configured():
        await interaction.response.send_message(
            embed=error_embed(
                "MAL client not configured. Ask the bot admin to set MAL_CLIENT_ID in the host environment."
            ),
            ephemeral=True,
        )
        return

    await interaction.response.defer()
    try:
        async with MALClient() as mal:
            items = await mal.search_manga(query, limit=5)

        if not items:
            await interaction.followup.send(embed=error_embed("No results found."), ephemeral=True)
            return

        if len(items) == 1:
            await interaction.followup.send(embed=build_item_card_embed(items[0], index=1))
            return

        first_pic = getattr(items[0], "picture", None)
        header = _header_embed(
            title=f"Manga results for “{query}”",
            description=f"Showing {len(items)} result{'s' if len(items)!=1 else ''} from MyAnimeList",
            thumb_url=first_pic,
        )
        await _send_cards(interaction, header, items)
    except Exception as e:
        await interaction.followup.send(embed=error_embed(str(e)))


@bot.tree.command(name="airing", description="Top airing anime (MAL ranking)")
async def airing(interaction: discord.Interaction):
    if not mal_configured():
        await interaction.response.send_message(
            embed=error_embed(
                "MAL client not configured. Ask the bot admin to set MAL_CLIENT_ID in the host environment."
            ),
            ephemeral=True,
        )
        return

    await interaction.response.defer()
    try:
        async with MALClient() as mal:
            items = await mal.top_airing_anime(limit=5)

        if not items:
            await interaction.followup.send(embed=error_embed("No airing results found."), ephemeral=True)
            return

        first_pic = getattr(items[0], "picture", None)
        header = _header_embed(
            title="Top Airing Anime",
            description=f"Top {len(items)} picks from MyAnimeList",
            thumb_url=first_pic,
        )
        await _send_cards(interaction, header, items)
    except Exception as e:
        await interaction.followup.send(embed=error_embed(str(e)))


@bot.tree.command(name="trending", description="Trending anime (by popularity)")
async def trending(interaction: discord.Interaction):
    if not mal_configured():
        await interaction.response.send_message(
            embed=error_embed(
                "MAL client not configured. Ask the bot admin to set MAL_CLIENT_ID in the host environment."
            ),
            ephemeral=True,
        )
        return

    await interaction.response.defer()
    try:
        async with MALClient() as mal:
            items = await mal.trending_anime(limit=5)

        if not items:
            await interaction.followup.send(embed=error_embed("No trending results found."), ephemeral=True)
            return

        first_pic = getattr(items[0], "picture", None)
        header = _header_embed(
            title="Trending Anime (Popularity)",
            description=f"Top {len(items)} by popularity on MyAnimeList",
            thumb_url=first_pic,
        )
        await _send_cards(interaction, header, items)
    except Exception as e:
        await interaction.followup.send(embed=error_embed(str(e)))


@bot.tree.command(name="seasonal", description="Current season picks (MAL seasonal)")
async def seasonal(interaction: discord.Interaction, year: int = 0, season: str = ""):
    if not mal_configured():
        await interaction.response.send_message(
            embed=error_embed(
                "MAL client not configured. Ask the bot admin to set MAL_CLIENT_ID in the host environment."
            ),
            ephemeral=True,
        )
        return

    await interaction.response.defer()
    try:
        if not year or not season:
            y, s = get_current_season()
        else:
            y, s = year, season.lower()

        async with MALClient() as mal:
            items = await mal.seasonal(y, s, limit=5)

        if not items:
            await interaction.followup.send(embed=error_embed("No seasonal results found."), ephemeral=True)
            return

        first_pic = getattr(items[0], "picture", None)
        header = _header_embed(
            title=f"{s.title()} {y} — Seasonal",
            description=f"Top {len(items)} picks from MyAnimeList",
            thumb_url=first_pic,
        )
        await _send_cards(interaction, header, items)
    except Exception as e:
        await interaction.followup.send(embed=error_embed(str(e)))


# --------- HEALTH SERVER (for Render Web Service) ----------
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
