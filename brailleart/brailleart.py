import os
import random
import sys

import aiohttp
import discord.ext.commands as commands
from PIL import Image


class BrailleArt(commands.Cog):
    """Converts an image into a rough Braille Interpretation"""

    def __init__(self, bot):
        self.bot = bot
        self.average = lambda x: sum(x) / len(x) if len(x) > 0 else 0
        self.directory = '/usr/mycogs/brailleart/'
        self.temp_img = self.directory + 'temp.png'

    @commands.command()
    async def imgtobrl(self, ctx):
        """Image to Braille"""
        image = Image

        try:
            url = ctx.message.attachments[0].url
            async with aiohttp.ClientSession().get(url) as r:
                imageData = await r.content.read()
            with open(self.temp_img, 'wb') as f:
                f.write(imageData)
                image = Image.open(self.temp_img).convert('RGBA')
            braille = await self.convert(image)
            for lines in braille:
                await ctx.send(lines)
            await ctx.send("Viola!")
            os.remove(self.temp_img)

        except IndexError:
            await ctx.send("There is no attached file.")

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
            lineList.append(line)
        lineList = await self.join_rows(lineList)
        return lineList

    async def join_rows(self, array):
        line_length = len(array[0])
        line_count = math.floor(2000 / line_length)
        return_array = []
        i = 0
        while i < len(array):
            return_array.append("\n".join(array[i: i + line_count]))
            i += line_count
        return return_array


def setup(bot):
    cog = BrailleArt(bot)
    bot.add_cog(cog)
