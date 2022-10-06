import logging
from typing import List

import nextcord
from nextcord.ext import application_checks

from bot import bot


def check_permissions(permissions: List[str], check_all: bool = True):
    """
    Checks that a user running the command has at least one of the specified permissions.
    """
    # Check for valid flags
    nextcord.Permissions(**{
        perm: True
        for perm in permissions
    })

    async def predicate(cog, interaction: nextcord.Interaction):
        if not isinstance(interaction.user, nextcord.Member):
            return False
        for perm in permissions:
            has_permission = getattr(interaction.user.guild_permissions, perm)
            if check_all and not has_permission:
                return False
            elif not check_all and has_permission:
                logging.info("Passed check_perms check")
                return True
        if check_all:
            return True
        return False

    return application_checks.check(predicate)


def is_owner_or_whitelist():

    async def predicate(cog, interaction: nextcord.Interaction):
        if await bot.is_owner(interaction.user) or interaction.user.id in bot.global_data["special command whitelist"]:
            return True
        logging.info("Failed the owner or whitelist check!")
        return False

    return application_checks.check(predicate)
