import logging

import discord
import discord.ext.commands as commands

from bot import StatiCat


class TestException(Exception):
    pass


class Owner(commands.Cog):
    def __init__(self, bot: StatiCat):
        self.bot = bot

    @commands.is_owner()
    @commands.command(name="testthrow")
    async def throw_error(self, ctx: commands.Context):
        raise TestException("This is a test.")

    @commands.is_owner()
    @commands.command(name="shutdown")
    async def shutdown_no_restart(self, ctx: commands.Context):
        await ctx.send("Good night :)")
        logging.warning("Received the instruction to shut down from the owner.")
        self.bot.loop.stop()

    @commands.is_owner()
    @commands.command(name="restart")
    async def shutdown_restart(self, ctx: commands.Context):
        await ctx.send("Restarting...")
        logging.warning("Received the instruction to restart from the owner.")
        self.bot.should_restart = True
        self.bot.loop.stop()
