import checks
from bot import StatiCat
import nextcord.ext.commands as commands


class Admin(commands.Cog):
    def __init__(self, bot: StatiCat):
        self.bot: StatiCat = bot


    @checks.check_permissions(["administrator"])
    @checks.check_in_guild()
    @commands.command(name="adminlock")
    async def set_admin_lock(self, ctx: commands.Context):
        """
        Toggles the Admin Lock for this server. When locked, only admins can use commands (text, slash, message, user).
        When unlocked, anyone with the permissions required for a command can use it.
        """
        if "admin_locked_servers" not in self.bot.global_data:
            self.bot.global_data["admin_locked_servers"] = []
        if ctx.guild.id in self.bot.global_data["admin_locked_servers"]:
            self.bot.global_data["admin_locked_servers"].remove(ctx.guild.id)
            await ctx.send("Commands unlocked from just admins.")
        else:
            self.bot.global_data["admin_locked_servers"].append(ctx.guild.id)
            await ctx.send("Commands locked to just admins.")
