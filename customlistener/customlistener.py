import logging
import re

import nextcord
import nextcord.ext.commands as commands
from nextcord import slash_command
from nextcord.ext import application_checks

from bot import Embedinator, StatiCat
from checks import check_permissions, check_in_guild, check_in_private, is_owner_or_whitelist
import interactions_checks
from cogwithdata import CogWithData
from interactions import SlashInteractionAliasContext


class CustomListener(CogWithData):
    _perms_to_check = ['administrator', 'manage_guild', 'manage_messages', 'kick_members', 'ban_members']

    def __init__(self, bot: StatiCat):
        super().__init__()
        self.bot = bot
        self.embedinator = Embedinator(**{"title": "**Custom Listeners**"})
        self.method_options = ["anywhere", "start", "end"]

    @commands.check_any(
        check_permissions(_perms_to_check, False),
        check_in_private(),
        is_owner_or_whitelist())
    @commands.group(name="customlisteners", aliases=["listeners", "clist"])
    async def custom_listeners(self, ctx: commands.Context):
        """Commands for managing custom listeners."""
        pass

    @slash_command(name="listeners",
                   dm_permission=False)
    @application_checks.check_any(
        interactions_checks.check_permissions(_perms_to_check, False),
        interactions_checks.is_owner_or_whitelist()
    )
    async def slash_custom_listeners(self, interaction: nextcord.Interaction):
        """Commands for managing custom listeners."""
        pass

    @check_in_guild()
    @custom_listeners.command(name="add")
    async def add_server(self, ctx: commands.Context, name: str, keyword: str, reaction: str,
                         channel_specific: bool = False):
        """
        Add a custom listener to the server.
        **name** The name of the reaction. This is important for removing and listing custom listeners.
        **keyword** What should I look for? Capitalization isn't important. If more than one word, surround with quotation marks. (ex. "Hello there!")
        **reaction** What should I say? If more than one word, surround with quotation marks. (ex. "General Kenobi!")
        **channel_specific** Should this reaction only exist for this channel? [True/False] (Defaults to False)
        """
        method = 0
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
            "channel": ctx.channel.id if channel_specific else False
        }
        if str(ctx.guild.id) not in self.data:
            self.data[str(ctx.guild.id)] = {}
        self.data[str(ctx.guild.id)][name] = listener

        if isinstance(ctx, SlashInteractionAliasContext):
            await ctx.send(
                f"Added a new custom listener to the {'channel' if channel_specific else 'server'}!\n> Name: {name}\n> Trigger: {keyword.lower()}\n> Reaction: {reaction}")

    @slash_custom_listeners.subcommand(name="add")
    async def slash_add_server(self, interaction: nextcord.Interaction, name: str, keyword: str, reaction: str,
                               channel_specific: bool = False):
        """
        Add a custom listener to the server.

        :param name: The name of the reaction. This is important for removing and listing custom listeners.
        :param keyword: What should I look for? Capitalization isn't important. If more than one word, surround with quotation marks. (ex. "Hello there!")
        :param reaction: What should I say? If more than one word, surround with quotation marks. (ex. "General Kenobi!")
        :param channel_specific: Should this reaction only exist for this channel? [True/False] (Defaults to False)
        """
        return await self.add_server(
            SlashInteractionAliasContext(interaction, self.bot, [name, keyword, reaction, channel_specific]),
            name, keyword, reaction, channel_specific)

    @check_in_guild()
    @custom_listeners.command(name="remove")
    async def remove_server(self, ctx: commands.Context, name: str):
        """
        Remove a specific listener.

        Use the list command to find all of the listeners for this server.
        """
        try:
            del self.data[str(ctx.guild.id)][name]
            await ctx.send("Removed the listener called {}!".format(name))
        except KeyError:
            await ctx.send("There isn't a listener named {} for this server.".format(name))
            return

    @slash_custom_listeners.subcommand(name="remove")
    async def slash_remove_server(self, interaction: nextcord.Interaction, name: str):
        """
        Remove a specific listener.

        Use the list command to find all of the listeners for this server.
        :param name: The name of the reaction
        """
        return await self.remove_server(SlashInteractionAliasContext(interaction, self.bot, [name, ]), name)

    @check_in_guild()
    @custom_listeners.command(name="list")
    async def list_server(self, ctx: commands.Context):
        """
        List the listeners for this server, by name.
        """
        prefix = self.bot.command_prefix
        if isinstance(prefix, list):
            prefix = prefix[0]
        if str(ctx.guild.id) not in self.data:
            await ctx.send(
                f"There are no custom listeners for this server. Add one with `{prefix}customlistener add`!")
            return
        self.embedinator.footer = f"Type `{prefix}customlisteners info <listener name>` or use /listeners info <listener name> for more info about a listener."
        self.embedinator.add_line("__Listeners for {0.guild.name}__".format(ctx))
        for name, info in sorted(self.data[str(ctx.guild.id)].items()):
            self.embedinator.add_line(name)

        for embed in self.embedinator.as_embeds(thumbnail_url=self.bot.user.avatar.url):
            await ctx.send(embed=embed)
        self.embedinator.clear()

    @slash_custom_listeners.subcommand(name="list")
    async def slash_list_server(self, interaction: nextcord.Interaction):
        """
        List the listeners for this server, by name.
        """

        return await self.list_server(SlashInteractionAliasContext(interaction, self.bot))

    @check_in_guild()
    @custom_listeners.command("info")
    async def info_server(self, ctx: commands.Context, name: str):
        """
        Get info about a listener. Use the list subcommand to get a list of listeners.
        """
        try:
            listener = self.data[str(ctx.guild.id)][name]
        except KeyError:
            await ctx.send("There isn't a listener named {} for this server.".format(name))
            return
        self.embedinator.footer = ""
        self.embedinator.add_line("__{}__".format(name))
        self.embedinator.add_line("Keyword: {}".format(name))
        self.embedinator.add_line("Keyword: {}".format(listener["keyword"]))
        self.embedinator.add_line("Reaction: {}".format(listener["reaction"]))
        # self.embedinator.add_line("Method: {}".format(listener["method"]))
        if ctx.channel.id == listener["channel"]:
            self.embedinator.add_line("Channel: {0.mention}".format(ctx.channel))

        for embed in self.embedinator.as_embeds(thumbnail_url=self.bot.user.avatar.url):
            await ctx.send(embed=embed)
        self.embedinator.clear()

    @slash_custom_listeners.subcommand(name="info")
    async def slash_info_server(self, interaction: nextcord.Interaction, name: str):
        """
        Get info about a listener. Use the list subcommand to get a list of listeners.
        """
        return await self.info_server(SlashInteractionAliasContext(interaction, self.bot, [name, ]), name)

    @custom_listeners.command("help")
    async def help_server(self, ctx: commands.Context):
        """
        Helpful information about the CustomListeners suite.
        """
        prefix = self.bot.command_prefix[0]
        if isinstance(prefix, list):
            prefix = prefix[0]
        self.embedinator.footer = f"Use {prefix}customlisteners <command> or /listeners <command> to use a command!"
        self.embedinator.add_line("There are currently **4** subcommands available with for custom listeners:")
        self.embedinator.add_line("**list** - List all of the commands defined for the current server.")
        self.embedinator.add_line("**info** - Display the information about the specified listener.")
        self.embedinator.add_line("⠀⠀<name> - The name of the listener, which you can find with `list`.")
        self.embedinator.add_line("**add** - Add a command to the current server.")
        self.embedinator.add_line("⠀⠀<name> - The name of the listener, which you will use with `remove` and `info`.")
        self.embedinator.add_line("⠀⠀<keyword> - What do you want me to pick out and respond to in a message?")
        self.embedinator.add_line("⠀⠀<reaction> - What do you want me to say in response?")
        self.embedinator.add_line(
            "⠀⠀[channel_specific=False] - Whether or not the listener only applies to the current channel. Defaults to False.")
        self.embedinator.add_line("**remove** - Remove a listener from the current server.")
        self.embedinator.add_line("⠀⠀<name> - The name of the listener, which you can find with `list`.")
        self.embedinator.add_line()
        self.embedinator.add_line("These commands only work in servers.")
        self.embedinator.add_line(
            "Any parameter with multiple words will need to be surrounded with \" \" if you don't use the slash commands.")
        for embed in self.embedinator.as_embeds(thumbnail_url=self.bot.user.avatar.url):
            await ctx.send(embed=embed)
        self.embedinator.clear()

    @slash_custom_listeners.subcommand(name="help")
    async def slash_help_server(self, interaction: nextcord.Interaction):
        """
        Helpful information about the CustomListeners suite.
        """
        return await self.help_server(SlashInteractionAliasContext(interaction, self.bot))

    def check_message(self, method: str, keyword: str, message: nextcord.Message):
        pattern_string = r'\b(?P<key>' + keyword + r')\b'
        if method == self.method_options[0]:
            pattern = re.compile(pattern_string, re.IGNORECASE)
        elif method == self.method_options[1]:
            pattern = re.compile(r'^' + pattern_string, re.IGNORECASE)
        else:
            pattern = re.compile(pattern_string + r'$', re.IGNORECASE)
        return pattern.search(message.content) is not None

    @commands.Cog.listener()
    async def on_message(self, message: nextcord.Message):
        if message.author.id != self.bot.user.id:
            if message.guild is not None:
                if str(message.guild.id) in self.data:
                    for name, info in self.data[str(message.guild.id)].items():
                        if message.channel.id == info["channel"] and self.check_message(info["method"], info["keyword"],
                                                                                        message):
                            await message.reply(info["reaction"])
                        elif info["channel"] is False and self.check_message(info["method"], info["keyword"], message):
                            await message.reply(info["reaction"])
