from typing import Union

import discord
import discord.ext.commands as commands

from bot import Embedinator
from checks import check_permissions, check_in_guild, check_in_private
from cogwithdata import CogWithData


class CustomListener(CogWithData):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.directory = "customlistener/"
        super().__init__(self.directory + "listeners.json")
        self.embedinator = Embedinator(**{"title": "Custom Listeners**"})
        self.method_options = ["anywhere", "start", "end"]

    @commands.check_any(
        check_permissions(['administrator', 'manage_guild', 'manage_messages', 'kick_members', 'ban_members'], False),
        check_in_private())
    @commands.group(name="customlisteners", aliases=["listeners", "clist"])
    async def custom_listeners(self, ctx: commands.Context):
        """Commands for managing custom listeners. Go into a server to see more commands."""
        pass

    @check_in_guild()
    @custom_listeners.command(name="add")
    async def add_server(self, ctx: commands.Context, name: str, keyword: str, reaction: str,
                         channel_specific: bool = False,
                         method: Union[str, int] = 0):
        """
        Add a custom listener to the server.
        **name** The name of the reaction. This is important for removing and listing custom listeners.
        **keyword** What should I look for? Capitalization isn't important. If more than one word, surround with quotation marks. (ex. "Hello there!")
        **reaction** What should I say? If more than one word, surround with quotation marks. (ex. "General Kenobi!")
        **channel_specific** Should this reaction only exist for this channel? [True/False] (Defaults to False)
        **method** Where should I look for the keyword? [anywhere/start/end or 0/1/2] (Defaults to anywhere)
        """
        if isinstance(method, int):
            try:
                method = self.method_options[method]
            except IndexError:
                method = self.method_options[0]
        if method.lower() not in self.method_options:
            method = self.method_options[0]

        listener = {
            "keyword": keyword.lower(),
            "reaction": reaction,
            "method": method.lower(),
            "channel": ctx.message.channel.id if channel_specific else False
        }
        if str(ctx.guild.id) not in self.data:
            self.data[str(ctx.guild.id)] = {}
        self.data[str(ctx.guild.id)][name] = listener
        self.set_data_file()
        await ctx.send("Added {}!".format(name))

    @check_in_guild()
    @custom_listeners.command(name="remove")
    async def remove_server(self, ctx: commands.Context, name: str):
        """
        Remove a specific listener.

        Use the list command to find all of the listeners for this server.
        **name** the name of the listener.
        """
        try:
            del self.data[str(ctx.guild.id)][name]
            self.set_data_file()
            await ctx.send("Removed {}!".format(name))
        except KeyError:
            await ctx.send("There isn't a listener named {} for this server.".format(name))
            return

    @check_in_guild()
    @custom_listeners.command(name="list")
    async def list_server(self, ctx: commands.Context):
        """
        List the listeners for this server, by name.
        """
        if str(ctx.message.guild.id) not in self.data:
            await ctx.send(
                "There are no custom listeners for this server. Add one with `{0.prefix}customlistener add`!".format(
                    ctx))
            return
        self.embedinator.footer = "Type `{0.prefix}customlisteners info <listener name>` for more info about a listener.".format(
            ctx)
        self.embedinator.add_line("__Listeners for {0.guild.name}__".format(ctx))
        for name, info in sorted(self.data[str(ctx.message.guild.id)].items()):
            self.embedinator.add_line(name)

        for embed in self.embedinator.as_embeds(thumbnail_url=self.bot.user.avatar_url):
            await ctx.send(embed=embed)
        self.embedinator.clear()

    @check_in_guild()
    @custom_listeners.command("info")
    async def info_server(self, ctx: commands.Context, name: str):
        """
        Get info about a listener.
        """
        try:
            listener = self.data[str(ctx.guild.id)][name]
        except KeyError:
            await ctx.send("There isn't a listener named {} for this server.".format(name))
            return
        self.embedinator.footer = ""
        self.embedinator.add_line("__{}__".format(name))
        self.embedinator.add_line("Keyword: {}".format(listener["keyword"]))
        self.embedinator.add_line("Reaction: {}".format(listener["reaction"]))
        self.embedinator.add_line("Method: {}".format(listener["method"]))
        if ctx.channel.id == listener["channel"]:
            self.embedinator.add_line("Channel: {0.mention}".format(ctx.channel))

        for embed in self.embedinator.as_embeds(thumbnail_url=self.bot.user.avatar_url):
            await ctx.send(embed=embed)
        self.embedinator.clear()

    def check_message(self, method: str, keyword: str, message: discord.Message):
        if method == self.method_options[0]:
            return keyword.lower() in message.content.lower()
        elif method == self.method_options[1]:
            return message.content.lower().startswith(keyword.lower())
        return message.content.lower().endswith(keyword.lower())

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.id != self.bot.user.id:
            if message.guild is not None:
                if str(message.guild.id) in self.data:
                    for name, info in self.data[str(message.guild.id)].items():
                        if message.channel.id == info["channel"] and self.check_message(info["method"], info["keyword"],
                                                                                        message):
                            await message.channel.send(info["reaction"])
                        elif info["channel"] is False and self.check_message(info["method"], info["keyword"], message):
                            await message.channel.send(info["reaction"])
