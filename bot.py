# bot.py
import os
import asyncio
import logging
from dotenv import load_dotenv

import discord
from discord.ext import commands
from aiohttp import web

# load .env for local dev; Render uses environment variables
load_dotenv()

# ---- Config / env ----
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    logging.critical("DISCORD_TOKEN environment variable is missing.")
    raise SystemExit(1)

# Optional MAL keys (if used elsewhere)
MAL_CLIENT_ID = os.getenv("MAL_CLIENT_ID")
MAL_CLIENT_SECRET = os.getenv("MAL_CLIENT_SECRET")

# ---- Intents ----
intents = discord.Intents.default()
# Enable only what you need:
intents.message_content = True

# ---- Bot setup ----
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (id={bot.user.id})")


# Example application-command (slash) — replace / add your commands
@bot.tree.command(name="ping", description="Check bot latency")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"Pong! {round(bot.latency * 1000)} ms")


# ---- Small aiohttp health server ----
async def health(request):
    return web.Response(text="ok")


async def start_web_app(host: str = "0.0.0.0", port: int = 8080):
    app = web.Application()
    app.add_routes([web.get("/", health), web.get("/health", health)])
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    print(f"Health server started on http://{host}:{port}")


# ---- Main async runner that runs web + bot concurrently ----
async def main():
    # Render sets PORT env var for web services; fallback to 8080 if not present
    port_str = os.getenv("PORT")
    if port_str:
        try:
            port = int(port_str)
        except ValueError:
            port = 8080
    else:
        port = 8080

    # Start health server and bot concurrently
    web_task = asyncio.create_task(start_web_app(port=port))
    # Use bot.start instead of bot.run to run inside this loop
    bot_task = asyncio.create_task(bot.start(TOKEN))

    done, pending = await asyncio.wait(
        [web_task, bot_task], return_when=asyncio.FIRST_EXCEPTION
    )

    # cancel other tasks if one fails
    for task in pending:
        task.cancel()

    # propagate exceptions if any
    for task in done:
        if task.exception():
            raise task.exception()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Shutting down")
