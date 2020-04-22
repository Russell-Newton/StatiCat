from general.general import General
import discord.ext.commands as commands

def setup(bot: commands.Bot):
    bot.add_cog(General(bot))