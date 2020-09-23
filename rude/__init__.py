from bot import StatiCat
from rude.rude import Rude


def setup(bot: StatiCat):
    bot.add_cog(Rude(bot))
