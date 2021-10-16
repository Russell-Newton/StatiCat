import logging
import os
import random
import sys
from io import BytesIO
from typing import List

import aiohttp
import nextcord.ext.commands as commands
from PIL import Image

from bot import StatiCat


class BrailleArt(commands.Cog):
    """Converts an image into a rough Braille Interpretation"""

    def __init__(self, bot: StatiCat):
        self.bot = bot
        self.average = lambda x: sum(x) / len(x) if len(x) > 0 else 0
        self.directory = 'brailleart/'
        self.temp_img = self.directory + 'temp.png'

    @commands.command()
    async def imgtobrl(self, ctx, url: str = None):
        """
        Image to Braille Art
        :param url: the link to the image. If this link is not provided, the first attached image is used.
        :return:
        """

        if url is None:
            if len(ctx.message.attachments) == 0:
                await ctx.send("You must supply a link to an image or an image as an attachment!")
                return
            url = ctx.message.attachments[0].url

        async with aiohttp.ClientSession().get(url) as r:
            image = Image.open(BytesIO(await r.content.read()))
        # with open(self.temp_img, 'wb') as f:
        #     f.write(imageData)
        #     image = Image.open(self.temp_img).convert('RGBA')
        braille = await self.convert(image)
        for lines in braille:
            logging.info(lines)
            await ctx.send(lines)
        # await ctx.send("Viola!")
        # os.remove(self.temp_img)

    # except Exception as e:
    #	await self.bot.say(e)

    async def image_average(self, x1, y1, x2, y2, base):
        return self.average([self.average(base.getpixel((x, y))[:3]) for x in range(x1, x2) for y in range(y1, y2)])

    async def convert_index(self, x):
        return {3: 6, 4: 3, 5: 4, 6: 5}.get(x, x)

    async def convert(self, image):
        lineList = []
        start = 0x2800
        char_width = 10
        char_height = char_width * 2
        dither = 10
        sensitivity = 0.8
        char_width_divided = round(char_width / 2)
        char_height_divided = round(char_height / 4)
        base = image
        match = lambda a, b: a < b if "--invert" in sys.argv else a > b
        for y in range(0, base.height - char_height - 1, char_height):
            line = ""
            for x in range(0, base.width - char_width - 1, char_width):
                byte = 0x0
                index = 0
                for xn in range(2):
                    for yn in range(4):
                        avg = await self.image_average(x + (char_height_divided * xn), y + (char_width_divided * yn),
                                                       x + (char_height_divided * (xn + 1)),
                                                       y + (char_width_divided * (yn + 1)), base)
                        if match(avg + random.randint(-dither, dither), sensitivity * 0xFF):
                            byte += 2 ** (await self.convert_index(index))
                        index += 1
                line += chr(start + byte)
            if len(line) > 2000:
                line = line[:2000]
            lineList.append(line)
        lineList = await self.join_rows(lineList)
        return lineList

    async def join_rows(self, array: List[str]):
        return_array: List[str] = [""]
        for i in range(len(array)):
            next_line = array[i]
            if len(return_array[-1]) + len(next_line) + len("\n") > 2000:
                return_array.append(next_line)
            else:
                return_array[-1] += "\n" + next_line

        return return_array
