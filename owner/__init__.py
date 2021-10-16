from owner.owner import Owner
from nextcord.ext.commands import Bot

def setup(bot: Bot):
    bot.add_cog(Owner(bot))
