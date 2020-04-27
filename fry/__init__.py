import discord.ext.commands as commands

from fry.fry import Fry


def setup(bot: commands.Bot):
    bot.add_cog(Fry(bot))
