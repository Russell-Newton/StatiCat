import nextcord.ext.commands as commands

from bot import StatiCat
from general.general import General


def setup(bot: StatiCat):
    bot.add_cog(General(bot))
