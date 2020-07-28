from discord.ext.commands import Bot

from wikirun.wikirun import WikiRun

def setup(bot: Bot):
    bot.add_cog(WikiRun(bot))
