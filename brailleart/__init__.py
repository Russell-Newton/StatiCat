from bot import StatiCat
from brailleart.brailleart import BrailleArt


def setup(bot: StatiCat):
    bot.add_cog(BrailleArt(bot))
