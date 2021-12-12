from admin.admin import Admin
from bot import StatiCat

def setup(bot: StatiCat):
    bot.add_cog(Admin(bot))