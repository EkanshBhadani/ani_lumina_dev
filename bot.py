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
    anime_embed_from_models,
    single_item_embed,
    compact_list_item_embed,
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

def mal_configured() -> bool:
    return bool(os.getenv("MAL_CLIENT_ID"))

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (id={bot.user.id})")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} application commands.")
    except Exception as e:
        print(f"Command sync failed: {e}")

# ----- Pagination View -----
class PaginatorView(discord.ui.View):
    def __init__(self, pages: list, author_id: int, timeout: int = 120):
        """
        pages: list of lists of embeds (each inner list contains up to per_page embeds)
        author_id: the user who can interact
        """
        super().__init__(timeout=timeout)
        self.pages = pages
        self.author_id = author_id
        self.current = 0

    async def _update_message(self, interaction: discord.Interaction):
        # edit original message to show current page's embeds
        embeds = self.pages[self.current]
        footer_text = f"Page {self.current+1}/{len(self.pages)}"
        # also set top embed footer (we will update all embeds footers)
        for e in embeds:
            # ensure footer shows page
            e.set_footer(text=f"{e.footer.text if e.footer and e.footer.text else ''} • {footer_text}".strip(" • "))
        await interaction.response.edit_message(embeds=embeds, view=self)

    def _check_user(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            # tell them they can't control it
            asyncio.create_task(interaction.response.send_message("You can't control this pagination session.", ephemeral=True))
            return False
        return True

    @discord.ui.button(label="◀ Prev", style=discord.ButtonStyle.secondary)
    async def prev(self, button: discord.ui.Button, interaction: discord.Interaction):
        if not self._check_user(interaction):
            return
        if self.current <= 0:
            self.current = 0
        else:
            self.current -= 1
        await self._update_message(interaction)

    @discord.ui.button(label="Next ▶", style=discord.ButtonStyle.secondary)
    async def next(self, button: discord.ui.Button, interaction: discord.Interaction):
        if not self._check_user(interaction):
            return
        if self.current >= len(self.pages) - 1:
            self.current = len(self.pages) - 1
        else:
            self.current += 1
        await self._update_message(interaction)

    async def on_timeout(self):
        # disable buttons after timeout
        for item in self.children:
            item.disabled = True
        # try to edit original message to disable UI
        # We cannot access interaction here, but we can attempt to fetch the message if needed.
        # Simpler: do nothing; Render logs will show view expired. If you want, store message reference in view.
        return

# ----- Commands -----
@bot.tree.command(name="anime", description="Search anime on MAL (paged results)")
async def anime(interaction: discord.Interaction, query: str):
    if not mal_configured():
        await interaction.response.send_message(embed=util_error_embed("MAL client not configured. Please set MAL_CLIENT_ID."), ephemeral=True)
        return

    await interaction.response.defer()
    try:
        async with MALClient() as mal:
            # fetch up to 15 results
            items = await mal.search_anime(query, limit=15)
        if not items:
            await interaction.followup.send(embed=util_error_embed("No results found."), ephemeral=True)
            return

        # Build per-item compact embeds (each has its own thumbnail)
        item_embeds = []
        for idx, item in enumerate(items, 1):
            embed = compact_list_item_embed(item, idx)
            item_embeds.append(embed)

        # chunk into pages of 5
        pages_of_embeds = chunk_items(item_embeds, 5)  # list of lists of embeds

        # create view
        view = PaginatorView(pages=pages_of_embeds, author_id=interaction.user.id, timeout=120)

        # send initial page (page 0)
        initial_embeds = pages_of_embeds[0]
        # add a header embed (optional) as first embed with title
        header = discord.Embed(title=f"Results for “{query}”", description=f"Showing {min(5, len(items))} of {len(items)} results (page 1/{len(pages_of_embeds)})", color=EMBED_COLOR)
        header.set_thumbnail(url=getattr(items[0], "picture", None) or (items[0].get("picture") if isinstance(items[0], dict) else None))
        header.set_footer(text=f"Data from MyAnimeList • Page 1/{len(pages_of_embeds)}")
        # combine header + page embeds
        to_send = [header] + initial_embeds

        await interaction.followup.send(embeds=to_send, view=view)
    except Exception as e:
        await interaction.followup.send(embed=util_error_embed(str(e)))

@bot.tree.command(name="manga", description="Search manga on MAL (paged results)")
async def manga(interaction: discord.Interaction, query: str):
    if not mal_configured():
        await interaction.response.send_message(embed=util_error_embed("MAL client not configured. Please set MAL_CLIENT_ID."), ephemeral=True)
        return

    await interaction.response.defer()
    try:
        async with MALClient() as mal:
            items = await mal.search_manga(query, limit=15)
        if not items:
            await interaction.followup.send(embed=util_error_embed("No results found."), ephemeral=True)
            return

        item_embeds = []
        for idx, item in enumerate(items, 1):
            embed = compact_list_item_embed(item, idx)
            item_embeds.append(embed)

        pages_of_embeds = chunk_items(item_embeds, 5)
        view = PaginatorView(pages=pages_of_embeds, author_id=interaction.user.id, timeout=120)

        header = discord.Embed(title=f"Manga results for “{query}”", description=f"Showing {min(5, len(items))} of {len(items)} results (page 1/{len(pages_of_embeds)})", color=EMBED_COLOR)
        header.set_thumbnail(url=getattr(items[0], "picture", None) or (items[0].get("picture") if isinstance(items[0], dict) else None))
        header.set_footer(text=f"Data from MyAnimeList • Page 1/{len(pages_of_embeds)}")

        to_send = [header] + pages_of_embeds[0]
        await interaction.followup.send(embeds=to_send, view=view)
    except Exception as e:
        await interaction.followup.send(embed=util_error_embed(str(e)))

# ------ health server for Render ------
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