from discord.ext import commands

import logging


class ElectionCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = self.bot.get_cog_config("election_cog_config")
        self.logger = logging.getLogger("TempleBot.ElectionCog")


def setup(bot):
    bot.add_cog(ElectionCog(bot))
