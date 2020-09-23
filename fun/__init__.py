from bot import StatiCat
from fun.fun import Fun


def setup(bot: StatiCat):
    bot.add_cog(Fun(bot))
