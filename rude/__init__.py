from discord.ext.commands import Bot

from rude.rude import Rude


def setup(bot: Bot):
    bot.add_cog(Rude(bot))
