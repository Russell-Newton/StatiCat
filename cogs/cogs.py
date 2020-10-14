import asyncio
import importlib
import itertools
import json
import logging
import sys
from importlib import import_module
from importlib.machinery import ModuleSpec
import traceback

import discord.ext.commands as commands

from bot import Embedinator, StatiCat


class Cogs(commands.Cog):
    def __init__(self, bot: StatiCat):
        """
        Commands for managing cogs.
        """
        self.bot: commands.Bot = bot
        self.embedinator = Embedinator(**{"title": "**Cogs**"})
        self.suppress_confirmation = False

    @commands.is_owner()
    @commands.command()
    async def load(self, ctx: commands.Context, *cog_names):
        """
        Loads a cog.

        Usage: load <cog_name>
        """
        for cog_name in cog_names:
            if self.bot.get_cog(cog_name) is not None:
                await ctx.send(f"Cog {cog_name} is already loaded! Try `{ctx.prefix}reload {cog_name}` instead.")
                return
            try:
                mod: ModuleSpec = import_module(cog_name.lower()).__spec__
                self._cleanup_and_refresh_modules(mod.name)
            except ImportError as e:
                # if e.name.lower() == cog_name.lower():
                #     await ctx.send("No cog of the name '{}' was found.".format(cog_name))
                traceback.print_exception(type(e), e, e.__traceback__)
                logging.exception("Error loading cog.")
                await ctx.send(str(e))
                return

            lib = mod.loader.load_module()
            if not hasattr(lib, "setup"):
                del lib
                await ctx.send(f"Cog '{cog_name}' doesn't have a setup function.")
                return

            try:
                if asyncio.iscoroutinefunction(lib.setup):
                    await lib.setup(self.bot)
                else:
                    lib.setup(self.bot)

                self.add_cog_to_data(cog_name)

                if not self.suppress_confirmation:
                    await ctx.send("Loaded {}!".format(cog_name))
            except Exception as e:
                traceback.print_exception(type(e), e, e.__traceback__)
                logging.exception("Error loading cog.")
                await ctx.send(str(e))

    @commands.is_owner()
    @commands.command()
    async def unload(self, ctx: commands.Context, *cog_names):
        """
        Unloads a cog.

        Usage: unload <cog_name>
        """
        for cog_name in cog_names:
            if self.bot.get_cog(cog_name) is None:
                await ctx.send(f"There isn't a loaded cog named '{cog_name}'.")
                return
            self.bot.remove_cog(cog_name)
            self.remove_cog_from_data(cog_name)

            if not self.suppress_confirmation:
                await ctx.send("Unloaded {}!".format(cog_name))

    @commands.is_owner()
    @commands.command()
    async def reload(self, ctx: commands.Context, *cog_names):
        """
        Reloads a cog.

        Usage: reload <cog_name>
        """
        for cog_name in cog_names:
            if self.bot.get_cog(cog_name) is None:
                await ctx.send(f"There isn't a loaded cog named '{cog_name}'.")
                return
            self.suppress_confirmation = True
            await self.unload(ctx, cog_name)
            await self.load(ctx, cog_name)
            self.suppress_confirmation = False

            await ctx.send("Reloaded {}!".format(cog_name))

    @commands.is_owner()
    @commands.command(name="listcogs", aliases=["lc", "cogslist", "cl"])
    async def list_cogs(self, ctx):
        """
        List all loaded cogs.
        """
        self.embedinator.footer = "Type `{0.prefix}help <cog name>` for more info about a cog.".format(ctx)
        for cog_name in sorted(self.bot.cogs):
            self.embedinator.add_line("{}".format(cog_name))
        for embed in self.embedinator.as_embeds(thumbnail_url=self.bot.user.avatar_url):
            await ctx.send(embed=embed)
        self.embedinator.clear()

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
            data["loaded cogs"] = sorted(data["loaded cogs"])
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
