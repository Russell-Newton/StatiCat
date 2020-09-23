from bot import StatiCat
from customlistener.customlistener import CustomListener


def setup(bot: StatiCat):
    bot.add_cog(CustomListener(bot))
