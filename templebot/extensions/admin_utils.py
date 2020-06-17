from discord.ext import commands

import discord

from datetime import datetime
from datetime import timedelta

import logging
import asyncio


class AdminUtils(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_client = None
        self.logger = logging.getLogger("TempleBot.AdminUtils")

    @commands.Cog.listener()
    async def on_ready(self):
        if self.bot.get_cog("DBSetup").db_client is None:
            await asyncio.sleep(0.25)
        self.db_client = self.bot.get_cog("DBSetup").db_client

    @commands.command()
    @commands.is_owner()
    async def shutdown(self, ctx):
        await self.bot.close()

    # async def __unverif_internal(self, target: discord.Member, reverif: datetime, reason=""):
    #     pass
    #
    # @commands.command(name="fullmute", hidden=True)
    # async def temp_unverif(self, ctx, target_member: discord.Member, duration: str, *, reason=""):
    #     """Mute a member through temporary (or indefinite) suspension of verification.
    #
    #     target_member must be convertible to discord.Member, i.e. mention, snowflake ID, name#disc etc.
    #     duration must be str type with no spaces, in the form WdXhYmZs for indefinite use -1, 0 will error.
    #     reason must be str type and is a catch all argument, you do not need to include quotes here to help
    #     the parser.
    #
    #     This command protects against users abusing the role repatriation system, as it takes priority."""
    #     if self.db_client is None:
    #         await asyncio.sleep(0.25)
    #
    #     curr_datetime = datetime.utcnow()
    #     reverif_timedelta = self.bot.parse_hms_str_to_timedelta(duration)
    #     self.logger.debug(reverif_timedelta)
    #     reverif_datetime = curr_datetime + reverif_timedelta
    #     self.logger.debug(reverif_datetime)
    #     await self.__unverif_internal(target_member, reverif_datetime, reason)


def setup(bot):
    bot.add_cog(AdminUtils(bot))
