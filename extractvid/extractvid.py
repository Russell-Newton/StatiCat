import re
import io
import aiohttp
import discord

import discord.ext.commands as commands
from bs4 import BeautifulSoup
from msedge.selenium_tools import Edge, EdgeOptions
from selenium.common.exceptions import SessionNotCreatedException
from datetime import datetime

from bot import StatiCat


class ExtractVid(commands.Cog):
    def __init__(self, bot: StatiCat):
        self.bot = bot
        self.directory = "extractvid/"
        self.ifunny_pattern = re.compile("^https://ifunny.co/video/..+$")

    @commands.command(name="getvid")
    async def get_video(self, ctx: commands.Context, link: str):
        """Extract a video from a link to a social media post."""
        if ExtractVid._validate_link_format(link, self.ifunny_pattern):
            return await self.extract_from_ifunny(ctx, link)

        await ctx.send("That link isn't valid.")

    async def extract_from_ifunny(self, ctx: commands.Context, link: str):
        """
        Using a link to an iFunny video, output the raw video file.
        """
        if not ExtractVid._validate_link_format(link, self.ifunny_pattern):
            await ctx.send("That link isn't valid.")
            return

        options = EdgeOptions()
        options.use_chromium = True
        options.add_argument("headless")
        options.add_argument("disable-gpu")
        try:
            browser = Edge(options=options)
        except SessionNotCreatedException as e:
            await ctx.send(
                "Something is out of date with this command. I'm sending a message to the owner about this. Thank you for your patience :)")
            await self.bot.message_owner(f"Ayo update the msedgedriver!\n{type(e)}\t{str(e)}\n{str(e.__traceback__)}")
            return

        browser.get(link)
        soup = BeautifulSoup(browser.page_source, "lxml")
        browser.close()
        src = soup.find("div", {"class": "media__content"}).find("video")['src']

        async with aiohttp.ClientSession() as session:
            async with session.get(src) as resp:
                if resp.status != 200:
                    return await ctx.send("Could not get video...")
                data = io.BytesIO(await resp.read())
                await ctx.send(file=discord.File(data, f'{datetime.now().strftime("%m%d%Y%H%M%S")}.mp4'))

    @staticmethod
    def _validate_link_format(link: str, re_format: re.Pattern) -> bool:
        return re.match(re_format, link) is not None
