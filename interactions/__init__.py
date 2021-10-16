from bot import StatiCat
from interactions.interactions import InteractionHandler, ApplicationCommand, APIRoute
from interactions.slashcommands import slash_command, SlashContext

async def setup(bot: StatiCat):
    from interactions.interactions import Interactions

    instance = Interactions(bot)
    bot.add_cog(instance)
    await instance.add_from_loaded_cogs()

    _previous_add_cog_command = bot.add_cog

    # Rebind the bot's add and remove cog methods to one that will load and unload ApplicationCommands from cogs
    # respectively
    from discord.ext.commands.bot import Bot, BotBase
    from discord.ext.commands import Cog
    def wrapped_add(_bot: Bot):
        def add_cog(cog: Cog):
            # Add the cog normally
            BotBase.add_cog(_bot, cog)
            # Add ApplicationCommands from the Cog when possible
            _bot.loop.create_task(instance.add_from_cog(cog))

        return add_cog

    def wrapped_remove(_bot: Bot):
        def remove_cog(name: str):
            # Remove ApplicationCommands from the Cog when possible
            _bot.loop.create_task(instance.remove_from_cog(_bot.get_cog(name)))
            # Remove the cog normally
            BotBase.remove_cog(_bot, name)

        return remove_cog

    bot.add_cog = wrapped_add(bot)
    bot.remove_cog = wrapped_remove(bot)


async def teardown(bot: StatiCat):
    # This happens before the Interactions cog is removed, undo the rebinding of the bot's add and remove cog methods
    from interactions.interactions import Interactions

    from discord.ext.commands.bot import BotBase
    from discord.ext.commands import Cog
    def wrapped_add(_bot: BotBase):
        def add_cog(cog: Cog):
            # Add the cog normally
            BotBase.add_cog(_bot, cog)

        return add_cog

    def wrapped_remove(_bot: BotBase):
        def remove_cog(name: str):
            # Remove the cog normally
            BotBase.remove_cog(_bot, name)

        return remove_cog

    bot.add_cog = wrapped_add(bot)
    bot.remove_cog = wrapped_remove(bot)