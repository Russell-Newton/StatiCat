import discord.ext.commands as commands

from deepfake.deepfake import DeepFake


def setup(bot: commands.Bot):
    bot.add_cog(DeepFake(bot))
