from discord.ext.commands import Bot
from cogs.cogs import Cogs

def setup(bot: Bot):
    bot.add_cog(Cogs(bot))