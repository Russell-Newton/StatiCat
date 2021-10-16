import abc
import asyncio
import inspect
import logging
from typing import Type, Union, Any, Optional

from bot import StatiCat
import nextcord
import nextcord.ext.commands as commands
from cogwithdata import CogWithData


slash_command_option_type_map = {
    "subcommand": 1,
    "subcommandgroup": 2,
    str: 3,
    int: 4,
    bool: 5,
    nextcord.User: 6,
    nextcord.abc.GuildChannel: 7,
    nextcord.Role: 8,
    nextcord.Member: 9,
    float: 10
}


def compare_online_with_offline_commands(online: dict, offline: dict) -> bool:
    if offline is None:
        return False
    same_type = online["type"] == offline["type"]
    same_name = online["name"] == offline["name"]
    same_description = online.get("description", "") == offline.get("description", "")
    same_options = online.get("options", []) == offline.get("options", [])
    same_default_permission = online.get("default_permission", True) == offline.get("default_permission", True)

    return same_type and same_name and same_description and same_options and same_default_permission


class ApplicationCommand(abc.ABC):
    _registry: dict[str, int] = {}

    def __init_subclass__(cls, _type=1, **kwargs):
        super().__init_subclass__(**kwargs)
        cls._registry[cls.__name__] = _type

    def __init__(self, callback, guild: Union[int, list[int]] = None, **kwargs):
        self.bot: Optional[StatiCat] = None
        self.callback = callback
        self.cog = None
        self.application_command_type: int = self.__class__._registry[self.__class__.__name__]
        self.default_permission: bool = kwargs.get("default_permission", True)
        self.command_name: str = kwargs.get("name") or callback.__name__
        self.parent: Optional[ApplicationCommand] = None

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
                "command_edit_data": data
            }
            self.instances[guild_id] = instance

    async def deploy(self):
        if self.bot is None:
            return
        for guild, instance in self.instances.items():
            data = instance["command_edit_data"]

            if guild is None:
                response_instance = await self.bot.http.upsert_global_command(self.bot.user.id, data)
            else:
                response_instance = await self.bot.http.upsert_guild_command(self.bot.user.id, guild, data)

            logging.info(f"Deployed a {self.__class__.__name__}:\n {response_instance}")

            instance["command_data"] = response_instance

    async def remove(self):
        for guild, instance in self.instances.items():
            data = instance["command_data"]
            if guild is None:
                await self.bot.http.delete_global_command(self.bot.user.id, data.id)
            else:
                await self.bot.http.delete_guild_command(self.bot.user.id, guild, data.id)
            logging.info(f"Removed a {self.__class__.__name__}:\n {data}")

    @abc.abstractmethod
    async def invoke(self, interaction: nextcord.Interaction):
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
    _registry: dict[nextcord.InteractionType, Type[object]] = {}

    def __init_subclass__(cls, _type=nextcord.InteractionType.application_command, **kwargs):
        super().__init_subclass__(**kwargs)
        cls._registry[_type] = cls

    def __new__(cls, interaction: nextcord.Interaction):
        _type = interaction.type
        if _type not in cls._registry.keys():
            raise NotImplementedError(f"No handler exists for an interaction of type {_type}!")

        subclass = cls._registry[_type]
        obj = super().__new__(subclass)
        return obj

    def __init__(self, interaction: nextcord.Interaction):
        self.interaction = interaction

    async def handle(self, available_commands: ApplicationCommandsDict):
        raise NotImplementedError


class PingHandler(InteractionHandler, _type=nextcord.InteractionType.ping):
    async def handle(self, available_commands):
        pass


class ApplicationCommandHandler(InteractionHandler, _type=nextcord.InteractionType.application_command):
    async def handle(self, available_commands: ApplicationCommandsDict):
        target_name = self.interaction.data["name"]
        target_type = self.interaction.data["type"]
        command = available_commands.get((target_name, target_type), None)
        if command is None:
            return
        return await command.invoke(self.interaction)


class MessageComponentHandler(InteractionHandler, _type=nextcord.InteractionType.component):
    async def handle(self, available_commands: ApplicationCommandsDict):
        # Additional options could be used here for component callback
        pass


class SlashCommand(ApplicationCommand, _type=1):

    def __init__(self, callback, guild: Union[int, list[int]] = None, **kwargs):
        super().__init__(callback, guild, **kwargs)
        self.subcommands: list[ApplicationCommand] = list()

        command_description = kwargs.get("help")
        if command_description is not None:
            command_description = inspect.cleandoc(command_description)
        else:
            command_description = inspect.getdoc(callback) or self.command_name
            if isinstance(command_description, bytes):
                command_description = command_description.decode("utf-8")

        command_options = []
        signature = inspect.signature(callback)
        parameters = signature.parameters
        for param_name, param in parameters.items():
            param: inspect.Parameter = param

            option = {
                "type": slash_command_option_type_map.get(param.annotation, 3),
                "name": param_name,
                "description": param_name
            }
            if param.default == inspect.Parameter.empty:
                option["required"] = True

            command_options.append(option)

        command_options.extend(self.process_subcommands())

        # Add a description and options to each json_data instance
        for instance in self.instances.values():
            data = instance["command_edit_data"]
            data["description"] = command_description
            data["options"] = command_options[2:]

    def process_subcommands(self):
        # TODO - Implement this
        subcommands = self.subcommands
        return []

    async def invoke(self, interaction: nextcord.Interaction):
        args = []
        if self.cog is not None:
            args.append(self.cog)
        args.append(interaction)
        kwargs = {}

        data = interaction.data

        options = data.get("options", [])
        # Application Command Interaction Data Option Structure
        for option in options:
            if option["type"] in (1, 2):
                # Subcommand or Subcommand group
                raise NotImplementedError
            kwargs[option["name"]] = option["value"]

        return await self.callback(*args, **kwargs)


class Interactions(CogWithData):

    def __init__(self, bot: StatiCat):
        self.bot = bot
        self.commands: ApplicationCommandsDict = ApplicationCommandsDict(self.bot)
        super().__init__()

    async def get_deployed_global_commands(self) -> list[dict]:
        return await self.bot.http.get_global_commands(self.bot.user.id)

    async def get_deployed_guild_commands(self, guild_id) -> list[dict]:
        try:
            return await self.bot.http.get_guild_commands(self.bot.user.id, guild_id)
        except nextcord.errors.Forbidden:
            return []

    @commands.is_owner()
    @commands.command(name="listappcomms")
    async def list_deployed_commands(self, ctx: commands.Context):
        await ctx.send("GLOBAL APPLICATION COMMANDS:")
        await ctx.send(str(await self.get_deployed_global_commands()))
        guild: nextcord.Guild = ctx.guild
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
            if (command["name"], command["type"]) not in self.commands.keys():
                await self.bot.http.delete_global_command(self.bot.user.id, command['id'])
                logging.info(f"Deleted stale command:\n{command}")
            elif compare_online_with_offline_commands(command, self.commands[(command["name"], command["type"])].instances.get(None, None)["command_edit_data"]):
                intersection.append(command["name"])

        # Identify guild commands that need syncing
        for guild in self.bot.guilds:
            guild_id = guild.id
            upstream = await self.get_deployed_guild_commands(guild_id)
            for command in upstream:
                if (command["name"], command["type"]) not in self.commands.keys():
                    await self.bot.http.delete_guild_command(self.bot.user.id, guild_id,command['id'])
                    logging.info(f"Deleted stale command:\n{command}")
                elif compare_online_with_offline_commands(command, self.commands[(command["name"], command["type"])].instances.get(guild_id, None)["command_edit_data"]):
                    intersection.append(command["name"])

        # Deploy offline commands that should be online
        for (name, _type), command in self.commands.items():
            if name not in intersection:
                await command.deploy()

    @commands.Cog.listener()
    async def on_interaction(self, interaction: nextcord.Interaction):
        await InteractionHandler(interaction).handle(self.commands)


def slash_command(guild: Union[int, list[int]] = None, name: str = None, cls=None, **attrs):
    """
    A decorator that transforms a function into a :class:`SlashCommand`.

    :param guild: The guild id to register this slash command for.
    :param name: The name to create the slash command with. By default this uses the function name unchanged.
    :param cls: The class to construct with. By default this is :class:`.SlashCommand`.
    :param attrs: Keyword arguments to pass into the construction of the class denoted by ``cls``.
    :raises TypeError: If the function is not a coroutine or is already a slash command.
    """

    if cls is None:
        cls = SlashCommand

    def decorator(func):
        if isinstance(func, SlashCommand):
            raise TypeError('Callback is already a slash command.')
        if not asyncio.iscoroutinefunction(func):
            raise TypeError('Callback must be a coroutine.')

        return cls(func, guild, name=name, **attrs)

    return decorator
