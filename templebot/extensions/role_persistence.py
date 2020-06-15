from discord.ext import commands

import logging
import asyncio


class RolePersistence(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_client = None
        self.config = self.bot.get_cog_config("role_persistence_config")
        self.logger = logging.getLogger("TempleBot.RolePersistence")

    @commands.Cog.listener()
    async def on_member_update(self):
        pass

    @commands.Cog.listener()
    async def on_ready(self):
        if self.bot.get_cog("DBSetup").db_client is None:
            await asyncio.sleep(0.25)
        self.db_client = self.bot.get_cog("DBSetup").db_client


def setup(bot):
    bot.add_cog(RolePersistence(bot))
