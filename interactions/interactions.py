import abc
import asyncio
import inspect
import logging
import traceback
from typing import Type, Union, Any, Optional, List

from nextcord.ext.commands import Command, Cog, CheckFailure
from nextcord.ext.commands._types import Check

from bot import StatiCat
import nextcord
import nextcord.ext.commands as commands
from cogwithdata import CogWithData
from interactions.context import SlashInteractionAliasContext
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
        self.subcommands: dict[str, ApplicationCommand] = {}

        guilds = guild if isinstance(guild, list) else [guild]
        for guild_id in guilds:
            self.instances[guild_id] = {}

        try:
            checks = callback.__commands_checks__
            checks.reverse()
        except AttributeError:
            checks = kwargs.get('checks', [])

        self.checks: List[Check] = checks

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

    def pre_check(self, interaction: nextcord.Interaction):
        if "admin_locked_servers" in self.bot.global_data and interaction.guild_id in self.bot.global_data["admin_locked_servers"]:
            if not interaction.user.guild_permissions.administrator:
                raise commands.CheckFailure("This server has locked all commands to administrators.")

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
        self.subcommands[subcommand.command_name] = subcommand
        subcommand.parent = self
        subcommand.bot = self.bot
        subcommand.cog = self.cog
        self.evaluate_subcommands()

    def add_check(self, func: Check) -> None:
        """Adds a check to the command.

        This is the non-decorator interface to :func:`.check`.
        """

        self.checks.append(func)

    def remove_check(self, func: Check) -> None:
        """Removes a check from the command.

        This function is idempotent and will not raise an exception
        if the function is not in the command's checks.
        """

        try:
            self.checks.remove(func)
        except ValueError:
            pass


class ApplicationCommandsDict(dict[tuple[str, int], ApplicationCommand]):

    def __init__(self, bot: StatiCat, **kwargs):
        if bot is None:
            raise ValueError("Cannot have an ApplicationCommandsDict with a null bot!")
        super().__init__(**kwargs)
        self.bot = bot

    def __setitem__(self, k: tuple[str, int], v: ApplicationCommand) -> None:
        v.bot = self.bot
        for subcommand in v.subcommands.values():
            subcommand.bot = self.bot
            subcommand.cog = v.cog
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
            command.pre_check(self.interaction)
            return await command.invoke(self.interaction)
        except CheckFailure:
            if self.interaction.response.is_done():
                await self.interaction.followup.send(content="You don't have permission to use that command here.", ephemeral=True)
            else:
                await self.interaction.response.send_message(content="You don't have permission to use that command here.", ephemeral=True)
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
        self.command_edit_data["description"] = command_description.split("\n")[0][:100]
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
            for sub in com.subcommands.values():
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

    async def invoke_subcommand(self, interaction: nextcord.Interaction, subcommand_options):
        subcommand: SlashCommand = self.subcommands[subcommand_options["name"]] # type: ignore
        if not await subcommand.can_run(interaction):
            raise CheckFailure(f'The check functions for command {self.command_name} failed.')
        options = subcommand_options.get("options", [])

        args = []
        if subcommand.cog is not None:
            args.append(subcommand.cog)
        args.append(interaction)

        kwargs = {}
        for option in options:
            kwargs[option["name"]] = await OptionConverter(self.bot, interaction, option).convert()

        return await subcommand.callback(*args, **kwargs)

    async def invoke(self, interaction: nextcord.Interaction):
        if not await self.can_run(interaction):
            raise CheckFailure(f'The check functions for command {self.command_name} failed.')

        args = []
        if self.cog is not None:
            args.append(self.cog)
        args.append(interaction)
        kwargs = {}

        data = interaction.data

        options = data.get("options", [])
        # Application Command Interaction Data Option Structure
        for option in options:
            if option["type"] == 1:
                return await self.invoke_subcommand(interaction, option)
            if option["type"] == 2:
                raise ValueError("I haven't gotten to subcommand groups yet")

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

        def decorator(command):
            if isinstance(command, Command):
                new_slash = cls(command.callback, list(self.instances.keys()), name=name, checks=command.checks, **attrs)

                async def slashified_callback(*args, **kwargs):
                    if new_slash.cog is not None:
                        idx = 1
                    else:
                        idx = 0
                    new_args = list(args)
                    interaction: nextcord.Interaction = new_args[idx]
                    await interaction.response.defer()
                    new_args[idx] = SlashInteractionAliasContext(interaction, new_slash.bot, new_args, kwargs)
                    new_args = tuple(new_args)

                    return await command.callback(*new_args, **kwargs)

                slashified_callback.__name__ = command.callback.__name__
                if hasattr(command.callback, "__commands_checks__"):
                    slashified_callback.__commands_checks__ = command.callback.__commands_checks__

                new_slash.callback = slashified_callback
                command.__slash_command__ = new_slash

                self.add_subcommand(new_slash)

                return command
            if isinstance(command, SlashCommand):
                raise TypeError(f'Callback is already a {type(command)}.')
            if not asyncio.iscoroutinefunction(command):
                raise TypeError('Callback must be a coroutine.')

            subcommand = cls(command, list(self.instances.keys()), name=name, **attrs)
            self.add_subcommand(subcommand)
            return subcommand

        return decorator

    async def can_run(self, interaction: nextcord.Interaction) -> bool:
        ctx = SlashInteractionAliasContext(interaction, self.bot)

        original = ctx.command
        ctx.command = self

        try:
            if not await self.bot.can_run(ctx):
                raise CheckFailure(f'The global check functions for command {self.command_name} failed.')

            cog = self.cog
            if cog is not None:
                local_check = Cog._get_overridden_method(cog.cog_check)
                if local_check is not None:
                    ret = await nextcord.utils.maybe_coroutine(local_check, ctx)
                    if not ret:
                        return False

            predicates = self.checks
            if not predicates:
                # since we have no checks, then we just return True.
                return True

            return await nextcord.utils.async_all(predicate(ctx) for predicate in predicates)  # type: ignore
        finally:
            ctx.command = original


class MessageCommand(ApplicationCommand, _type=3):
    def __init__(self, callback, guild: Union[int, list[int]] = None, **kwargs):
        super().__init__(callback, guild, **kwargs)

    async def invoke(self, interaction: nextcord.Interaction):
        args = []
        if self.cog is not None:
            args.append(self.cog)
        args.append(interaction)

        message_id = interaction.data["target_id"]
        channel_id = interaction.data["resolved"]["messages"][message_id]["channel_id"]
        channel = await self.bot.fetch_channel(channel_id)
        message: nextcord.Message = await channel.fetch_message(message_id)
        args.append(message)

        return await self.callback(*args)

    def evaluate_subcommands(self, *args, **kwargs):
        pass

    def subcommand(self, name: str = None, cls=None, **attrs):
        pass


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
        for item in await self.get_deployed_global_commands():
            await ctx.send(str(item))
        # await ctx.send(str(await self.get_deployed_global_commands()))
        guild: nextcord.Guild = ctx.guild
        if guild:
            await ctx.send("THIS GUILD'S APPLICATION COMMANDS:")
            for item in await self.get_deployed_guild_commands(guild.id):
                await ctx.send(str(item))

    async def add_command(self, command: ApplicationCommand, sync: bool = True):
        self.commands[(command.command_name, command.application_command_type)] = command

        if sync:
            await self.sync_commands()

    async def add_from_cog(self, cog: commands.Cog, sync: bool = True):
        for base in reversed(cog.__class__.__mro__):
            for elem, value in base.__dict__.items():
                if hasattr(value, '__slash_command__'):
                    value = value.__slash_command__
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

    async def remove_command(self, command: ApplicationCommand, sync: bool = True):
        if command.parent is not None:
            return
        self.commands.pop((command.command_name, command.application_command_type))
        if sync:
            await self.sync_commands()

    async def remove_from_cog(self, cog: commands.Cog, sync: bool = True):
        for base in reversed(cog.__class__.__mro__):
            for elem, value in base.__dict__.items():
                if hasattr(value, '__slash_command__'):
                    value = value.__slash_command__
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
                try:
                    await command.deploy()
                except nextcord.HTTPException or nextcord.Forbidden as error:
                    logging.error(f"Unable to sync command {command.command_name}!",
                                  exc_info=(type(error), error, error.__traceback__))
                    print(f"Unable to sync command {command.command_name}!")
                    traceback.print_exception(type(error), error, error.__traceback__)

    @commands.Cog.listener()
    async def on_interaction(self, interaction: nextcord.Interaction):
        await InteractionHandler(interaction).handle(self.commands)


def slash_command(guild: Union[int, list[int]] = None, name: str = None, cls=None, **attrs):
    """
    A decorator that transforms a function into a :class:`.SlashCommand`. Such functions must take in a
    :class:`nextcord.Interaction` as their first (not self) parameter.

    :param guild: The guild id to register this slash command for.
    :param name: The name to create the slash command with. By default this uses the function name unchanged.
    :param cls: The class to construct with. By default this is :class:`.SlashCommand`.
    :param attrs: Keyword arguments to pass into the construction of the class denoted by ``cls``.
    :raises TypeError: If the function is not a coroutine or is already a slash command.
    """

    if cls is None:
        cls = SlashCommand

    def decorator(command):
        if isinstance(command, SlashCommand):
            raise TypeError('Callback is already a slash command.')
        if not asyncio.iscoroutinefunction(command):
            raise TypeError('Callback must be a coroutine.')

        return cls(command, guild, name=name, **attrs)

    return decorator


def command_also_slash_command(guild: Union[int, list[int]] = None, name: str = None, cls=None, **attrs):
    """
    A decorator that creates a SlashCommand from a Command while preserving the original Command.
    :param guild:
    :param name:
    :param cls:
    :param attrs:
    :return:
    """

    if cls is None:
        cls = SlashCommand

    def decorator(command: Command):

        new_slash = cls(command.callback, guild, name=name, checks=command.checks, **attrs)

        async def slashified_callback(*args, **kwargs):
            if new_slash.cog is not None:
                idx = 1
            else:
                idx = 0
            new_args = list(args)
            interaction: nextcord.Interaction = new_args[idx]
            await interaction.response.defer()
            new_args[idx] = SlashInteractionAliasContext(interaction, new_slash.bot, new_args, kwargs)
            new_args = tuple(new_args)

            return await command.callback(*new_args, **kwargs)
        slashified_callback.__name__ = command.callback.__name__
        if hasattr(command.callback, "__commands_checks__"):
            slashified_callback.__commands_checks__ = command.callback.__commands_checks__

        new_slash.callback = slashified_callback
        command.__slash_command__ = new_slash

        return command

    return decorator


def message_command(guild: Union[int, list[int]] = None, name: str = None, cls=None, **attrs):
    """
    A decorator that transforms a function into a :class:`.MessageCommand`. Such functions must take in a
    :class:`nextcord.Interaction` and a :class:`nextcord.Message` as their first two (not self) parameters.

    :param guild: The guild id to register this slash command for.
    :param name: The name to create the slash command with. By default this uses the function name unchanged.
    :param cls: The class to construct with. By default this is :class:`.MessageCommand`.
    :param attrs: Keyword arguments to pass into the construction of the class denoted by ``cls``.
    :raises TypeError: If the function is not a coroutine or is already a slash command.
    """
    if cls is None:
        cls = MessageCommand

    def decorator(command):
        if isinstance(command, MessageCommand):
            raise TypeError("Callback is already a message command.")
        if not asyncio.iscoroutinefunction(command):
            raise TypeError('Callback must be a coroutine.')

        return cls(command, guild, name=name, **attrs)

    return decorator
