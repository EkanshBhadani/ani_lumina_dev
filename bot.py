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

GUILD_ID = os.getenv("GUILD_ID")  # optional: set while developing to register commands to a guild instantly

def mal_configured() -> bool:
    return bool(os.getenv("MAL_CLIENT_ID"))

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (id={bot.user.id})")
    # If a GUILD_ID is provided, sync commands to that guild for instant availability in that server.
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
        embeds = self.pages[self.current]
        footer_text = f"Page {self.current+1}/{len(self.pages)}"
        for e in embeds:
            # append page info in footer (if exists keep existing text)
            existing = e.footer.text if e.footer and e.footer.text else ""
            e.set_footer(text=f"{existing} • {footer_text}".strip(" • "))
        # use response.edit_message to properly acknowledge the interaction
        await interaction.response.edit_message(embeds=embeds, view=self)

    async def _deny_control(self, interaction: discord.Interaction):
        # used when a non-author tries to use controls
        # respond promptly so Discord does not show "This interaction failed"
        try:
            await interaction.response.send_message("You can't control this pagination session.", ephemeral=True)
        except Exception:
            # ignore if it's already responded somehow
            pass

    async def _is_author(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.author_id

    @discord.ui.button(label="◀ Prev", style=discord.ButtonStyle.secondary)
    async def prev(self, button: discord.ui.Button, interaction: discord.Interaction):
        # check auth
        if not await self._is_author(interaction):
            await self._deny_control(interaction)
            return
        try:
            if self.current > 0:
                self.current -= 1
            await self._update_message(interaction)
        except Exception as exc:
            # guarantee we respond so the interaction doesn't fail
            try:
                await interaction.response.send_message(f"Error updating page: {exc}", ephemeral=True)
            except Exception:
                # fallback: try editing the message directly
                try:
                    await interaction.message.edit(view=self)
                except Exception:
                    pass

    @discord.ui.button(label="Next ▶", style=discord.ButtonStyle.secondary)
    async def next(self, button: discord.ui.Button, interaction: discord.Interaction):
        if not await self._is_author(interaction):
            await self._deny_control(interaction)
            return
        try:
            if self.current < len(self.pages) - 1:
                self.current += 1
            await self._update_message(interaction)
        except Exception as exc:
            try:
                await interaction.response.send_message(f"Error updating page: {exc}", ephemeral=True)
            except Exception:
                try:
                    await interaction.message.edit(view=self)
                except Exception:
                    pass

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        # try to edit the original message to disable buttons (best effort)
        # We don't have the original interaction here; if you need deterministic disabling,
        # store message reference when sending and use it to edit after timeout.
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

        item_embeds = []
        for idx, item in enumerate(items, 1):
            embed = compact_list_item_embed(item, idx)
            item_embeds.append(embed)

        pages_of_embeds = chunk_items(item_embeds, 5)
        view = PaginatorView(pages=pages_of_embeds, author_id=interaction.user.id, timeout=120)

        header = discord.Embed(title=f"Results for “{query}”", description=f"Showing {min(5, len(items))} of {len(items)} results (page 1/{len(pages_of_embeds)})", color=EMBED_COLOR)
        header.set_thumbnail(url=getattr(items[0], "picture", None) or (items[0].get("picture") if isinstance(items[0], dict) else None))
        header.set_footer(text=f"Data from MyAnimeList • Page 1/{len(pages_of_embeds)}")

        to_send = [header] + pages_of_embeds[0]
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