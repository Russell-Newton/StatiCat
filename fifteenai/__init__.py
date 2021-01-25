from bot import StatiCat
from fifteenai.fifteenai import FifteenAI

def setup(bot: StatiCat):
    bot.add_cog(FifteenAI(bot))
