from bot import StatiCat
from dad.dad import Dad


def setup(bot: StatiCat):
    bot.add_cog(Dad(bot))
