from fry.fry import Fry
import discord.ext.commands as commands

def setup(bot: commands.Bot):
	bot.add_cog(Fry(bot))