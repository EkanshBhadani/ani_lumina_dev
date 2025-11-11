import os
import asyncio
import logging
from typing import Optional

import discord
from discord.ext import commands
from aiohttp import web

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ani_lumina")

# ---------- Read secrets / config from environment ----------
TOKEN = os.environ.get("DISCORD_TOKEN")  # <- Add your DISCORD_TOKEN in environment (Render secrets)
# MAL credentials: put them in env vars. Example:
#   export MAL_CLIENT_ID="your_mal_client_id"
#   export MAL_CLIENT_SECRET="your_mal_client_secret"
MAL_CLIENT_ID = os.environ.get("MAL_CLIENT_ID")       # <-- Add MAL client id here (env)
MAL_CLIENT_SECRET = os.environ.get("MAL_CLIENT_SECRET")  # <-- Add MAL secret here (env)

# Default port for the tiny web server used so hosting platforms detect a bound port
DEFAULT_PORT = int(os.environ.get("PORT", 8000))


# ---------- Intents and Bot creation ----------
intents = discord.Intents.default()
# enable message content if your bot needs to read message text (only enable if necessary)
# If you enable this, also toggle it in Developer Portal (Privileged Gateway Intents).
intents.message_content = False

# Create Bot. You might have been using commands.Bot or subclass; adapt if needed.
bot = commands.Bot(
    command_prefix="!",  # not used for slash commands, but harmless
    intents=intents,
    application_id=os.environ.get("DISCORD_APP_ID"),  # optional: helps with global command registration
    help_command=None,
)

# Import (or register) your commands and modules here.
# If your project has separate files for commands (e.g., cogs), load them here.
# Example:
# from utils import register_commands
# register_commands(bot)

# If you maintain slash commands or cogs in other files, import them *after* bot creation:
try:
    # If your repo has a file that registers commands automatically when imported,
    # import it here so the commands are attached to `bot`.
    # Example: from commands import load_commands  (uncomment & adapt)
    pass
except Exception:
    logger.exception("Failed to import command modules (this can be fine if you don't have any).")


# ---------- Event handlers ----------
@bot.event
async def on_ready():
    logger.info("Logged in as %s (id: %s)", bot.user, bot.user.id)
    # Sync slash commands to guilds or globally as desired:
    # If you want to sync per-guild quickly during development, pass guild parameter.
    try:
        # Sync global commands (can take ~1 hour to propagate) or
        # to speed up during dev, sync to a test guild:
        # await bot.tree.sync(guild=discord.Object(id=YOUR_GUILD_ID))
        await bot.tree.sync()
        logger.info("Slash commands synced.")
    except Exception:
        logger.exception("Failed to sync commands.")


# ---------- Minimal health web server ----------
async def _make_app() -> web.Application:
    """
    Create a small aiohttp web app with / and /healthz endpoints.
    Render (and other hosts) will detect this open port.
    """
    app = web.Application()

    async def index(req):
        return web.Response(text="Ani Lumina — bot is running")

    async def health(req):
        # Simple health check; you could extend this to return bot status
        return web.json_response({"status": "ok", "bot_user": bot.user.name if bot.user else None})

    app.router.add_get("/", index)
    app.router.add_get("/healthz", health)
    return app


async def _start_web_server(port: int = DEFAULT_PORT) -> web.AppRunner:
    app = await _make_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info("Web server listening on 0.0.0.0:%d", port)
    return runner


# ---------- Main: start web server and bot in same loop ----------
async def main():
    # Validate token early
    if not TOKEN:
        logger.error("DISCORD_TOKEN not found in environment. Set DISCORD_TOKEN and redeploy.")
        raise SystemExit("DISCORD_TOKEN environment variable is required.")

    # Optional: warn if MAL client id missing
    if not MAL_CLIENT_ID:
        logger.warning("MAL_CLIENT_ID not found in environment. Some MAL features may require it.")

    # Start tiny web server (so hosting platform sees a bound port)
    runner = await _start_web_server(DEFAULT_PORT)

    try:
        # Start discord bot (non-blocking inside this same loop)
        # Use bot.start so we can cleanup runner on shutdown
        logger.info("Starting discord bot...")
        await bot.start(TOKEN)
    finally:
        # Clean up the aiohttp runner on shutdown
        logger.info("Stopping web server...")
        await runner.cleanup()


# Allow running the module directly
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted, shutting down...")
    except Exception:
        logger.exception("Fatal error, exiting.")
        raise
