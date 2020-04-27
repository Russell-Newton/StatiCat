from random import choice
from typing import Union

import discord
import discord.ext.commands as commands

from checks import check_permissions
from cogwithdata import CogWithData


class Rude(CogWithData):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.directory = "rude/"
        super().__init__(self.directory + "targets.json")

    @check_permissions(['administrator', 'manage_guild', 'manage_messages', 'kick_members', 'ban_members'], False)
    @commands.group(name="mimic", pass_context=True)
    async def _mimic(self, ctx):
        """Manage the mimicking status"""
        pass

    @check_permissions(['administrator', 'manage_guild', 'manage_messages', 'kick_members', 'ban_members'], False)
    @commands.group(pass_context=True)
    async def silence(self, ctx):
        """Manage the silencing status"""
        pass

    @_mimic.command(name="add", pass_context=True)
    async def mimic_add(self, ctx, target: Union[discord.Member, discord.User]):
        """Add someone to the list of targets"""
        if target.id is self.bot.user.id:
            await ctx.send("I can't mimic myself.")
            return
        self.data["mimic"].append(target.id)
        self.set_data_file()

        await ctx.send("{0.mention} <3".format(target))

    @_mimic.command(name="remove", pass_context=True)
    async def mimic_remove(self, ctx, target: Union[discord.Member, discord.User]):
        """Remove someone from the list of targets"""
        self.data["mimic"].remove(target.id)
        self.set_data_file()

        await ctx.send("You're off the hook for now, {0.mention}.".format(target))

    @_mimic.command(name="clear", pass_context=True)
    async def mimic_clear(self, ctx):
        """Clear the list of targets"""
        self.data["mimic"] = []
        self.set_data_file()

        await ctx.send("I'll stop now.")

    @silence.command(name="add", pass_context=True)
    async def silence_add(self, ctx, target: Union[discord.Member, discord.User]):
        """Add someone to the list of targets"""
        if target.id is self.bot.user.id:
            await ctx.send("I can't silence myself.")
            return
        self.data["silence"].append(target.id)
        self.set_data_file()

        await ctx.send("{0.mention} <3".format(target))

    @silence.command(name="remove", pass_context=True)
    async def silence_remove(self, ctx, target: Union[discord.Member, discord.User]):
        """Remove someone from the list of targets"""
        self.data["silence"].remove(target.id)
        self.set_data_file()

        await ctx.send("You're off the hook for now, {0.mention}.".format(target))

    @silence.command(name="clear", pass_context=True)
    async def silence_clear(self, ctx):
        """Clear the list of targets"""
        self.data["silence"] = []
        self.set_data_file()

        await ctx.send("I'll stop now.")

    def get_silence_message(self, input_message) -> str:
        choices = [
            "Bro shut up.",
            "Who said you could speak?",
            "You're on thin ice, bud.",
            "What's so hard to understand about \"shut up\"?",
            lambda: "{0.mention}, get your boy. {1.mention}'s all up in my face, bro".format(
                self.get_random_guild_member(input_message),
                input_message.author) if input_message.guild is not None else "You're all up in my face, bro."
        ]
        chosen = choice(choices)
        if callable(chosen):
            return chosen()
        return chosen

    @staticmethod
    def get_random_guild_member(input_message) -> discord.Member:
        guild: discord.Guild = input_message.guild
        chosen: discord.Member = choice(guild.members)
        while chosen.id is input_message.author.id:
            chosen = choice(guild.members)
        return choice(guild.members)

    @staticmethod
    def spongebobify(message: discord.Message):
        out = ""
        choices = [lambda x: x.lower(),
                   lambda x: x.upper()]
        for i, char in enumerate(message.content):
            out += choice(choices)(char)
        return out

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.id is not self.bot.user.id:
            try:
                if message.author.id in self.data["mimic"]:
                    await message.channel.send(self.spongebobify(message))
                if message.author.id in self.data["silence"]:
                    try:
                        await message.delete()
                    except discord.Forbidden:
                        await message.channel.send(self.get_silence_message(message))
            except Exception:
                pass

    @commands.Cog.listener()
    async def on_typing(self, channel: discord.abc.Messageable, user: Union[discord.User, discord.Member], when):
        if user.id is not self.bot.user.id:
            try:
                if user.id in self.data["silence"]:
                    await channel.send("Stop typing, {0.mention}".format(user))
            except Exception:
                pass
