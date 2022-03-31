import json
import logging
import random
import re
import io
import string
import codecs
import traceback
from typing import Dict, Tuple, Pattern, Callable, Optional, Awaitable

import aiohttp
import nextcord

import nextcord.ext.commands as commands
import selenium.common.exceptions
from bs4 import BeautifulSoup
from datetime import datetime
import requests
from fake_useragent import UserAgent
from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver

from bot import StatiCat


TIKTOK_FAILED_EXTRACT = "Couldn't extract full link from small link"
TIKTOK_FAILED_DOWNLOADADDR = "Couldn't find the downloadAddr in the page data"
TIKTOK_FAILED_ENDLINK = "Couldn't find the end of the downloadAddr"
WEBDRIVER_SESSION_FAILED = "Cached webdriver is out of date"


def get_tiktok_cookies():
    device_id = "".join(random.choice(string.digits) for _ in range(19))
    return {
        "tt_webid": device_id,
        "tt_webid_v2": device_id,
        "csrf_session_id": None,
        "tt_csrf_token": "".join(
            random.choice(string.ascii_uppercase + string.ascii_lowercase) for _ in range(16)
        ),
    }


class ExtractVid(commands.Cog):
    def __init__(self, bot: StatiCat):
        self.bot = bot
        self.directory = "extractvid/"
        self.pattern_map: Dict[str, Tuple[Pattern,
                                          Callable[[str], Awaitable[Optional[io.BytesIO]]]]] = {
            "ifunny": (re.compile("^https://ifunny.co/video/..+$"), self.extract_from_ifunny),
            "tiktok": (re.compile("^https://vm.tiktok.com/[a-zA-Z0-9]+/\S*$"), self.extract_from_tiktok),
            "tiktoklong": (
            re.compile("^https://www.tiktok.com/@[a-zA-Z0-9_.]+/video/[0-9]+\S*$"), self.extract_from_tiktok_long)
        }
        self.agent = UserAgent().chrome

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
                elif data in (TIKTOK_FAILED_EXTRACT, TIKTOK_FAILED_DOWNLOADADDR, TIKTOK_FAILED_ENDLINK):
                    await ctx.reply(f"I couldn't get that video from TikTok ({data}). Try a second time or with the long link :)")
                else:
                    file = nextcord.File(data, f'{datetime.now().strftime("%m%d%Y%H%M%S")}.mp4')
                    await ctx.send(file=file)
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

    async def extract_from_tiktok_long(self, full_link: str):
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            "authority": "www.tiktok.com",
            "path": full_link.split("tiktok.com")[1],
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Host": "www.tiktok.com",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36"
        }
        cookies = get_tiktok_cookies()

        with requests.get(full_link, headers=headers, proxies=None, cookies=cookies) as r:
            html = r.text
            # nonce_start = '<head nonce="'
            # nonce_end = '">'
            # nonce = html.split(nonce_start)[1].split(nonce_end)[0]
            # j_raw = html.split(
            #     '<script id="__NEXT_DATA__" type="application/json" nonce="%s" crossorigin="anonymous">'
            #     % nonce
            # )[1].split("</script>")[0]
            # src = json.loads(j_raw)["props"]["pageProps"]["itemInfo"]["itemStruct"]["video"]["downloadAddr"]

            try:
                src_raw = html.split("\"downloadAddr\":\"")[1]
            except IndexError:
                return TIKTOK_FAILED_EXTRACT
            try:
                src_raw = src_raw.split("\",")[0]
            except IndexError:
                return TIKTOK_FAILED_ENDLINK
            src = codecs.decode(src_raw, "unicode-escape")

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

        # with requests.get(src, headers=headers, proxies=None, cookies=cookies) as r:
        #     try:
        #         return io.BytesIO(r.content)
        #     except:
        #         return None

        async with aiohttp.ClientSession(headers=headers, cookies=cookies) as session:
            async with session.get(src) as resp:
                try:
                    return io.BytesIO(await resp.read())
                except:
                    return None

    async def extract_from_tiktok(self, link: str):
        """
        Based on https://github.com/davidteather/TikTok-Api
        """
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36")
        options.add_argument("--disable-gpu")
        try:
            browser = webdriver.Chrome(executable_path=ChromeDriverManager(#version="100.0.4896.60",
                                                                           log_level=0,
                                                                           print_first_line=False).install(),
                                       options=options)
        except selenium.common.exceptions.SessionNotCreatedException as error:
            traceback.print_exception(type(error), error, error.__traceback__)
            return WEBDRIVER_SESSION_FAILED

        browser.get(link)

        soup = BeautifulSoup(browser.page_source, features="lxml")
        browser.quit()
        try:
            full_link = soup.find("link", {"rel": "canonical"})["href"]
        except TypeError:
            return TIKTOK_FAILED_EXTRACT

        return await self.extract_from_tiktok_long(full_link)

    @commands.Cog.listener()
    async def on_message(self, message: nextcord.Message):
        content: str = message.content
        channel: nextcord.TextChannel = message.channel
        author: nextcord.User = message.author

        for k, v in self.pattern_map.items():
            if ExtractVid._validate_link_format(content, v[0]):
                data = await v[1](content)
                if data in (TIKTOK_FAILED_EXTRACT, TIKTOK_FAILED_DOWNLOADADDR, TIKTOK_FAILED_ENDLINK):
                    await message.reply(f"I couldn't get that video from TikTok ({data}). Try a second time or with the long link :)")
                elif data in (WEBDRIVER_SESSION_FAILED,):
                    await message.reply(f"I couldn't get that video for you ({data}). <@{self.bot.owner_id}> if you're here, check this out and fix it please :)")
                elif data is not None:
                    video = nextcord.File(data, f'{datetime.now().strftime("%m%d%Y%H%M%S")}.mp4')
                    try:
                        await channel.send(
                            f"Automatically extracted a video for you! Original link from {author.display_name}: <{content}>",
                            file=video)
                    except nextcord.HTTPException as e:
                        if e.code == 40005:
                            await message.reply("I'd extract that video for you, but it's too big")
                            return
                    try:
                        await message.delete()
                    except nextcord.Forbidden:
                        pass
