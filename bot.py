import asyncio
import itertools
import logging
import os
import sys
from datetime import datetime
from importlib import import_module
from importlib.machinery import ModuleSpec
from random import choice
from typing import List

import click
import nextcord
import nextcord.ext.commands as commands
from dotenv import load_dotenv

from autosavedict import AutoSavingDict
from checks import NoPermissionError


TOKEN_KEY = "BOT_TOKEN"
ENV_FILE = ".env"


bot = None


def add_empty_env_keys(*keys):
    with open(".env", "a+") as f:
        for key in keys:
            if key not in os.environ:
                f.write(f"{key}=\n")


def load_env():
    load_dotenv()

    keys_to_add = []
    fail = False
    if TOKEN_KEY not in os.environ or os.environ[TOKEN_KEY] == "":
        keys_to_add.append(TOKEN_KEY)
        fail = True

    add_empty_env_keys(*keys_to_add)

    if fail:
        raise EnvironmentError("Failed to load environment from .env file.")


def restart_after_shutdown():
    logging.warning("Shutdown complete. Attempting to restart...")
    os.execv(sys.executable, sys.argv)


def clean_files():
    files = os.listdir("_logs")
    full_path = ["_logs/{0}".format(x) for x in files]

    time_sorted = sorted(full_path, key=os.path.getctime, reverse=True)

    while len(time_sorted) >= 15:
        oldest_file = time_sorted.pop()
        os.remove(oldest_file)


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
        self.color = options.pop('color', nextcord.Color(int(0x7bacf6)))
        self.title = options.pop('title', "**Help Menu**")
        self.footer: str = options.pop('footer', "")

    @staticmethod
    def add_field_fix_empty_strings(embed: nextcord.Embed, field_title: str, field_content: str):
        if field_title == "":
            if field_content != "":
                embed.add_field(name="\u2800", value=field_content, inline=False)
        else:
            if field_content == "":
                embed.add_field(name=field_title, value="\u2800", inline=False)
            else:
                embed.add_field(name=field_title, value=field_content, inline=False)

    def as_embeds(self, thumbnail_url, color: nextcord.Color = None) -> List[nextcord.Embed]:
        embeds = []
        field_title = ""
        if color is None:
            color = self.color
        for page, number in zip(self.pages, range(len(self.pages))):
            field_content = ""
            embed = nextcord.Embed(title=self.title,
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
    def __init__(self, color_palette, **options):
        super().__init__(**options)
        self.bot = bot
        self.width: int = options.pop('width', 100)
        self.indent: int = options.pop('indent', 2)
        self.dm_help_threshold: int = options.pop('dm_help_threshold', 2000)
        self.no_category: str = "Miscellaneous"
        self.embedinator: Embedinator = Embedinator(**options)
        self.color_palette = color_palette

    async def send_pages(self, **options):
        destination = self.get_destination()
        self.embedinator.footer = "Type `{0}help <command>` for more info on a command. You can also type `{0}help <category>` for more info on a category.".format(
            self.context.prefix)

        for embed in self.embedinator.as_embeds(thumbnail_url=self.context.bot.user.avatar.url, **options):
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

        await self.send_pages(color=self.color_palette[0])

    async def send_cog_help(self, cog):
        filtered = await self.filter_commands(cog.get_commands(), sort=True)
        if cog.description:
            self.embedinator.add_line(cog.description)
        self.add_command_block("__**Commands:**__", filtered)

        await self.send_pages(color=self.color_palette[7])

    async def send_group_help(self, group):
        self.add_command_syntax(group)

        filtered = await self.filter_commands(group.commands, sort=True)
        self.add_command_block("__**Subcommands:**__", filtered)

        await self.send_pages(color=self.color_palette[9])

    async def send_command_help(self, command):
        self.add_command_syntax(command)
        self.embedinator.close_page()
        await self.send_pages(color=self.color_palette[9])

    async def prepare_help_command(self, ctx, command=None):
        self.embedinator.clear()
        await super().prepare_help_command(ctx, command)


class StatiCat(commands.Bot):
    def __init__(self, **options):
        # This should never be set to true without shutting down the bot
        self.should_restart = False
        self.send_startup_message_to_owner = False
        self.global_data = AutoSavingDict("global_data.json")

        super().__init__(command_prefix=self.get_prefixes(), **options)

    @staticmethod
    def get_invite_link():
        perms: nextcord.Permissions = nextcord.Permissions.text()
        return nextcord.utils.oauth_url(client_id='702205746493915258', permissions=perms,
                                        scopes=["bot", "applications.commands"])

    @staticmethod
    def print_invite_link():
        print(f'Invite me! {StatiCat.get_invite_link()}')

    def get_prefixes(self):
        return self.global_data["prefixes"]

    def get_color_palette(self) -> List[nextcord.Color]:
        hexes = self.global_data["color palette"]
        return [nextcord.Color(int(hex_val, 0)) for hex_val in hexes]

    async def load_cogs(self):
        logging.info("Loading cogs...")
        _cogs: list = self.global_data["loaded cogs"]
        if "Cogs" not in _cogs:
            _cogs.insert(0, "Cogs")
        if "Owner" not in _cogs:
            _cogs.insert(0, "Owner")
        for cog in _cogs:
            try:
                await self._load_cog_silent(cog)
                logging.info(f"Loaded {cog}!")
            except Exception as error:
                logging.exception("Failed to load a cog.")

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
                logging.warning(f"No cog of the name '{cog_name}' was found.")
            raise e

        lib = mod.loader.load_module()
        if not hasattr(lib, "setup"):
            del lib
            logging.warning(f"Cog '{cog_name}' doesn't have a setup function.")
            return

        try:
            if asyncio.iscoroutinefunction(lib.setup):
                await lib.setup(self)
            else:
                lib.setup(self)
        except Exception as e:
            logging.exception("Caught an exception while running a cog setup script.")
            raise e

    async def on_ready(self):
        logging.info(f"Logged in as {self.user}")

        await self.load_cogs()
        self.help_command = EmbeddingHelpCommand(self.get_color_palette(),
                                                 **{"title": "{} Help Menu".format(self.user.name)})
        self.print_invite_link()
        await self.change_presence(activity=nextcord.Game(name="Type s!help for help!"))

        # Initialize owner_id
        await self.is_owner(self.user)

        if self.send_startup_message_to_owner:
            send_message_task = asyncio.create_task(self.message_owner("Up and running!"))
            await send_message_task

        await self.sync_all_application_commands()

    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.CheckFailure):
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
            logging.error("Caught a command error.", exc_info=(type(error), error, error.__traceback__))
            await ctx.send(
                "Oops! You just caused an error ({} caused by {})! Try `{}help <command_name>` for usage information!".format(
                    error.__class__.__name__, error.__cause__.__class__.__name__, ctx.prefix))

    async def invoke(self, ctx: commands.Context):
        if ctx.command is not None and ctx.guild:
            if "admin_locked_servers" in self.global_data and ctx.guild.id in self.global_data["admin_locked_servers"]:
                if not ctx.author.guild_permissions.administrator:
                    raise commands.CheckFailure("This server has locked all commands to administrators.")
            if self.global_data["deny odds"] != 0 and choice(range(self.global_data["deny odds"])) == 0:
                await ctx.send(choice(self.global_data["deny choices"]))
                return
        return await super().invoke(ctx)

    async def message_owner(self, message: str):
        owner: nextcord.User = await self.fetch_user(self.owner_id)
        await owner.send(message)


@click.command()
@click.option("-l",
              "--log-level",
              type=click.Choice(list(logging._nameToLevel.keys()), case_sensitive=False),
              default="INFO")
@click.option("-m", "--message-owner", is_flag=True)
def main(log_level, message_owner):
    global bot

    clean_files()

    numeric_level = logging._nameToLevel[log_level]

    logging.basicConfig(filename=f'_logs/{datetime.now().strftime("%m-%d-%Y %H_%M_%S.log")}',
                        level=numeric_level,
                        format='%(levelname)s::%(asctime)s::%(message)s',
                        datefmt='%m/%d/%Y %H:%M:%S')
    logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))

    intents: nextcord.Intents = nextcord.Intents.default()
    intents.members = True
    intents.message_content = True
    intents.presences = True

    bot = StatiCat(intents=intents)

    if message_owner:
        bot.send_startup_message_to_owner = True

    logging.info(sys.argv)

    bot.run(os.environ[TOKEN_KEY])
    if bot.should_restart:
        restart_after_shutdown()


if __name__ == '__main__':
    try:
        load_env()
    except EnvironmentError:
        print("Failed to load environment config from .env file. Please add the necessary fields that have been added")
    else:
        main()
