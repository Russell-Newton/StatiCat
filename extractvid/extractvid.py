import asyncio
import glob
import io
import logging
import os
import random
import re
import string
import urllib.request
from datetime import datetime
from os import path
from typing import Dict, Tuple, Pattern, Callable, Optional, Awaitable

import aiohttp
import nextcord
import nextcord.ext.commands as commands
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from tiktokapipy.async_api import AsyncTikTokAPI, TikTokAPIError
from tiktokapipy.models.video import Video

from bot import StatiCat


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
            "tiktokshort": (re.compile("^https://(www|vm).tiktok.com/\S+$"), self.extract_from_tiktok),
            # "tiktoklong": (
            # re.compile("^https://www.tiktok.com/@[a-zA-Z0-9_.]+/video/[0-9]+\S*$"), self.extract_from_tiktok_long)
        }
        self.agent = UserAgent().chrome

    @staticmethod
    def _validate_link_format(link: str, re_format: re.Pattern) -> bool:
        return re.match(re_format, link) is not None

    @commands.command(name="getvid")
    async def get_video(self, ctx: commands.Context, link: str):
        """Extract a video from a link to a social media post."""
        for k, (pattern, extractor) in self.pattern_map.items():
            if ExtractVid._validate_link_format(link, pattern):
                data = await extractor(link)
                if data is None:
                    await ctx.send("Could not get your video :(")
                elif isinstance(data, TikTokAPIError):
                    await ctx.reply(
                        f"I couldn't get that video from TikTok [_{data}_]. Try a second time or with the long link :)")
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

    async def extract_from_tiktok(self, link: str):
        async with AsyncTikTokAPI(emulate_mobile=True, navigation_retries=2, navigation_timeout=10000) as api:
            try:
                video: Video = await api.video(link)
                if video.image_post:
                    vf = "\"scale=iw*min(1080/iw\,1920/ih):ih*min(1080/iw\,1920/ih)," \
                         "pad=1080:1920:(1080-iw)/2:(1920-ih)/2," \
                         "format=yuv420p\""
                    for i, image_data in enumerate(video.image_post.images):
                        url1, url2, url3 = image_data.image_url.url_list
                        urllib.request.urlretrieve(url3, path.join(self.directory, f"temp_{video.id}_{i:02}.jpg"))
                    urllib.request.urlretrieve(video.music.play_url, path.join(self.directory, f"temp_{video.id}.mp3"))
                    command = [
                        "ffmpeg",
                        "-r 2/5",
                        f"-i {self.directory}/temp_{video.id}_%02d.jpg",
                        f"-i {self.directory}/temp_{video.id}.mp3",
                        "-r 30",
                        f"-vf {vf}",
                        "-acodec copy",
                        "-shortest",
                        f"{self.directory}/temp_{video.id}.mp4",
                        "-y"
                    ]
                    ffmpeg_proc = await asyncio.create_subprocess_shell(
                        " ".join(command),
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    _, stderr = await ffmpeg_proc.communicate()
                    generated_files = glob.glob(path.join(self.directory, f"temp_{video.id}*"))

                    if not path.exists(path.join(self.directory, f"temp_{video.id}.mp4")):
                        logging.error(stderr.decode("utf-8"))
                        ret = TikTokAPIError("Something went wrong with piecing the slideshow together")
                    else:
                        with open(path.join(self.directory, f"temp_{video.id}.mp4"), "rb") as f:
                            ret = io.BytesIO(f.read())

                    for file in generated_files:
                        os.remove(file)

                    return ret
                async with aiohttp.ClientSession() as session:
                    async with session.get(video.video.download_addr) as resp:
                        return io.BytesIO(await resp.read())
            except TikTokAPIError as e:
                return e

    @commands.Cog.listener()
    async def on_message(self, message: nextcord.Message):
        content: str = message.content
        channel: nextcord.TextChannel = message.channel
        author: nextcord.User = message.author

        for k, (pattern, extractor) in self.pattern_map.items():
            if ExtractVid._validate_link_format(content, pattern):
                data = await extractor(content)
                if isinstance(data, TikTokAPIError):
                    await message.reply(
                        f"I couldn't get that video from TikTok [_{data}_]. Try a second time or with the long link :)")
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
