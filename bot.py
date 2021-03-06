import argparse
import asyncio
import itertools
import logging
import os
import sys
import traceback
from datetime import datetime
from importlib import import_module
from importlib.machinery import ModuleSpec
from typing import List

import discord
import discord.ext.commands as commands

from checks import NoPermissionError
from universals import get_prefixes, get_owner_data, get_global_data, get_color_palette


def restart_after_shutdown():
    logging.warning("Shutdown complete. Attempting to restart...")
    python = sys.executable
    os.execl(python, python, *sys.argv + ["--messageowner"])


class Embedinator(commands.Paginator):
    """
    Can be used to create custom embeds.
    Some variables can be set on initialization:
        max_size
        color
        title
        footer
    """

    def __init__(self, **options):
        """
        :param options: max_size, color, title, and footer can be set on initialization.
        """
        super().__init__(prefix=None, suffix=None, max_size=options.pop('max_size', 2000))
        self.color = options.pop('color', discord.Color(int(0x7bacf6)))
        self.title = options.pop('title', "**Help Menu**")
        self.footer: str = options.pop('footer', "")

    @staticmethod
    def add_field_fix_empty_strings(embed: discord.Embed, field_title: str, field_content: str):
        if field_title == "":
            if field_content != "":
                embed.add_field(name="\u2800", value=field_content, inline=False)
        else:
            if field_content == "":
                embed.add_field(name=field_title, value="\u2800", inline=False)
            else:
                embed.add_field(name=field_title, value=field_content, inline=False)

    def as_embeds(self, thumbnail_url, color: discord.Color = None) -> List[discord.Embed]:
        embeds = []
        field_title = ""
        if color is None:
            color = self.color
        for page, number in zip(self.pages, range(len(self.pages))):
            field_content = ""
            embed = discord.Embed(title=self.title,
                                  color=color,
                                  description="*Page {} of {}*".format(str(number + 1), len(self.pages))
                                  ).set_thumbnail(
                url=thumbnail_url
            )
            embed.set_footer(text=self.footer)

            lines = page.splitlines()

            if not lines[0].startswith("__") and not lines[0].endswith("__") and number != 0:
                field_title = field_title + " (cont.)"

            for line in lines:
                if line.startswith("__") and line.endswith("__"):
                    self.add_field_fix_empty_strings(embed, field_title, field_content)
                    field_title = line
                    field_content = ""
                else:
                    field_content = field_content + "\n" + line
            self.add_field_fix_empty_strings(embed, field_title, field_content)

            embeds.append(embed)

        return embeds


class EmbeddingHelpCommand(commands.HelpCommand):
    def __init__(self, **options):
        super().__init__(**options)
        self.width: int = options.pop('width', 100)
        self.indent: int = options.pop('indent', 2)
        self.dm_help_threshold: int = options.pop('dm_help_threshold', 2000)
        self.no_category: str = "Miscellaneous"
        self.embedinator: Embedinator = Embedinator(**options)
        self.palette = get_color_palette()

    async def send_pages(self, **options):
        destination = self.get_destination()
        self.embedinator.footer = "Type `{0}help <command>` for more info on a command. You can also type `{0}help <category>` for more info on a category.".format(
            self.context.prefix)

        for embed in self.embedinator.as_embeds(thumbnail_url=self.context.bot.user.avatar_url, **options):
            await destination.send(embed=embed)
        self.embedinator.clear()

    def shorten_text(self, text):
        """Shortens text to fit into the :attr:`width`."""
        if len(text) > self.width:
            return text[:self.width - 3] + '...'
        return text

    def get_destination(self):
        ctx = self.context
        if len(self.embedinator) > self.dm_help_threshold:
            return ctx.author
        return ctx.channel

    def add_command_block(self, cog_name, _commands):
        self.embedinator.add_line(cog_name)
        for command in _commands:
            self.embedinator.add_line(self.format_command_info(command))

    def add_command_syntax(self, command):
        signature = self.get_command_signature(command)
        self.embedinator.add_line("`Syntax: {}`".format(signature))

        if command.description:
            self.embedinator.add_line(command.description)

        if command.aliases:
            self.embedinator.add_line("Aliases:")
            for alias in command.aliases:
                self.embedinator.add_line(alias)

        if command.help:
            try:
                self.embedinator.add_line(command.help)
            except RuntimeError:
                for line in command.help.splitlines():
                    self.embedinator.add_line(line)
                self.embedinator.add_line()

    def format_command_info(self, command: commands.Command):
        return self.shorten_text("**{0.name}** {0.short_doc}".format(command))

    async def send_bot_help(self, mapping):
        ctx = self.context
        _bot = ctx.bot

        no_category = '__**{0.no_category}:**__'.format(self)

        def get_category(command, *, _no_category=no_category):
            cog = command.cog
            return "__**" + cog.qualified_name + ':**__' if cog is not None else _no_category

        filtered = await self.filter_commands(_bot.commands, sort=True, key=get_category)
        to_iterate = itertools.groupby(filtered, key=get_category)

        # Now we can add the commands to the page.
        for category, _commands in to_iterate:
            _commands = sorted(_commands, key=lambda c: c.name)
            self.add_command_block(category, tuple(_commands))

        await self.send_pages(color=self.palette[0])

    async def send_cog_help(self, cog):
        filtered = await self.filter_commands(cog.get_commands(), sort=True)
        if cog.description:
            self.embedinator.add_line(cog.description)
        self.add_command_block("__**Commands:**__", filtered)

        await self.send_pages(color=self.palette[7])

    async def send_group_help(self, group):
        self.add_command_syntax(group)

        filtered = await self.filter_commands(group.commands, sort=True)
        self.add_command_block("__**Subcommands:**__", filtered)

        await self.send_pages(color=self.palette[9])

    async def send_command_help(self, command):
        self.add_command_syntax(command)
        self.embedinator.close_page()
        await self.send_pages(color=self.palette[9])

    async def prepare_help_command(self, ctx, command=None):
        self.embedinator.clear()
        await super().prepare_help_command(ctx, command)


class StatiCat(commands.Bot):
    def __init__(self, **options):
        super().__init__(command_prefix=get_prefixes, **options)

        # This should never be set to true without shutting down the bot
        self.should_restart = False
        self.send_startup_message_to_owner = False

    @staticmethod
    def print_invite_link():
        # perms: discord.Permissions = discord.Permissions(change_nickname=True,
        #                                                  view_channel=True,
        #                                                  send_messages=True,
        #                                                  send_tts_messages=True,
        #                                                  embed_links=True,
        #                                                  attach_files=True,
        #                                                  read_messages=True,
        #                                                  read_message_history=True,
        #                                                  add_reactions=True,
        #                                                  connect=True,
        #                                                  speak=True,
        #                                                  use_voice_activation=True)
        print('Invite me! {}'.format(discord.utils.oauth_url(client_id='702205746493915258'
                                                             # , permissions=perms
                                                             )))
        pass

    async def load_cogs(self):
        print("Loading cogs...")
        logging.info("Loading cogs...")
        _cogs = get_global_data()["loaded cogs"]
        for cog in _cogs:
            try:
                await self._load_cog_silent(cog)
                print("Loaded {}!".format(cog))
                logging.info(f"Loaded {cog}!")
            except Exception as error:
                traceback.print_exception(type(error), error, error.__traceback__)
                logging.exception("Failed to load a cog.")
        print("Done!\n")
        logging.info("Done!\n")

    async def _load_cog_silent(self, cog_name):
        """
        Loads a cog.

        Usage: load <cog_name>
        """
        if self.get_cog(cog_name) is not None:
            return
        try:
            mod: ModuleSpec = import_module(cog_name.lower()).__spec__
        except ImportError as e:
            if e.name.lower() == cog_name.lower():
                print("No cog of the name '{}' was found.".format(cog_name))
                logging.warning(f"No cog of the name '{cog_name}' was found.")
            return

        lib = mod.loader.load_module()
        if not hasattr(lib, "setup"):
            del lib
            print("Cog '{}' doesn't have a setup function.".format(cog_name))
            logging.warning(f"Cog '{cog_name}' doesn't have a setup function.")
            return

        try:
            if asyncio.iscoroutinefunction(lib.setup):
                await lib.setup(self)
            else:
                lib.setup(self)
        except Exception as e:
            logging.exception("Caught an exception while running a cog setup script.")
            print(str(e))

    async def on_ready(self):
        print(f'Logged in as {self.user}')
        logging.info(f"Logged in as {self.user}")

        await self.load_cogs()
        self.help_command = EmbeddingHelpCommand(**{"title": "{} Help Menu".format(self.user.name)})
        self.print_invite_link()
        await self.change_presence(activity=discord.Game(name="Type s!help for help!"))

        # Initialize owner_id
        await self.is_owner(self.user)

        if self.send_startup_message_to_owner:
            send_message_task = asyncio.create_task(self.message_owner("Up and running!"))
            await send_message_task

    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.CheckFailure):
            traceback.print_exception(type(error), error, error.__traceback__)
            logging.error("Caught a command checks error.", exc_info=(type(error), error, error.__traceback__))
            return
        if isinstance(error, NoPermissionError):
            await ctx.send("You don't have permission to use that")
            logging.error("Someone tried to use a command that they didn't have permission for.",
                          exc_info=(type(error), error, error.__traceback__))
            return
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(
                "Missing required arguments. Try `{0.prefix}help <command_name>` for usage information!".format(ctx))
            return
        elif isinstance(error, commands.BadArgument):
            await ctx.send("Bad argument. {}".format(str(error)))
            await ctx.send("Try `{0.prefix}help <command_name>` for usage information!".format(ctx))
        elif not isinstance(error, commands.CommandNotFound):
            traceback.print_exception(type(error), error, error.__traceback__)
            logging.error("Caught a command error.", exc_info=(type(error), error, error.__traceback__))
            await ctx.send(
                "Oops! You just caused an error ({} caused by {})! Try `{}help <command_name>` for usage information!".format(
                    error.__class__.__name__, error.__cause__.__class__.__name__, ctx.prefix))

    async def message_owner(self, message: str):
        await self.get_user(self.owner_id).send(message)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Optional bot parameters.")
    parser.add_argument('-l', '--loglevel',
                        dest='loglevel',
                        type=str,
                        default="INFO",
                        help="The logging level for the bot (default: INFO)")
    parser.add_argument('--messageowner',
                        dest='messageowner',
                        action='store_true')

    args = parser.parse_args()

    numeric_level = getattr(logging, args.loglevel.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: %s' % args.loglevel)

    logging.basicConfig(filename=f'_logs/{datetime.now().strftime("%m-%d-%Y %H_%M_%S.log")}',
                        level=args.loglevel,
                        format='%(levelname)s::%(asctime)s::%(message)s',
                        datefmt='%m/%d/%Y %H:%M:%S')

    intents: discord.Intents = discord.Intents.default()

    bot = StatiCat(intents=intents)

    if args.messageowner:
        bot.send_startup_message_to_owner = True

    logging.info(sys.argv)

    bot.run(get_owner_data()["Token"])
    if bot.should_restart:
        restart_after_shutdown()
