import contextlib
import json
import os
from datetime import datetime
from io import BytesIO
from math import ceil
from typing import Union, List, Optional

import discord
import discord.ext.commands as commands
import requests
from PIL import Image, ImageDraw
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

from random import choice


class UnavailablePokemonError(ValueError):
    pass


class General(commands.Cog):
    """General commands for general needs."""

    def __init__(self, bot):
        self.bot = bot
        self.directory = "general/"

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
            raise UnavailablePokemonError

        capabilities = DesiredCapabilities.CHROME
        capabilities['goog:loggingPrefs'] = {'performance': 'ALL'}
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        browser = webdriver.Chrome(desired_capabilities=capabilities, chrome_options=options)
        browser.get(self.pokepalette_url + pokemon_lower)

        soup = BeautifulSoup(browser.page_source, features="html.parser")
        network_response_log = browser.get_log('performance')
        sprite = self.get_pokemon_sprite(pokemon)
        browser.close()

        background_color = self.convert_style_to_color(soup.find("div", id="app")["style"])
        color_bar_entries = soup.findAll("div", class_="bar")
        colors = [background_color]
        for bar in color_bar_entries:
            try:
                colors.append(self.convert_style_to_color(bar["style"]))
            except KeyError:
                continue

        palette = self.create_palette(sprite, colors)

        temp_loc = self.directory + str(datetime.now().microsecond)
        palette.save(temp_loc + ".png")
        await ctx.send(file=discord.File(temp_loc + ".png"))
        os.remove(temp_loc + ".png")

    @pokepalette.error
    async def pokepalette_error(self, ctx, error):
        if isinstance(error.__cause__, UnavailablePokemonError) or isinstance(error.__cause__, IndexError):
            await ctx.send("Only pokemon from Gen I to Gen V please :).")

    def get_pokemon_list(self) -> List[str]:
        with open(self.directory + "pokemon.json") as file:
            lines = json.load(file)
            return [line.lower() for line in lines]

    @staticmethod
    def convert_style_to_color(style: str) -> discord.Color:
        bg_color = style.split(";")[0]
        rgb = bg_color.split("rgb(")[1][:-1].split(",")
        return discord.Color.from_rgb(int(rgb[0]), int(rgb[1]), int(rgb[2]))

    def get_pokemon_sprite(self, pokemon: str) -> Image:
        r = requests.get(self.pokepalette_sprite_url + "{}.png".format(self.pokemon_list.index(pokemon) + 1))
        img = Image.open(BytesIO(r.content))
        return img

    def create_palette(self, sprite: Image, colors: List[discord.Color]) -> Image:
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
        await ctx.send('Invite me! {}'.format(discord.utils.oauth_url(client_id='702205746493915258')))

    @commands.command(name="8ball")
    async def eight_ball(self, ctx):
        """Peer into the Magic 8 Ball."""
        await ctx.send(choice(self.eight_ball_choices))

    @commands.command()
    async def flip(self, ctx):
        """Flip a coin."""
        await ctx.send("It's {}!".format(choice(("heads", "tails"))))

    @commands.command()
    async def roll(self, ctx, sides: Optional[int]=6):
        """Roll a dice. Default 6 sides"""
        await ctx.send("It's {}!".format(choice(range(sides))))

