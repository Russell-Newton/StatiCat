import json
import os
import re
from datetime import datetime
from io import BytesIO
import aiohttp
from math import ceil
from random import choice
from typing import Union, List, Optional

import nextcord
import nextcord.ext.commands as commands
from PIL import Image, ImageDraw
from bs4 import BeautifulSoup
from nextcord import slash_command
from playwright.async_api import async_playwright

from bot import StatiCat
from checks import check_permissions
from cogwithdata import CogWithData
from interactions import SlashInteractionAliasContext


class UnavailablePokemonError(ValueError):
    pass


class DateTimeConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> datetime:
        just_date = re.compile("^\d{2}/\d{2}/\d{2}$")
        date_and_time = re.compile("^\d{2}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}$")

        if re.match(just_date, argument):
            argument += ' 00:00:00'
        if re.match(date_and_time, argument):
            return datetime.strptime(argument, '%m/%d/%y %H:%M:%S')
        raise commands.BadArgument("Date must be in the re_format: \"mm/dd/yy\" or \"mm/dd/yy hh:mm:ss\"")


class General(CogWithData):
    """General commands for general needs."""

    def __init__(self, bot: StatiCat):
        self.bot = bot
        super().__init__()

        # pokepalette stuff
        self.pokepalette_url = "http://pokepalettes.com/#"
        self.pokepalette_sprite_url = "http://pokepalettes.com/images/sprites/poke/bw/"
        self.pokemon_list = self.get_pokemon_list()
        self.palette_bg_color = (0, 0, 0)
        self.sprite_padding = 10
        self.swatch_tab_size = 20
        self.swatch_max_width = 5
        self.swatch_v_padding = 5
        self.swatch_h_padding = 5
        self.swatch_stroke_width = 1
        self.swatch_stroke_color = (0, 0, 0)

        self.eight_ball_choices = [
            "As I see it, yes.",
            "Ask again later.",
            "Better not tell you now.",
            "Cannot predict now.",
            "Concentrate and ask again.",
            "Don’t count on it.",
            "It is certain.",
            "It is decidedly so.",
            "Most likely.",
            "My reply is no.",
            "My sources say no.",
            "Outlook not so good.",
            "Outlook good.",
            "Reply hazy, try again.",
            "Signs point to yes.",
            "Very doubtful.",
            "Without a doubt.",
            "Yes.",
            "Yes – definitely.",
            "You may rely on it."
        ]

        self.scraping_output = self.directory + "scraping.csv"

    @commands.command()
    async def ping(self, ctx: commands.Context):
        await ctx.send("Pong!")

    @commands.command(aliases=['pokep', 'pokepal', 'pp'])
    async def pokepalette(self, ctx, *, pokemon: Union[int, str]):
        """
        Get the palette of colors of a pokemon from Gen I to Gen V.


        :param pokemon: the name or number of the pokemon.
        """
        if isinstance(pokemon, int):
            if pokemon >= len(self.pokemon_list):
                raise UnavailablePokemonError
            pokemon = self.pokemon_list[pokemon - 1]
        pokemon_lower = pokemon.lower()
        if pokemon_lower not in self.pokemon_list:
            await ctx.send("Only pokemon from Gen I to Gen V please :).")
            return

        # options = EdgeOptions()
        # options.use_chromium = True
        # options.add_argument("headless")
        # options.add_argument("disable-gpu")
        # try:
        #     browser = Edge(options=options)
        # except SessionNotCreatedException as e:
        #     await ctx.send(
        #         "Something is out of date with this command. I'm sending a message to the owner about this. Thank you for your patience :)")
        #     await self.bot.message_owner(f"Ayo update the msedgedriver!\n{type(e)}\t{str(e)}\n{str(e.__traceback__)}")
        #     return
        #
        # try:
        #     browser.get(self.pokepalette_url + pokemon_lower)
        # except WebDriverException:
        #     await ctx.send("The pokepalette website isn't up :(...")
        #     return
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            await page.goto(self.pokepalette_url + pokemon_lower)
            soup = BeautifulSoup(await page.content(), features="lxml")

        sprite = await self.get_pokemon_sprite(pokemon_lower)

        background_color = self.convert_style_to_color(soup.find("div", id="app")["style"])
        color_bar_entries = soup.findAll("div", class_="bar")
        colors = [background_color]
        for bar in color_bar_entries:
            try:
                colors.append(self.convert_style_to_color(bar["style"]))
            except KeyError:
                continue

        palette = await self.create_palette(sprite, colors)

        temp_loc = self.directory + str(datetime.now().microsecond)
        palette.save(temp_loc + ".png")
        await ctx.send(file=nextcord.File(temp_loc + ".png"))
        os.remove(temp_loc + ".png")

    def get_pokemon_list(self) -> List[str]:
        with open(self.directory + "\\pokemon.json") as file:
            lines = json.load(file)
            return [line.lower() for line in lines]

    @staticmethod
    def convert_style_to_color(style: str) -> nextcord.Color:
        bg_color = style.split(";")[0]
        rgb = bg_color.split("rgb(")[1][:-1].split(",")
        return nextcord.Color.from_rgb(int(rgb[0]), int(rgb[1]), int(rgb[2]))

    async def get_pokemon_sprite(self, pokemon: str) -> Image:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                    self.pokepalette_sprite_url + "{}.png".format(self.pokemon_list.index(pokemon) + 1)) as r:
                img = Image.open(BytesIO(await r.read()))
                return img

    async def create_palette(self, sprite: Image, colors: List[nextcord.Color]) -> Image:
        rows = ceil(len(colors) / self.swatch_max_width)
        cols = self.swatch_max_width if rows > 1 else len(colors)
        height = 2 * self.sprite_padding + sprite.size[1] + \
                 rows * self.swatch_tab_size + self.swatch_v_padding + cols * self.swatch_stroke_width
        width = max(2 * self.sprite_padding + sprite.size[0],
                    cols * self.swatch_tab_size + 2 * self.swatch_h_padding + rows * self.swatch_stroke_width)
        palette = Image.new("RGB", (width, height), self.palette_bg_color)

        sprite_x = (width - sprite.size[0]) / 2
        sprite_y = self.sprite_padding
        palette.paste(sprite, (int(sprite_x), int(sprite_y)))

        draw = ImageDraw.Draw(palette)

        tab_x_start = max(self.swatch_h_padding, (width - cols * self.swatch_tab_size) / 2)

        for color, i in zip(colors, range(len(colors))):
            row = int(i / self.swatch_max_width)
            col = i % self.swatch_max_width
            tab_x = int(tab_x_start + col * self.swatch_tab_size)
            tab_y = int(
                sprite_y + sprite.size[1] + self.sprite_padding + self.swatch_stroke_width + row * self.swatch_tab_size)
            draw.rectangle((tab_x, tab_y, tab_x + self.swatch_tab_size, tab_y + self.swatch_tab_size),
                           fill=(color.r, color.g, color.b), outline=self.swatch_stroke_color,
                           width=self.swatch_stroke_width)

        return palette

    @commands.command()
    async def invite(self, ctx):
        """Get a link to invite me to your server!"""
        await ctx.send(f'Invite me! {StatiCat.get_invite_link()}')

    @slash_command()
    async def invite(self, interaction: nextcord.Interaction):
        return await self.invite(SlashInteractionAliasContext(interaction, self.bot))

    @commands.command(name="8ball")
    async def eight_ball(self, ctx):
        """Peer into the Magic 8 Ball."""
        await ctx.send(choice(self.eight_ball_choices))

    @commands.command()
    async def flip(self, ctx):
        """Flip a coin."""
        await ctx.send("It's {}!".format(choice(("heads", "tails"))))

    @commands.command()
    async def roll(self, ctx, sides: Optional[int] = 6):
        """Roll a dice. Default 6 sides"""
        await ctx.send("It's {}!".format(choice(range(sides))))

    @check_permissions(['manage_messages', 'read_message_history'])
    @commands.command(name="collecthistory", aliases=["history"])
    async def package_message_history(self, ctx: commands.Context, start: datetime, end: datetime,
                                      limit: Optional[int] = None):
        """
        Compiles the messages from this channel from a start date to an end date.
        Dates must be specified in one of the following formats: "mm/dd/yy" or "mm/dd/yy hh:mm:ss"
        If no time is specified, 00:00:00 is chosen. Dates should be surrounded in quotation marks if they include a time.

        Sends a csv file to the invoker when done. The csv file is not saved on the host computer and can only be
        accessed by the command invoker. The invoker takes full responsibility for the data collected.
        """
        channel: nextcord.TextChannel = ctx.channel

        try:
            await ctx.send("This may take a while.")
            messages: List[nextcord.Message] = await channel.history(limit=limit, before=end, after=start).flatten()
        except nextcord.Forbidden:
            await ctx.send("I don't have permission to perform this operation.")
            return
        except nextcord.HTTPException:
            await ctx.send("I had some trouble performing this operation.")
            return

        if os.path.exists(self.scraping_output):
            os.remove(self.scraping_output)

        with open(self.scraping_output, 'w') as output:
            for message in messages:
                author: nextcord.User = message.author
                if message.content != "" and not author.bot:
                    output.write(f"{str(message.clean_content)},\n")

        if os.path.exists(self.scraping_output):
            author: nextcord.User = ctx.author
            await author.send("Viola!", file=nextcord.File(self.scraping_output))
            os.remove(self.scraping_output)
        else:
            await ctx.send("I had some trouble compiling the messages into a file")
