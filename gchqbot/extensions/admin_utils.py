from discord.ext import commands

import logging


class AdminUtils(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("GCHQBot.AdminUtils")

    @commands.command()
    @commands.is_owner()
    async def shutdown(self):
        await self.bot.close()
