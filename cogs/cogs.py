import asyncio
import importlib
import itertools
import json
import sys
from importlib import import_module
from importlib.machinery import ModuleSpec

import discord.ext.commands as commands


class Cogs(commands.Cog):
    def __init__(self, bot: commands.Bot):
        """
        Commands for managing cogs.
        """
        self.bot: commands.Bot = bot

    @commands.is_owner()
    @commands.command()
    async def load(self, ctx: commands.Context, cog_name: str, suppress_end_message: bool = False):
        """
        Loads a cog.

        Usage: load <cog_name>
        """
        if self.bot.get_cog(cog_name) is not None:
            await ctx.send("Cog is already loaded! Try `{}reload {}` instead.".format(ctx.prefix, cog_name))
            return
        try:
            mod: ModuleSpec = import_module(cog_name.lower()).__spec__
            self._cleanup_and_refresh_modules(mod.name)
        except ImportError as e:
            if e.name.lower() == cog_name.lower():
                await ctx.send("No cog of the name '{}' was found.".format(cog_name))
            return

        lib = mod.loader.load_module()
        if not hasattr(lib, "setup"):
            del lib
            await ctx.send("Cog '{}' doesn't have a setup function.".format(cog_name))
            return

        try:
            if asyncio.iscoroutinefunction(lib.setup):
                await lib.setup(self.bot)
            else:
                lib.setup(self.bot)

            self.add_cog_to_data(cog_name)

            if not suppress_end_message:
                await ctx.send("Loaded {}!".format(cog_name))
        except Exception as e:
            await ctx.send(str(e))

    @commands.is_owner()
    @commands.command()
    async def unload(self, ctx: commands.Context, cog_name: str, suppress_end_message: bool = False):
        """
        Unloads a cog.

        Usage: unload <cog_name>
        """
        if self.bot.get_cog(cog_name) is None:
            await ctx.send("There isn't a loaded cog named '{}'.".format(cog_name))
            return
        self.bot.remove_cog(cog_name)
        self.remove_cog_from_data(cog_name)

        if not suppress_end_message:
            await ctx.send("Unloaded {}!".format(cog_name))

    @commands.is_owner()
    @commands.command()
    async def reload(self, ctx: commands.Context, cog_name: str, suppress_end_message: bool = False):
        """
        Reloads a cog.

        Usage: reload <cog_name>
        """
        if self.bot.get_cog(cog_name) is None:
            await ctx.send("There isn't a loaded cog named '{}'.".format(cog_name))
            return
        await self.unload(ctx, cog_name, True)
        await self.load(ctx, cog_name, True)

        if not suppress_end_message:
            await ctx.send("Reloaded {}!".format(cog_name))

    @commands.is_owner()
    @commands.command(name="listcogs", aliases=["lc", "cogslist", "cl"])
    async def list_cogs(self, ctx):
        """
        List all loaded cogs.
        """
        for cog_name in sorted(self.bot.cogs):
            await ctx.send(cog_name)

    @staticmethod
    def remove_cog_from_data(cog_name):
        with open("global_data.json", 'r') as file:
            data = json.load(file)
        with open("global_data.json", 'w') as file:
            data["loaded cogs"].remove(cog_name)
            json.dump(data, file)

    @staticmethod
    def add_cog_to_data(cog_name):
        with open("global_data.json", 'r') as file:
            data = json.load(file)
        with open("global_data.json", 'w') as file:
            data["loaded cogs"].append(cog_name)
            json.dump(data, file)

    @staticmethod
    def _cleanup_and_refresh_modules(module_name: str) -> None:
        """Internally reloads modules so that changes are detected"""
        splitted = module_name.split(".")

        def maybe_reload(new_name):
            try:
                lib = sys.modules[new_name]
            except KeyError:
                pass
            else:
                importlib._bootstrap._exec(lib.__spec__, lib)

        # noinspection PyTypeChecker
        modules = itertools.accumulate(splitted, "{}.{}".format)
        for m in modules:
            maybe_reload(m)

        children = {name: lib for name, lib in sys.modules.items() if name.startswith(module_name)}
        for child_name, lib in children.items():
            importlib._bootstrap._exec(lib.__spec__, lib)
