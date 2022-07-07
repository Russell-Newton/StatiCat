from typing import List

import nextcord

from bot import bot


def check_one(permissions: List[str]):
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
            if has_permission:
                return True
        return False

    def wrapper(app_command: nextcord.BaseApplicationCommand):
        return app_command.add_check(predicate)

    return wrapper


def check_all(permissions: List[str]):
    """
    Checks that a user running the command has all the specified permissions.
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
            if not has_permission:
                return False
        return True

    def wrapper(app_command: nextcord.BaseApplicationCommand):
        return app_command.add_check(predicate)

    return wrapper

def is_owner_or_whitelist():

    async def predicate(cog, interaction: nextcord.Interaction):
        if await bot.is_owner(interaction.user) or interaction.user.id in bot.owner_data["special command whitelist"]:
            return True
        return False

    def wrapper(app_command: nextcord.BaseApplicationCommand):
        return app_command.add_check(predicate)

    return wrapper
