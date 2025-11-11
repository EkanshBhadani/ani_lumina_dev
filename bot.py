# bot.py
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

# ----- Robust Paginator View -----
class PaginatorView(discord.ui.View):
    def __init__(self, pages: list, author_id: int, header: discord.Embed, timeout: int = 120):
        """
        pages: list of lists of embeds (each inner list contains up to per_page embeds)
        author_id: the user who can interact
        header: header embed to show on every page (kept as first embed)
        """
        super().__init__(timeout=timeout)
        self.pages = pages
        self.author_id = author_id
        self.current = 0
        self.header = header
        self.message: Optional[discord.Message] = None

    def _page_embeds(self, page_index: int):
        """
        Build full embed list for a page: header (with updated footer) + the page's item embeds.
        Returns list[discord.Embed]
        """
        page_count = len(self.pages)
        header_copy = discord.Embed.from_dict(self.header.to_dict())
        header_footer_text = header_copy.footer.text or ""
        header_copy.set_footer(text=f"{header_footer_text} • Page {page_index+1}/{page_count}".strip(" • "))
        embeds = [header_copy]
        embeds.extend(self.pages[page_index])
        return embeds

    async def _deny_control(self, interaction: discord.Interaction):
        # reply ephemeral to non-author trying to control pagination
        try:
            await interaction.response.send_message("You can't control this pagination session.", ephemeral=True)
        except Exception:
            # if already responded, ignore
            pass

    async def _is_author(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.author_id

    async def _edit_message(self, interaction: discord.Interaction, page_index: int):
        """
        Safely acknowledge the interaction and edit the message attached to this view.
        Uses defer(update=True) and edits stored message for reliability.
        """
        new_embeds = self._page_embeds(page_index)
        # Acknowledge that we will update the original message
        try:
            await interaction.response.defer(update=True)
        except Exception:
            # possibly already acknowledged; continue
            pass

        # Try to edit the stored message (preferred)
        try:
            if self.message:
                await self.message.edit(embeds=new_embeds, view=self)
            else:
                # fallback to editing the interaction message
                await interaction.message.edit(embeds=new_embeds, view=self)
        except Exception as exc:
            # Try using edit_message on response (rare path)
            try:
                await interaction.response.edit_message(embeds=new_embeds, view=self)
            except Exception as exc2:
                # Log both exceptions to stdout (visible in your service logs)
                print("Failed to edit message using all methods:", exc, exc2)
                # Attempt to send ephemeral error so user sees something and interaction is acknowledged
                try:
                    await interaction.followup.send("Failed to update page — check logs.", ephemeral=True)
                except Exception:
                    pass

    @discord.ui.button(label="◀ Prev", style=discord.ButtonStyle.secondary)
    async def prev(self, button: discord.ui.Button, interaction: discord.Interaction):
        # Only the author can change page (change logic here if you want to allow others)
        if not await self._is_author(interaction):
            await self._deny_control(interaction)
            return
        if self.current > 0:
            self.current -= 1
        await self._edit_message(interaction, self.current)

    @discord.ui.button(label="Next ▶", style=discord.ButtonStyle.secondary)
    async def next(self, button: discord.ui.Button, interaction: discord.Interaction):
        if not await self._is_author(interaction):
            await self._deny_control(interaction)
            return
        if self.current < len(self.pages) - 1:
            self.current += 1
        await self._edit_message(interaction, self.current)

    async def on_timeout(self):
        # disable buttons on timeout (best-effort)
        for child in self.children:
            child.disabled = True
        try:
            if self.message:
                await self.message.edit(view=self)
        except Exception:
            pass

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

        # Build item embeds (compact) — each embed should include the item's image in the embed.thumbnail
        item_embeds = []
        for idx, item in enumerate(items, 1):
            embed = compact_list_item_embed(item, idx)
            item_embeds.append(embed)

        pages_of_embeds = chunk_items(item_embeds, 5)  # pages of lists of embeds (5 per page max)
        # header embed (kept as the top embed on every page)
        header = discord.Embed(
            title=f"Results for “{query}”",
            description=f"Showing {min(5, len(items))} of {len(items)} results (page 1/{len(pages_of_embeds)})",
            color=EMBED_COLOR,
        )
        # try to set thumbnail from the first item
        try:
            first_pic = getattr(items[0], "picture", None) or (items[0].get("picture") if isinstance(items[0], dict) else None)
            if first_pic:
                header.set_thumbnail(url=first_pic)
        except Exception:
            pass
        header.set_footer(text=f"Data from MyAnimeList • Page 1/{len(pages_of_embeds)}")

        view = PaginatorView(pages=pages_of_embeds, author_id=interaction.user.id, header=header, timeout=120)

        # send first page (header + page0) and store message reference on the view
        to_send = view._page_embeds(0)
        msg = await interaction.followup.send(embeds=to_send, view=view)
        view.message = msg

    except Exception as e:
        print("Error in /anime command:", e)
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
        header = discord.Embed(
            title=f"Manga results for “{query}”",
            description=f"Showing {min(5, len(items))} of {len(items)} results (page 1/{len(pages_of_embeds)})",
            color=EMBED_COLOR,
        )
        try:
            first_pic = getattr(items[0], "picture", None) or (items[0].get("picture") if isinstance(items[0], dict) else None)
            if first_pic:
                header.set_thumbnail(url=first_pic)
        except Exception:
            pass
        header.set_footer(text=f"Data from MyAnimeList • Page 1/{len(pages_of_embeds)}")

        view = PaginatorView(pages=pages_of_embeds, author_id=interaction.user.id, header=header, timeout=120)
        to_send = view._page_embeds(0)
        msg = await interaction.followup.send(embeds=to_send, view=view)
        view.message = msg

    except Exception as e:
        print("Error in /manga command:", e)
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