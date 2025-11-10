import os
import logging
from dotenv import load_dotenv
import discord
from discord.ext import commands

# Load environment variables
load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    logging.critical("DISCORD_TOKEN environment variable is missing.")
    exit(1)

MAL_CLIENT_ID = os.getenv("MAL_CLIENT_ID")
MAL_CLIENT_SECRET = os.getenv("MAL_CLIENT_SECRET")
# you can check and log if these are missing as well if required

intents = discord.Intents.default()
intents.message_content = True  # enable if you respond to message content

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (id={bot.user.id})")

# Example slash / command — you likely have more
@bot.tree.command(name="ping", description="Check bot latency")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"Pong! {round(bot.latency * 1000)} ms")

# Setup MAL client etc. — if you have a separate module, import it here
# from mal_client import MALClient
# bot.mal = MALClient(...) etc.

if __name__ == "__main__":
    bot.run(TOKEN)