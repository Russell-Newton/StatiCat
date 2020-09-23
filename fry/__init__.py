from bot import StatiCat
from fry.fry import Fry


def setup(bot: StatiCat):
    bot.add_cog(Fry(bot))
