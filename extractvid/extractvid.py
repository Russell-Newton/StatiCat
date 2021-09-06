import json
import random
import re
import io
import string
from typing import Dict, Tuple, Pattern, Callable, Optional, Awaitable

import aiohttp
import discord

import discord.ext.commands as commands
from bs4 import BeautifulSoup
from datetime import datetime
import requests
from fake_useragent import UserAgent

from bot import StatiCat


def get_tiktok_cookies():
    device_id = "".join(random.choice(string.digits) for num in range(19))
    return {
        "tt_webid": device_id,
        "tt_webid_v2": device_id,
        "csrf_session_id": None,
        "tt_csrf_token": "".join(
            random.choice(string.ascii_uppercase + string.ascii_lowercase) for i in range(16)
        ),
    }


class ExtractVid(commands.Cog):
    def __init__(self, bot: StatiCat):
        self.bot = bot
        self.directory = "extractvid/"
        self.pattern_map: Dict[str, Tuple[Pattern,
                                          Callable[[str], Awaitable[Optional[io.BytesIO]]]]] = {
            "ifunny": (re.compile("^https://ifunny.co/video/..+$"), self.extract_from_ifunny),
            "tiktok": (re.compile("^https://vm.tiktok.com/[a-zA-Z0-9]+/$"), self.extract_from_tiktok)
        }
        self.agent = UserAgent().firefox

    @staticmethod
    def _validate_link_format(link: str, re_format: re.Pattern) -> bool:
        return re.match(re_format, link) is not None

    @commands.command(name="getvid")
    async def get_video(self, ctx: commands.Context, link: str):
        """Extract a video from a link to a social media post."""
        for k, v in self.pattern_map.items():
            if ExtractVid._validate_link_format(link, v[0]):
                data = await v[1](link)
                if data is None:
                    await ctx.send("Could not get your video :(")
                else:
                    await ctx.send(file=discord.File(data, f'{datetime.now().strftime("%m%d%Y%H%M%S")}.mp4'))
                return

        await ctx.send("That link isn't valid.")

    def get_ifunny_video_link(self, link: str):
        with requests.get(link, headers={'User-Agent': self.agent}) as r:
            soup = BeautifulSoup(r.content, "lxml")
        return soup.find("video")['data-src']

    async def extract_from_ifunny(self, link: str):
        """
        Using a link to an iFunny video, output the raw video file.
        """
        src = self.get_ifunny_video_link(link)

        async with aiohttp.ClientSession() as session:
            async with session.get(src) as resp:
                try:
                    return io.BytesIO(await resp.read())
                except:
                    return None

    async def extract_from_tiktok(self, link: str):
        """
        Based on https://github.com/davidteather/TikTok-Api
        """

        with requests.get(link, headers={"User-Agent": self.agent}) as r:
            soup = BeautifulSoup(r.content, "lxml")
            full_link = soup.find("link", {"rel": "canonical"})["href"]

        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            "authority": "www.tiktok.com",
            "path": full_link.split("tiktok.com")[1],
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Host": "www.tiktok.com",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.111 Safari/537.36"
        }
        cookies = get_tiktok_cookies()

        with requests.get(full_link, headers=headers, proxies=None, cookies=cookies) as r:
            html = r.text
            nonce_start = '<head nonce="'
            nonce_end = '">'
            nonce = html.split(nonce_start)[1].split(nonce_end)[0]
            j_raw = html.split(
                '<script id="__NEXT_DATA__" type="application/json" nonce="%s" crossorigin="anonymous">'
                % nonce
            )[1].split("</script>")[0]

            src = json.loads(j_raw)["props"]["pageProps"]["itemInfo"]["itemStruct"]["video"]["downloadAddr"]

        headers = {
            "Accept": "*/*",
            "Accept-Encoding": "identity;q=1, *;q=0",
            "Accept-Language": "en-US;en;q=0.9",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Host": src.split("/")[2],
            "Pragma": "no-cache",
            "Range": "bytes=0-",
            "Referer": "https://www.tiktok.com/",
            "User-Agent": self.agent
        }

        with requests.get(src, headers=headers, proxies=None, cookies=cookies) as r:
            try:
                return io.BytesIO(r.content)
            except:
                return None

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        content: str = message.content
        channel: discord.TextChannel = message.channel
        author: discord.User = message.author

        for k, v in self.pattern_map.items():
            if ExtractVid._validate_link_format(content, v[0]):
                data = await v[1](content)
                if data is not None:
                    video = discord.File(data, f'{datetime.now().strftime("%m%d%Y%H%M%S")}.mp4')
                    await channel.send(
                        f"Automatically extracted a video for you! Original link from {author.display_name}: <{content}>",
                        file=video)
                    try:
                        await message.delete()
                    except discord.Forbidden:
                        pass
