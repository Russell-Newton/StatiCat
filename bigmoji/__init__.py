from bigmoji.bigmoji import Bigmoji
from bot import StatiCat


def setup(bot: StatiCat):
    bot.add_cog(Bigmoji(bot))
