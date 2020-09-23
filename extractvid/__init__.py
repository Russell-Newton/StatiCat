from bot import StatiCat
from extractvid.extractvid import ExtractVid


def setup(bot: StatiCat):
    bot.add_cog(ExtractVid(bot))
