import discord
import discord.ext.commands as commands
import requests
from lxml import html


class Dad(commands.Cog):
    """Dad-Bot"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def dadjoke(self, ctx):
        page = requests.get('https://icanhazdadjoke.com/')
        tree = html.fromstring(page.content)
        joke = tree.xpath('/html/body/section/div/div[2]/div/div/p/text()')[0]
        await ctx.send(joke)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        channel = message.channel
        if message.author.id != self.bot.user.id:
            if message.content.lower().startswith("i'm ") or message.content.lower().startswith(
                    'im ') or message.content.lower().startswith('i am '):
                nameStart = message.content.find('m') + 1
                nameEnd = message.content.find('.')
                if nameEnd > 0:
                    name = message.content[nameStart:nameEnd]
                else:
                    name = message.content[nameStart:]
                await channel.send("Hi" + name + "! I'm {}!".format(self.bot.user.name))


def setup(bot):
    n = Dad(bot)
    # bot.add_listener(n.listener, "on_message")
    bot.add_cog(n)
