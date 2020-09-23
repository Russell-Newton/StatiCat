from typing import AnyStr

import discord.ext.commands as commands
import discord
from bs4 import BeautifulSoup
import requests
import re
from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from webdriver_manager.chrome import ChromeDriverManager

from bot import StatiCat


class ExtractVid(commands.Cog):
    def __init__(self, bot: StatiCat):
        self.bot = bot
        self.directory = "extractvid/"
        self.ifunny_pattern = re.compile("^https://ifunny.co/fun/..+$")

    @commands.group(name="extractvid", aliases=["getvid"], pass_context=True)
    async def extract_video(self, ctx):
        """Extract a video from a link to a social media post. Use `<prefix>help extractvid` for implementations."""
        pass

    @extract_video.command(name="ifunny", aliases=["if"])
    async def extract_from_ifunny(self, ctx: commands.Context, link: str):
        """
        Using a link to an iFunny video, output the raw video file.
        """
        if not ExtractVid._validate_link_format(link, self.ifunny_pattern):
            await ctx.send("That link isn't valid.")
            return

        capabilities = DesiredCapabilities.CHROME
        capabilities['goog:loggingPrefs'] = {'performance': 'ALL'}
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        browser = webdriver.Chrome(ChromeDriverManager().install(), desired_capabilities=capabilities, chrome_options=options)

        browser.get(link)
        soup = BeautifulSoup(browser.page_source, "lxml")
        find = soup.find("div", {"class": "media__content"})
        await ctx.send(find.prettify())

    @staticmethod
    def _validate_link_format(link: str, re_format: re.Pattern) -> bool:
        return re.match(re_format, link) is not None
