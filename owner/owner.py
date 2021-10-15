import asyncio
import logging
from typing import Optional

import discord
import discord.ext.commands as commands

from bot import StatiCat
from universals import _global_data, save_global_data
from checks import is_owner_or_whitelist


class TestException(Exception):
    pass


class Owner(commands.Cog):
    def __init__(self, bot: StatiCat):
        self.bot = bot

    @is_owner_or_whitelist()
    @commands.command(name="denyodds")
    async def set_deny_odds(self, ctx: commands.Context, odds: Optional[int]):
        """
        Sets the odds to deny a user's command request. Set to 0 to disable. Setting to 1 will require manual change and override.
        """
        if odds is None:
            await ctx.send("The current deny odds is 1:" + str(_global_data["deny odds"]))
            return
        _global_data["deny odds"] = odds
        save_global_data()
        await ctx.send(f"Set the deny odds to 1:{odds}")

    @commands.is_owner()
    @commands.command(name="testthrow")
    async def throw_error(self, ctx: commands.Context):
        raise TestException("This is a test.")

    # @commands.is_owner()
    # @commands.command(name="shutdown")
    async def shutdown_no_restart(self, ctx: commands.Context):
        await ctx.send('Are you sure? React with 👍 to confirm.')

        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=30, check=self.approval_check)
        except asyncio.TimeoutError:
            await ctx.send("Shutdown request cancelled.")
        else:
            await ctx.send("Good night :)")
            logging.warning("Received the instruction to shut down from the owner.")
            await self.bot.close()
            self.bot.loop.stop()

    # @commands.is_owner()
    # @commands.command(name="restart")
    async def shutdown_restart(self, ctx: commands.Context):
        await ctx.send('Are you sure? React with 👍 to confirm.')

        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=30, check=self.approval_check)
        except asyncio.TimeoutError:
            await ctx.send("Restart request cancelled.")
        else:
            await ctx.send("Restarting...")
            logging.warning("Received the instruction to restart from the owner.")
            self.bot.should_restart = True
            await self.bot.close()
            self.bot.loop.stop()

    @commands.is_owner()
    @commands.command(name="attribute", aliases=["getattr", "attr"])
    async def send_attr(self, ctx: commands.Context, attribute: str):
        """
        Sends the bot's attribute specified by the passed parameter.
        """
        await ctx.send(getattr(self.bot, attribute))

    def approval_check(self, reaction: discord.Reaction, user: discord.User):
        return user.id == self.bot.owner_id and str(reaction.emoji) == '👍'
