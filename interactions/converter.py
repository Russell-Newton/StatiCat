from typing import Optional, TypeVar, Union, Type, Generic

import nextcord
from nextcord.ext.commands import ArgumentParsingError

from bot import StatiCat

T = TypeVar("T", covariant=True)
Channel = Union[nextcord.abc.GuildChannel, nextcord.Thread, nextcord.abc.PrivateChannel]


class OptionConverter(Generic[T]):
    _registry: dict[int, Type[object]] = {}

    def __init_subclass__(cls, _type=3, **kwargs):
        super().__init_subclass__(**kwargs)
        cls._registry[_type] = cls

    def __new__(cls, bot: StatiCat, interaction: nextcord.Interaction, option: dict):
        _type = option["type"]
        if _type not in cls._registry.keys():
            raise NotImplementedError(f"No converter exists for an option of type {_type}!")

        subclass = cls._registry[_type]
        obj = super().__new__(subclass)
        return obj

    def __init__(self, bot: StatiCat, interaction: nextcord.Interaction, option: dict):
        self.bot = bot
        self.interaction = interaction
        self.value = option["value"]

        self.interaction_data = interaction.data
        self.resolved_users: Optional[dict] = self.interaction_data.get("users", None)
        self.resolved_members: Optional[dict] = self.interaction_data.get("members", None)
        self.resolved_roles: Optional[dict] = self.interaction_data.get("roles", None)
        self.resolved_channels: Optional[dict] = self.interaction_data.get("channels", None)

    async def convert(self) -> T:
        raise NotImplementedError


class StrConverter(OptionConverter[str], _type=3):
    async def convert(self) -> str:
        return self.value


class IntConverter(OptionConverter[int], _type=4):
    async def convert(self) -> int:
        return int(self.value)


class BoolConverter(OptionConverter[bool], _type=5):
    async def convert(self) -> bool:
        return bool(self.value)


class FloatConverter(OptionConverter[float], _type=10):
    async def convert(self) -> float:
        return float(self.value)


class MemberConverter(OptionConverter[Union[nextcord.User, nextcord.Member]], _type=6):
    async def convert(self) -> Union[nextcord.User, nextcord.Member]:
        guild: nextcord.Guild = self.interaction.guild
        if guild is None:
            user = await self.bot.fetch_user(int(self.value))
            if user is None:
                raise ArgumentParsingError(f"Cannot find user with id {self.value}!")
            return user
        member = await guild.fetch_member(int(self.value))
        if member is None:
            raise ArgumentParsingError(f"Cannot find member with id {self.value}!")
        return member


class RoleConverter(OptionConverter[nextcord.Role], _type=8):
    async def convert(self) -> nextcord.Role:
        guild: nextcord.Guild = self.interaction.guild
        role = guild.get_role(int(self.value))
        if role is None:
            raise ArgumentParsingError(f"Cannot find role with id {self.value}!")
        return role


class ChannelConverter(OptionConverter[Channel], _type=7):
    async def convert(self) -> Channel:
        channel = await self.bot.fetch_channel(int(self.value))
        if channel is None:
            raise ArgumentParsingError(f"Cannot find channel with id {self.value}!")
        return channel
