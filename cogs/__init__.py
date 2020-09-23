from bot import StatiCat
from cogs.cogs import Cogs


def setup(bot: StatiCat):
    bot.add_cog(Cogs(bot))
