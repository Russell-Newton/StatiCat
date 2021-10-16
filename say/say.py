import nextcord
import nextcord.ext.commands as commands

import interactions
from bot import StatiCat
from checks import check_in_guild


class Say(commands.Cog):
    """Makes the bot say stuff"""

    def __init__(self, bot: StatiCat):
        self.bot = bot

    @commands.command()
    async def say(self, ctx, *, message):
        """Make me say something"""
        await ctx.send(message)
        try:
            await ctx.message.delete()
        except nextcord.Forbidden:
            pass

    @commands.command()
    async def speak(self, ctx, *, message):
        """Make me say something, with tts"""
        await ctx.send(message, tts=True)
        try:
            await ctx.message.delete()
        except nextcord.Forbidden:
            pass

    @check_in_guild()
    @commands.command(name="privatemessage", aliases=["pm"])
    async def send_private_message(self, ctx: commands.Context, target: nextcord.Member, *, message):
        try:
            await target.send(message)
            await ctx.message.delete()
        except nextcord.Forbidden:
            pass
        except nextcord.HTTPException:
            await ctx.send("Oops I had some trouble sending that.")

    @interactions.slash_command(name="say")
    async def say_slash(self, interaction: nextcord.Interaction, message, tts: bool = False):
        await interaction.response.send_message("Only you can see this", ephemeral=True)
        channel_id = interaction.channel_id
        if channel_id is not None:
            channel = await self.bot.fetch_channel(channel_id)
            await channel.send(message, tts=tts)
        else:
            await interaction.followup.send(message, tts=tts)


    # @commands.command()
    # async def imitate(self, ctx, user : nextcord.Member, *, message):
    #     channel = ctx.message.channel
    #     botUser = ctx.message.server.me
    #
    #     try:
    #         currentPFPLink = "https://cdn.nextcordapp.com/avatars/" + botUser.id + "/" + botUser.avatar + ".png?size=1024"
    #         currentPFP = requests.get(currentPFPLink).content
    #         currentNick = botUser.display_name
    #
    #         imitationPFPLink = "https://cdn.nextcordapp.com/avatars/" + user.id + "/" + user.avatar + ".png?size=1024"
    #         imitationPFP = requests.get(imitationPFPLink).content
    #         imitationNick = user.display_name
    #
    #         await self.bot.delete_message(ctx.message)
    #
    #         await self.bot.edit_profile(avatar = imitationPFP)
    #         await self.bot.change_nickname(botUser, imitationNick)
    #         await self.bot.send_message(channel, message)
    #
    #         await self.bot.edit_profile(avatar = currentPFP)
    #         await self.bot.change_nickname(botUser, currentNick)
    #     except nextcord.HTTPException:
    #         await self.bot.say("This command is on cooldown I think. It sometimes won't work, which is annoying")
    #
    # @commands.command()
    # @checks.is_owner()
    # async def resetPFP(self, ctx):
    #     author = ctx.message.author
    #     resetPFPLink = "https://cdn.nextcordapp.com/avatars/" + author.id + "/" + author.avatar + ".png?size=1024"
    #     resetPFP = requests.get(resetPFPLink).content
    #     await self.bot.edit_profile(avatar = resetPFP)

