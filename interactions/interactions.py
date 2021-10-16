import abc
import logging
from typing import Type, Union, Any, Optional

from bot import StatiCat
import discord
from discord.http import Route
import discord.ext.commands as commands
from cogwithdata import CogWithData


def global_url(bot: StatiCat) -> str:
    return f"/applications/{bot.user.id}/commands"


def guild_url(bot: StatiCat, guild_id: int) -> str:
    if guild_id is None:
        return global_url(bot)
    return f"/applications/{bot.user.id}/guilds/{guild_id}/commands"


class APIRoute(Route):
    BASE = "https://discord.com/api/v8"


def compare_online_with_offline(online: dict, offline: dict) -> bool:
    if offline is None:
        return False
    same_type = online["type"] == offline["type"]
    same_name = online["name"] == offline["name"]
    same_description = online.get("description", "") == offline.get("description", "")
    same_options = online.get("options", None) == offline.get("options", None)
    same_default_permission = online.get("default_permission") == offline.get("default_permission")

    return same_type and same_name and same_description and same_options and same_default_permission


class ApplicationCommand(abc.ABC):
    _registry: dict[str, int] = {}

    def __init_subclass__(cls, _type=1, **kwargs):
        super().__init_subclass__(**kwargs)
        cls._registry[cls.__name__] = _type

    def __init__(self, callback, guild: Union[int, list[int]] = None, **kwargs):
        self.bot = None
        self.callback = callback
        self.cog = None
        self.subcommands: dict[str, ApplicationCommand] = dict()
        self.application_command_type: int = self.__class__._registry[self.__class__.__name__]
        self.default_permission: bool = kwargs.get("default_permission", True)
        self.command_name: str = kwargs.get("name") or callback.__name__

        # Instances are saved as
        # guild_id/None: {"data": json_data, "deploy_url": deploy_url}
        self.instances: dict[Optional[int], dict[str, Any]] = {}

        guilds = guild if isinstance(guild, list) else [guild]
        for guild_id in guilds:
            data = {
                "name": self.command_name,
                "type": self.application_command_type,
                "default_permission": self.default_permission
            }

            instance: dict[str, Any] = {
                "data": data
            }
            self.instances[guild_id] = instance

    async def deploy(self):
        if self.bot is None:
            return
        for guild, instance in self.instances.items():
            data = instance["data"]
            if "deploy_url" not in instance.keys():
                instance["deploy_url"] = guild_url(self.bot, guild)
            url = instance["deploy_url"]

            response_instance: dict = await self.bot.http.request(
                APIRoute("POST", url), json=data
            )
            logging.info(f"Deployed a {self.__class__.__name__}:\n {response_instance}")

            instance["data"] = response_instance

    async def remove(self):
        for _, instance in self.instances.items():
            data = instance["data"]
            deploy_url = instance["data"]
            url = f"{deploy_url}/{data['id']}"
            await self.bot.http.request(APIRoute("DELETE", url))
            logging.info(f"Removed a {self.__class__.__name__}:\n {data}")

    @abc.abstractmethod
    async def invoke(self, interaction: dict):
        raise NotImplementedError


class ApplicationCommandsDict(dict[tuple[str, int], ApplicationCommand]):

    def __init__(self, bot: StatiCat, **kwargs):
        if bot is None:
            raise ValueError("Cannot have an ApplicationCommandsDict with a null bot!")
        super().__init__(**kwargs)
        self.bot = bot

    def __setitem__(self, k: tuple[str, int], v: ApplicationCommand) -> None:
        v.bot = self.bot
        super().__setitem__(k, v)


class InteractionHandler:
    _registry: dict[int, Type[object]] = {}

    def __init_subclass__(cls, _type=2, **kwargs):
        super().__init_subclass__(**kwargs)
        cls._registry[_type] = cls

    def __new__(cls, interaction: dict):
        _type = interaction["type"]
        if _type not in cls._registry.keys():
            raise NotImplementedError(f"No handler exists for an interaction of type {_type}!")

        subclass = cls._registry[_type]
        obj = super().__new__(subclass)
        return obj

    def __init__(self, interaction: dict):
        self.interaction = interaction

    async def handle(self, available_commands: ApplicationCommandsDict):
        raise NotImplementedError


class PingHandler(InteractionHandler, _type=1):
    async def handle(self, available_commands):
        pass


class ApplicationCommandHandler(InteractionHandler, _type=2):             # ApplicationCommands use type 2 interactions
    async def handle(self, available_commands: ApplicationCommandsDict):
        target_name = self.interaction["data"]["name"]
        target_type = self.interaction["data"]["type"]
        command = available_commands.get((target_name, target_type), None)
        if command is None:
            return
        return await command.invoke(self.interaction)


class Interactions(CogWithData):

    def __init__(self, bot: StatiCat):
        self.bot = bot
        self.commands: ApplicationCommandsDict = ApplicationCommandsDict(self.bot)
        super().__init__()

    async def get_deployed_global_commands(self) -> list[dict]:
        return await self.bot.http.request(APIRoute("GET", global_url(self.bot)))

    async def get_deployed_guild_commands(self, guild_id) -> list[dict]:
        try:
            return await self.bot.http.request(APIRoute("GET", guild_url(self.bot, guild_id)))
        except discord.errors.Forbidden:
            return []

    @commands.is_owner()
    @commands.command(name="listappcomms")
    async def list_deployed_commands(self, ctx: commands.Context):
        await ctx.send("GLOBAL APPLICATION COMMANDS:")
        await ctx.send(str(await self.get_deployed_global_commands()))
        guild: discord.Guild = ctx.guild
        if guild:
            await ctx.send("THIS GUILD'S APPLICATION COMMANDS:")
            await ctx.send(str(await self.get_deployed_guild_commands(guild.id)))

    async def add_from_cog(self, cog: commands.Cog, sync: bool = True):
        for base in reversed(cog.__class__.__mro__):
            for elem, value in base.__dict__.items():
                if hasattr(value, 'application_command_type'):
                    if isinstance(value, staticmethod):
                        raise TypeError(f"ApplicationCommand {cog.__name__}.{elem} must not be a staticmethod.")
                    value: ApplicationCommand = value
                    value.cog = cog
                    self.commands[(value.command_name, value.application_command_type)] = value

        if sync:
            await self.sync_commands()

    async def add_from_loaded_cogs(self, sync: bool = True):
        for cog_name in self.bot.cogs:
            cog = self.bot.get_cog(cog_name)
            await self.add_from_cog(cog, False)

        if sync:
            await self.sync_commands()

    async def remove_from_cog(self, cog: commands.Cog, sync: bool = True):
        for base in reversed(cog.__class__.__mro__):
            for elem, value in base.__dict__.items():
                if hasattr(value, 'application_command_type'):
                    if isinstance(value, staticmethod):
                        raise TypeError(f"ApplicationCommand {cog.__name__}.{elem} must not be a staticmethod.")
                    value: ApplicationCommand = value
                    self.commands.pop((value.command_name, value.application_command_type))

        if sync:
            await self.sync_commands()

    async def sync_commands(self):
        intersection: list[str] = []

        # Identify global commands that need syncing
        upstream = await self.get_deployed_global_commands()
        for command in upstream:
            if command["name"] not in self.commands.keys():
                await self.bot.http.request(APIRoute("DELETE", f"{global_url(self.bot)}/{command['id']}"))
                logging.info(f"Deleted stale command:\n{command}")
            elif compare_online_with_offline(command, self.commands[(command["name"], command["type"])].instances.get(None, None)):
                intersection.append(command["name"])

        # Identify guild commands that need syncing
        for guild in self.bot.guilds:
            guild_id = guild.id
            upstream = await self.get_deployed_guild_commands(guild_id)
            for command in upstream:
                if command["name"] not in self.commands.keys():
                    await self.bot.http.request(APIRoute("DELETE", f"{guild_url(self.bot, guild_id)}/{command['id']}"))
                    logging.info(f"Deleted stale command:\n{command}")
                elif compare_online_with_offline(command, self.commands[(command["name"], command["type"])].instances.get(None, None)):
                    intersection.append(command["name"])

        # Deploy offline commands that should be online
        for (name, _type), command in self.commands.items():
            if name not in intersection:
                await command.deploy()

    @commands.Cog.listener()
    async def on_socket_response(self, message):
        resp_type = message["t"]
        if resp_type != "INTERACTION_CREATE":
            return

        interaction = message["d"]
        await InteractionHandler(interaction).handle(self.commands)
