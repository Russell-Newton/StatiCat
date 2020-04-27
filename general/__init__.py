import discord.ext.commands as commands

from general.general import General


def setup(bot: commands.Bot):
    bot.add_cog(General(bot))
