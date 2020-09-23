from bot import StatiCat
from wikirun.wikirun import WikiRun

def setup(bot: StatiCat):
    bot.add_cog(WikiRun(bot))
