import nextcord.ext.commands as commands
import wikipedia
from requests.utils import requote_uri

from bot import StatiCat
from cogwithdata import CogWithData


class WikiRun(CogWithData):
    """
    Competitive Wikipedia speedruns!
    Get random start and ending pages for a run as well as the fastest paths between the two!
    """

    def __init__(self, bot: StatiCat):
        self.bot = bot
        super().__init__("stats")

    @commands.group(name="wikirun", aliases=['wrun'], pass_context=True)
    async def runs(self, ctx):
        pass

    @runs.command(name="run", aliases=['randomrun'])
    async def gen_random_run(self, ctx: commands.Context):
        """
        Get the starting and ending points for a run!
        """
        complete = False
        while not complete:
            try:
                pages = wikipedia.random(2)
                pages = [wikipedia.page(page) for page in pages]
                complete = True
            except:
                continue

        await ctx.send("Start at:")
        await ctx.send(pages[0].url)
        await ctx.send("End at:")
        await ctx.send(pages[1].url)

        await ctx.send("The following link can be used to find the shortest paths between the two: ")
        await ctx.send(requote_uri(
            "https://www.sixdegreesofwikipedia.com/?source={0.title}&target={1.title}".format(pages[0], pages[1])))

    @runs.command(name="random")
    async def gen_random_pages(self, ctx: commands.Context, pages_count: int = 1):
        """
        Get random Wikipedia pages!
        pages_count will be automatically bounded between 1 and 10.
        """
        pages_count = max(1, min(pages_count, 10))
        complete = False
        while not complete:
            try:
                pages = wikipedia.random(pages_count)
                if not isinstance(pages, list):
                    pages = [pages]
                pages = [wikipedia.page(page) for page in pages]
                complete = True
            except:
                continue
        for page in pages:
            await ctx.send(page.url)
