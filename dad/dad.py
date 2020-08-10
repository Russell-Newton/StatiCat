import discord
import discord.ext.commands as commands
import requests
from lxml import html
from cogwithdata import CogWithData
from random import randrange

class Dad(CogWithData):
    """Dad-Bot"""

    def __init__(self, bot):
        self.bot = bot
        super().__init__("dad/imdadblacklist.json")

    @commands.command()
    async def dadjoke(self, ctx):
        """
        Go to https://icanhazdadjoke.com/ for more!
        """
        page = requests.get('https://icanhazdadjoke.com/')
        tree = html.fromstring(page.content)
        joke = tree.xpath('/html/body/section/div/div[2]/div/div/p/text()')[0]
        await ctx.send(joke)

    @commands.command(name="stopdad")
    async def blacklist_imdad(self, ctx: commands.Context):
        """
        Disables the funny I'm StatiCat joke for this server.
        """
        if "blacklist" not in self.data:
            self.data["blacklist"] = []
        self.data["blacklist"].append(ctx.guild.id)
        self.update_data_file()
        await ctx.send("No longer responding with the classic joke.")

    @commands.command(name="startdad")
    async def unblacklist_imdad(self, ctx: commands.Context):
        """
        Enables the funny I'm StatiCat joke for this server.
        """
        if "blacklist" not in self.data:
            self.data["blacklist"] = []
        self.data["blacklist"].remove(ctx.guild.id)
        self.update_data_file()
        await ctx.send("Time to become funny.")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.id != self.bot.user.id:
            content: str = message.content
            channel = message.channel
            for word in content.split(" "):
                if word.endswith("er") and 15 <= randrange(0, 200) <= 20:
                    await channel.send("\"{}\"? I hardly even know her!".format(word))
                    return

            if message.guild is not None:
                if message.guild.id in self.data["blacklist"]:
                   return
            if content.lower().startswith("i'm ") or content.lower().startswith(
                    'im ') or content.lower().startswith('i am '):
                nameStart = content.find('m') + 1
                nameEnd = content.find('.')
                if nameEnd > 0:
                    name = content[nameStart:nameEnd]
                else:
                    name = content[nameStart:]
                await channel.send("Hi" + name + "! I'm {}!".format(self.bot.user.name))


def setup(bot):
    n = Dad(bot)
    # bot.add_listener(n.listener, "on_message")
    bot.add_cog(n)
