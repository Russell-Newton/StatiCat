import asyncio
import inspect

import discord
from typing import Union

from interactions import InteractionHandler, ApplicationCommand, APIRoute
from interactions.interactions import ApplicationCommandsDict

from bot import StatiCat


option_type_map = {
    "subcommand": 1,
    "subcommandgroup": 2,
    str: 3,
    int: 4,
    bool: 5,
    discord.User: 6,
    discord.abc.GuildChannel: 7,
    discord.Role: 8,
    discord.Member: 9,
    float: 10
}

class SlashContext:
    def __init__(self, bot: StatiCat, interaction):
        self.bot = bot
        self.interaction = interaction
        self.base_url = f'/interactions/{interaction["id"]}/{interaction["token"]}'
        self.followup_url = f'/webhooks/{self.bot.user.id}/{interaction["token"]}'
        self.responded = False

    async def say(self,
                  content: str = "",
                  *,
                  file: list[discord.File] = None,
                  embeds: list[discord.Embed] = None,
                  tts: bool = False,
                  allowed_mentions: discord.AllowedMentions = None,
                  hidden: bool = False):
        # Build new followup message json
        json = {
            "content": content,
            "tts": tts,
            "embeds": embeds or [],
            "allowed_mentions": allowed_mentions or {},
        }
        if hidden:
            json["flags"] = 64

        if not self.responded:
            initial_response_data = {
                "type": 4,
                "data": json
            }
            await self.bot.http.request(APIRoute("POST", self.base_url + "/callback"),
                                        json=initial_response_data)
            self.responded = True
        else:
            await self.bot.http.request(APIRoute("POST", self.followup_url), json=json)


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

        command_options = []
        signature = inspect.signature(callback)
        parameters = signature.parameters
        for param_name, param in parameters.items():
            param: inspect.Parameter = param

            option = {
                "type": option_type_map.get(param.annotation, 3),
                "name": param_name,
                "description": param_name
            }
            if param.default == inspect.Parameter.empty:
                option["required"] = True

            command_options.append(option)

        command_options.extend(self.process_subcommands())

        # Add a description and options to each json_data instance
        for instance in self.instances.values():
            data = instance["data"]
            data["description"] = command_description
            data["options"] = command_options[2:]

    def process_subcommands(self):
        # TODO - Implement this
        subcommands = self.subcommands
        return []

    async def invoke(self, interaction: dict):
        ctx = SlashContext(self.bot, interaction)

        args = []
        if self.cog is not None:
            args.append(self.cog)
        args.append(ctx)
        kwargs = {}

        data = interaction["data"]

        options = data.get("options", None)
        # Application Command Interaction Data Option Structure
        for option in options:
            if option["type"] in (1, 2):
                # Subcommand or Subcommand group
                raise NotImplementedError
            kwargs[option["name"]] = option["value"]

        return await self.callback(*args, **kwargs)


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