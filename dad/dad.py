import logging
from typing import Union

import discord
import discord.ext.commands as commands
import requests
from lxml import html

from bot import StatiCat
from cogwithdata import CogWithData
from random import random

class Dad(CogWithData):
    """Dad-Bot"""

    def __init__(self, bot: StatiCat):
        self.bot = bot
        super().__init__("dad/imdadblacklist.json")
        self.funny_chance = 0.02

    @commands.command()
    async def dadjoke(self, ctx):
        """
        Go to https://icanhazdadjoke.com/ for more!
        """
        page = requests.get('https://icanhazdadjoke.com/')
        tree = html.fromstring(page.content)
        joke = tree.xpath('/html/body/section/div/div[2]/div/div/p/text()')[0]
        await ctx.send(joke)

    @commands.command(name="stopdad")
    async def blacklist_imdad(self, ctx: commands.Context):
        """
        Disables the funny I'm StatiCat joke for this server.
        """
        if "blacklist" not in self.data:
            self.data["blacklist"] = []
        self.data["blacklist"].append(ctx.guild.id)
        self.update_data_file()
        await ctx.send("No longer responding with the classic joke.")

    @commands.command(name="startdad")
    async def unblacklist_imdad(self, ctx: commands.Context):
        """
        Enables the funny I'm StatiCat joke for this server.
        """
        if "blacklist" not in self.data:
            self.data["blacklist"] = []
        self.data["blacklist"].remove(ctx.guild.id)
        self.update_data_file()
        await ctx.send("Time to become funny.")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        content: str = message.content
        channel = message.channel
        if message.author.id != self.bot.user.id:
            for word in content.split(" "):
                if word.endswith("er") and random() < self.funny_chance:
                    if word == "her" and random() >= self.funny_chance:
                        continue
                    await channel.send(f"\"{word}\"? I hardly even know her!")
                    return

        if message.guild is not None:
            if message.guild.id in self.data["blacklist"]:
               return
        if content.lower().startswith("i'm ") or content.lower().startswith(
                'im ') or content.lower().startswith('i am '):
            nameStart = content.find('m') + 1
            nameEnd = content.find('.')
            if nameEnd > 0:
                name = content[nameStart:nameEnd]
            else:
                name = content[nameStart:]
            await channel.send("Hi" + name + f"! I'm {self.bot.user.name}!")

    @commands.Cog.listener("on_reaction_add")
    async def remove_funny_dad_message(self, reaction: discord.Reaction, user: Union[discord.Member, discord.User]):
        message: discord.Message = reaction.message
        if user.id != self.bot.user.id and message.content.startswith("Hi") and message.content.endswith(f"! I'm {self.bot.user.name}!"):
            # logging.info(f"Grabbed reacted message: {message.content}, with emoji: {str(reaction.emoji)}")
            if reaction.emoji == "\u274c":
                await reaction.message.delete()
