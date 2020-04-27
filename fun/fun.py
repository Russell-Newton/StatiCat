# noinspection PyUnresolvedReferences
from random import randint, choice

import discord
import discord.ext.commands as commands

__author__ = "ScarletRav3n"

b = False
nsword = nlove = nsquat = npizza = nbribe = ndad = ncalc = nbutt = ncom = nflirt = nup = 0


class Fun(commands.Cog):
    """fun random commands"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def sword(self, ctx, *, user: discord.Member):
        """Sword Duel!"""
        global nsword
        author = ctx.message.author
        nsword += 1
        if b is True:
            k = "\n*This command has been used " + str(nsword) + " times.*"
        else:
            k = ""
        if user.id == self.bot.user.id:
            await ctx.send("I'm not the fighting kind" + k)
        elif user.nick == "Soham":
            await ctx.send(author.mention + " and " + user.mention + " dueled for " + str(randint(2, 120)) +
                           " gruesome hours! It was a long, heated battle, but " + user.mention +
                           " came out victorious!" + k)
        elif author.nick == "Soham":
            await ctx.send(author.mention + " and " + user.mention + " dueled for " + str(randint(2, 120)) +
                           " gruesome hours! It was a long, heated battle, but " + author.mention +
                           " came out victorious!" + k)
        else:
            await ctx.send(author.mention + " and " + user.mention + " dueled for " + str(randint(2, 120)) +
                           " gruesome hours! It was a long, heated battle, but " +
                           choice([author.mention, user.mention]) + " came out victorious!" + k)

    @commands.command()
    async def love(self, ctx, user: discord.Member):
        """Found your one true love?"""
        global nlove
        author = ctx.message.author
        nlove += 1
        if b is True:
            k = "\n*This command has been used " + str(nlove) + " times.*"
        else:
            k = ""
        if user.id == self.bot.user.id:
            await ctx.send("I am not capable of loving like you can. I'm sorry." + k)
        else:
            await ctx.send(author.mention + " is capable of loving " + user.mention + " a whopping " +
                           str(randint(0, 100)) + "%!" + k)

    @commands.command()
    async def squat(self, ctx):
        """How is your workout going?"""
        global nsquat
        author = ctx.message.author
        nsquat += 1
        if b is True:
            k = "\n*This command has been used " + str(nsquat) + " times.*"
        else:
            k = ""
        await ctx.send(author.mention + " puts on their game face and does " + str(randint(2, 1000)) +
                       " squats in " + str(randint(4, 90)) + " minutes. Wurk it!" + k)

    @commands.command()
    async def pizza(self, ctx):
        """How many slices of pizza have you eaten today?"""
        global npizza
        author = ctx.message.author
        npizza += 1
        if b is True:
            k = "\n*This command has been used " + str(npizza) + " times.*"
        else:
            k = ""
        await ctx.send(author.mention + " has eaten " + str(randint(2, 120)) + " slices of pizza today." + k)

    @commands.command()
    async def bribe(self, ctx):
        """Find out who is paying under the table"""
        global nbribe
        author = ctx.message.author
        nbribe += 1
        if b is True:
            k = "\n*This command has been used " + str(nbribe) + " times.*"
        else:
            k = ""
        await ctx.send(author.mention + " has bribed " + self.bot.user.mention + " with " +
                       str(randint(10, 10000)) + " dollars!" + k)

    @commands.command()
    async def daddy(self, ctx):
        global ndad
        author = ctx.message.author
        ndad += 1
        if b is True:
            k = "\n*This command has been used " + str(ndad) + " times.*"
        else:
            k = ""
        await ctx.send("I'm kink shaming you, " + author.mention + k)

    @commands.command()
    async def calculated(self, ctx):
        global ndad
        ndad += ndad
        if b is True:
            k = "\n*This command has been used " + str(ndad) + " times.*"
        else:
            k = ""
        await ctx.send("That was " + str(randint(0, 100)) + "% calculated!" + k)

    @commands.command()
    async def butts(self, ctx):
        global nbutt
        nbutt += 1
        if b is True:
            k = "\n*This command has been used " + str(nbutt) + " times.*"
        else:
            k = ""
        await ctx.send("ლ(́◉◞౪◟◉‵ლ)" + k)

    @commands.command(name="commands")
    async def _commands(self, ctx):
        global ncom
        ncom += 1
        if b is True:
            k = "\n*This command has been used " + str(ncom) + " times.*"
        else:
            k = ""
        await ctx.send("Don't tell me what to do." + k)

    @commands.command()
    async def flirt(self, ctx):
        global nflirt
        nflirt += 1
        if b is True:
            k = "\n*This command has been used " + str(nflirt) + " times.*"
        else:
            k = ""
        await ctx.send("xoxoxoxoxo ;)) ))) hey b a b e ; ; ;))) ) ;)" + k)

    @commands.command()
    async def updog(self, ctx):
        global nup
        nup += 1
        if b is True:
            k = "\n*This command has been used " + str(nup) + " times.*"
        else:
            k = ""
        await ctx.send("What's updog?" + k)


def setup(bot):
    n = Fun(bot)
    bot.add_cog(n)
