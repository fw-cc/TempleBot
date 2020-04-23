from discord.ext import commands

import discord

import logging


class DBSetup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("GCHQBot.DBSetup")


def setup(bot):
    bot.add_cog(DBSetup(bot))
