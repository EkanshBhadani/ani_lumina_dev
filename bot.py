# bot.py
import os
import aiohttp
import asyncio
from dotenv import load_dotenv
import discord
from discord import app_commands
from discord.ext import commands

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
DEV_GUILD_ID = int(os.getenv("DEV_GUILD_ID") or 0)

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="/", intents=intents)
tree = bot.tree

# small helper to build an embed for an anime item returned by Jikan
def anime_item_to_embed(item: dict) -> discord.Embed:
    title = item.get("title") or "Unknown"
    url = item.get("url")
    synopsis = item.get("synopsis") or "No synopsis."
    episodes = item.get("episodes", "N/A")
    score = item.get("score", "N/A")
    embed = discord.Embed(title=title, url=url, description=(synopsis[:400] + "...") if len(synopsis)>400 else synopsis)
    embed.add_field(name="Episodes", value=str(episodes), inline=True)
    embed.add_field(name="Score", value=str(score), inline=True)
    # thumbnail (Jikan: images.jpg.image_url)
    img = None
    images = item.get("images")
    if images and isinstance(images, dict):
        jpg = images.get("jpg")
        if jpg:
            img = jpg.get("image_url")
    if img:
        embed.set_thumbnail(url=img)
    return embed

@bot.event
async def setup_hook():
    # create an aiohttp session and attach a MAL client
    bot.http_session = aiohttp.ClientSession()
    from mal_client import MALClient
    bot.mal = MALClient(bot.http_session)

    # register commands to a single dev guild for instant availability
    if DEV_GUILD_ID:
        guild = discord.Object(id=DEV_GUILD_ID)
        # register commands to the guild only
        await tree.sync(guild=guild)
        print(f"Synced commands to guild {DEV_GUILD_ID}")
    else:
        # fallback: global sync (slower)
        await tree.sync()
        print("Synced global commands (may take ~1 hour to appear).")

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (id: {bot.user.id})")

# Ping test
@tree.command(name="ping", description="Check bot responsiveness")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("Pong! 🟢", ephemeral=True)

# Anime search (quick)
@tree.command(name="anime_search", description="Search anime on MAL (Jikan)")
@app_commands.describe(query="Search query (title or keyword)")
async def anime_search(interaction: discord.Interaction, query: str):
    await interaction.response.defer()
    results = await bot.mal.search_anime(query, limit=5)
    if not results:
        await interaction.followup.send("No results found.")
        return
    # Show top result embed and a quick list
    top = results[0]
    embed = anime_item_to_embed(top)
    excerpt = "\n".join([f"**{i+1}.** {r.get('title')}" for i, r in enumerate(results)])
    embed.add_field(name="Top matches", value=excerpt, inline=False)
    await interaction.followup.send(embed=embed)

# graceful shutdown of aiohttp session
async def close_http_session():
    if getattr(bot, "http_session", None):
        await bot.http_session.close()

@bot.event
async def on_disconnect():
    # ensure session closed
    asyncio.create_task(close_http_session())

if __name__ == "__main__":
    if not TOKEN or not DEV_GUILD_ID:
        print("ERROR: Please set DISCORD_TOKEN and DEV_GUILD_ID in .env")
        raise SystemExit(1)
    bot.run(TOKEN)
