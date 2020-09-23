from bot import StatiCat
from say.say import Say


def setup(bot: StatiCat):
    bot.add_cog(Say(bot))
