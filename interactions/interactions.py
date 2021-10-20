import abc
import asyncio
import inspect
import logging
from typing import Type, Union, Any, Optional

from bot import StatiCat
import nextcord
import nextcord.ext.commands as commands
from cogwithdata import CogWithData
from interactions.converter import OptionConverter

slash_command_option_type_map = {
    "subcommand": 1,
    "subcommandgroup": 2,
    str: 3,
    int: 4,
    bool: 5,
    nextcord.User: 6,
    nextcord.Member: 6,
    nextcord.TextChannel: 7,
    nextcord.DMChannel: 7,
    nextcord.VoiceChannel: 7,
    nextcord.GroupChannel: 7,
    nextcord.CategoryChannel: 7,
    nextcord.StoreChannel: 7,
    nextcord.StageChannel: 7,
    nextcord.Thread: 7,
    nextcord.Role: 8,
    float: 10
}


def deep_options_equal(options1: dict, options2: dict):
    import operator

    def _deep_dict_equal(d1, d2):
        k1 = sorted(d1.keys())
        k2 = sorted(d2.keys())
        if k1 != k2:  # keys should be exactly equal
            return False
        return sum(deep_options_equal(d1[k], d2[k]) for k in k1) == len(k1)

    def _deep_iter_equal(l1, l2):
        if len(l1) != len(l2):
            return False
        return sum(deep_options_equal(v1, v2) for v1, v2 in zip(l1, l2)) == len(l1)

    op = operator.eq
    c1, c2 = (options1, options2)

    # guard against strings because they are also iterable
    # and will consistently cause a RuntimeError (maximum recursion limit reached)
    if not isinstance(options1, str):
        if isinstance(options1, dict):
            op = _deep_dict_equal
        else:
            try:
                c1, c2 = (list(iter(options1)), list(iter(options2)))
            except TypeError:
                c1, c2 = options1, options2
            else:
                op = _deep_iter_equal

    return op(c1, c2)


def compare_online_with_offline_commands(online: dict, offline: dict) -> bool:
    if offline is None:
        return False
    same_type = online["type"] == offline["type"]
    same_name = online["name"] == offline["name"]
    same_description = online.get("description", "") == offline.get("description", "")
    same_options = deep_options_equal(online.get("options", []), offline.get("options", []))
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
        self.command_edit_data: dict[str, Any] = {
            "name": self.command_name,
            "type": self.application_command_type,
            "default_permission": self.default_permission
        }
        self.parent: Optional[ApplicationCommand] = None

        # Instances are saved as
        # guild_id/None: {"data": json_data, "deploy_url": deploy_url}
        self.instances: dict[Optional[int], dict[str, Any]] = {}
        self.subcommands: list[ApplicationCommand] = list()

        guilds = guild if isinstance(guild, list) else [guild]
        for guild_id in guilds:
            self.instances[guild_id] = {}

    async def deploy(self):
        if self.bot is None:
            return
        for guild, instance in self.instances.items():
            if guild is None:
                response_instance = await self.bot.http.upsert_global_command(self.bot.user.id, self.command_edit_data)
            else:
                response_instance = await self.bot.http.upsert_guild_command(self.bot.user.id, guild,
                                                                             self.command_edit_data)

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

    @abc.abstractmethod
    def evaluate_subcommands(self, *args, **kwargs):
        raise NotImplementedError

    @abc.abstractmethod
    def subcommand(self, name: str = None, cls=None, **attrs):
        raise NotImplementedError

    def add_subcommand(self, subcommand):
        if subcommand.parent is not None:
            raise ValueError("An ApplicationCommand can only have one parent!")
        self.subcommands.append(subcommand)
        subcommand.parent = self
        self.evaluate_subcommands()


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
        try:
            return await command.invoke(self.interaction)
        except Exception as error:
            logging.exception("Failed to invoke an Application Command.", exc_info=error)


class MessageComponentHandler(InteractionHandler, _type=nextcord.InteractionType.component):
    async def handle(self, available_commands: ApplicationCommandsDict):
        # Additional options could be used here for component callback
        pass


class SlashCommand(ApplicationCommand, _type=1):

    def __init__(self, callback, guild: Union[int, list[int]] = None, **kwargs):
        super().__init__(callback, guild, **kwargs)

        command_description = kwargs.get("help")
        if command_description is not None:
            command_description = inspect.cleandoc(command_description)
        else:
            command_description = inspect.getdoc(callback) or self.command_name
            if isinstance(command_description, bytes):
                command_description = command_description.decode("utf-8")

        # Add a description and options to each json_data instance
        self.command_edit_data["description"] = command_description
        self.prep_parameters()

    def prep_parameters(self):
        command_options = []
        signature = inspect.signature(self.callback)
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

        self.command_edit_data["options"] = command_options[2:]
        if len(self.command_edit_data["options"]) == 0:
            self.command_edit_data.pop("options")

    def add_subcommand(self, subcommand: ApplicationCommand):
        super().add_subcommand(subcommand)
        self.evaluate_subcommands()

    def evaluate_subcommands(self, current_depth=0):
        # Refresh the options to regroup subcommands
        if "options" in self.command_edit_data.keys():
            self.command_edit_data.pop("options")
        self.prep_parameters()

        # Evaluate one level lower
        def eval_down(com):
            for sub in com.subcommands:
                sub_data = sub.command_edit_data
                if len(sub.subcommands) > 0:
                    sub_data["type"] = slash_command_option_type_map["subcommandgroup"]
                else:
                    sub_data["type"] = slash_command_option_type_map["subcommand"]

                if "default_permission" in sub_data.keys():
                    sub_data.pop("default_permission")

                if "options" not in com.command_edit_data.keys():
                    com.command_edit_data["options"] = []
                com.command_edit_data["options"].append(sub_data)

        eval_down(self)

        # Reevaluate up
        if current_depth >= 2:
            raise NotImplementedError(
                f"Nesting of subcommand groups is not supported! Problem exists with {self.command_edit_data}")
        if self.parent is not None:
            try:
                self.parent.evaluate_subcommands(current_depth=current_depth + 1)
            except NotImplementedError:
                raise NotImplementedError(
                    f"Nesting of subcommand groups is not supported! Problem exists with {self.command_edit_data}")

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
                await interaction.response.send_message("Subcommands are currently not supported :(", ephemeral=True)
                raise NotImplementedError
            kwargs[option["name"]] = await OptionConverter(self.bot, interaction, option).convert()

        return await self.callback(*args, **kwargs)

    def subcommand(self, name: str = None, cls=None, **attrs):
        """
        A decorator that transforms a function into a subcommand of this ApplicationCommand.
        :param name:
        :param cls:
        :param attrs:
        :return:
        """
        if cls is None:
            cls = SlashCommand

        def decorator(func):
            if isinstance(func, SlashCommand):
                raise TypeError(f'Callback is already a {type(func)}.')
            if not asyncio.iscoroutinefunction(func):
                raise TypeError('Callback must be a coroutine.')

            subcommand = cls(func, list(self.instances.keys()), name=name, **attrs)
            self.add_subcommand(subcommand)
            return subcommand

        return decorator


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
                    if value.parent is None:
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
                    if value.parent is None:
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
            else:
                offline = self.commands[(command["name"], command["type"])]
                if None not in offline.instances.keys():
                    await self.bot.http.delete_global_command(self.bot.user.id, command['id'])
                    logging.info(f"Deleted stale command:\n{command}")
                elif compare_online_with_offline_commands(command, offline.command_edit_data):
                    intersection.append(command["name"])

        # Identify guild commands that need syncing
        for guild in self.bot.guilds:
            guild_id = guild.id
            upstream = await self.get_deployed_guild_commands(guild_id)
            for command in upstream:
                if (command["name"], command["type"]) not in self.commands.keys():
                    await self.bot.http.delete_guild_command(self.bot.user.id, guild_id, command['id'])
                    logging.info(f"Deleted stale command:\n{command}")
                else:
                    offline = self.commands[(command["name"], command["type"])]
                    if guild_id not in offline.instances.keys():
                        await self.bot.http.delete_guild_command(self.bot.user.id, guild_id, command['id'])
                        logging.info(f"Deleted stale command:\n{command}")
                    elif compare_online_with_offline_commands(command, offline.command_edit_data):
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
