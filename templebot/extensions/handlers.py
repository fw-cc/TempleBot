from discord.ext import commands

import logging
import traceback
import sys


class HandlersCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # self.config = self.bot.get_cog_config("handlers_cog_config")
        self.logger = logging.getLogger("TempleBot.HandlersCog")

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        silent_exceptions = [
            commands.CommandOnCooldown
        ]
        if type(error) not in silent_exceptions:
            print('Ignoring exception in command {}:'.format(ctx.command), file=sys.stderr)
            traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)
        await ctx.send(f"{error}")


def setup(bot):
    bot.add_cog(HandlersCog(bot))
