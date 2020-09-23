from bot import StatiCat
from deepfake.deepfake import DeepFake


def setup(bot: StatiCat):
    bot.add_cog(DeepFake(bot))
