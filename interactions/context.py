import inspect
from distutils.cmd import Command
from typing import Any, Optional, List, Union, Dict

import nextcord
import nextcord.ext.commands as commands
from nextcord import Message, Embed, User, Member, Guild
from nextcord.ext.commands.context import CogT, P, T, BotT
from nextcord.ext.commands.view import StringView
from nextcord.interactions import Interaction
from nextcord.state import ConnectionState
from nextcord.ui import View
from nextcord.utils import MISSING


class SlashInteractionAliasContext(commands.Context):
    def __init__(self,
                 interaction: Interaction,
                 bot: commands.Bot,
                 args: list = MISSING,
                 kwargs: dict[str, Any] = MISSING):
        self.interaction = interaction
        self.message: Message = interaction.message
        self.bot: BotT = bot
        self.args: List[Any] = args or []
        self.kwargs: Dict[str, Any] = kwargs or {}
        self.prefix: Optional[str] = None
        self.command: Optional[Command] = None
        self.view: StringView = StringView(self.message) if self.message else None
        self.invoked_with: Optional[str] = None
        self.invoked_parents: List[str] = []
        self.invoked_subcommand: Optional[Command] = None
        self.subcommand_passed: Optional[str] = None
        self.command_failed: bool = False
        self.current_parameter: Optional[inspect.Parameter] = None
        self._state: ConnectionState = self.interaction._state
        self._has_deferred = False

    @nextcord.utils.cached_property
    def guild(self) -> Optional[Guild]:
        return self.interaction.guild

    @nextcord.utils.cached_property
    def channel(self):
        return self.interaction.channel

    @nextcord.utils.cached_property
    def author(self) -> Union[User, Member]:
        return self.interaction.user

    async def invoke(self, command, /, *args, **kwargs) -> T:
        raise ValueError("This Context was created for a SlashCommand and cannot be used to invoke standard Commands.")

    async def reinvoke(self, *, call_hooks: bool = False, restart: bool = True) -> None:
        raise ValueError("This Context was created for a SlashCommand and cannot be used to invoke standard Commands.")

    async def send_help(self, *args: Any) -> Any:
        raise ValueError("This Context was created for a SlashCommand and cannot be used to send Command help.")

    async def reply(self, content: Optional[str] = None, **kwargs: Any) -> Message:
        return await self.send(content=content, **kwargs)

    async def send(
            self,
            content: Optional[Any] = None,
            *,
            embed: Embed = MISSING,
            embeds: List[Embed] = MISSING,
            view: View = MISSING,
            tts: bool = False,
            ephemeral: bool = False,
            **kwargs
    ):
        if not self._has_deferred:
            await self.interaction.response.defer()
            self._has_deferred = True
        return await self.interaction.followup.send(
            content=content,
            embed=embed,
            embeds=embeds,
            view=view,
            tts=tts,
            ephemeral=ephemeral,
            **kwargs
        )

    async def defer(self):
        await self.interaction.response.defer()
        self._has_deferred = True
