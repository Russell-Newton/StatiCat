from typing import List

import discord
import discord.ext.commands as commands

from universals import get_owner_data


class NoPermissionError(commands.CheckFailure):
    pass


def check_permissions(permissions: List[str], check_all: bool = True):
    """
    Used to check if a Guild member has certain permissions.
    :param permissions: A list of permission names to check for
    :param check_all: If True, all permissions are required. Otherwise, at least one is required.
    """

    # Check for valid flags
    discord.Permissions(**{
        perm: True
        for perm in permissions
    })

    async def predicate(ctx: commands.Context):
        if not isinstance(ctx.author, discord.Member):
            return False
        for perm in permissions:
            has_permission = getattr(ctx.author.guild_permissions, perm)
            if check_all and not has_permission:
                raise NoPermissionError
            elif not check_all and has_permission:
                return True
        if check_all:
            return True
        raise NoPermissionError

    return commands.check(predicate)


def check_in_guild():
    """
    Check if the command is called in a guild channel instead of a private message.
    """

    async def predicate(ctx: commands.Context):
        return ctx.guild is not None

    return commands.check(predicate)


def check_in_private():
    """
    Check if the command is called in a DM.
    """

    async def predicate(ctx: commands.Context):
        return ctx.guild is None

    return commands.check(predicate)


def is_owner_or_whitelist():
    """
    Check if the command is called by the owner or by someone in the owner_data whitelist
    :return:
    """

    async def predicate(ctx: commands.Context):
        if await ctx.bot.is_owner(ctx.author) or ctx.author.id in get_owner_data()["special command whitelist"]:
            return True
        return False

    return commands.check(predicate)
