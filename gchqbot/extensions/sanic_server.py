from discord.ext import commands

import discord

import logging
import asyncio
from sanic import Sanic, response


class SanicVerificationCog(commands.Cog):
    app = Sanic()
    app.static("/.well-known/acme-challenge/", "/var/www/certbot")

    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("GCHQBot.Sanic")

    @commands.Cog.listener()
    async def on_ready(self):
        ssl_placeholder = {"cert": "", "key": ""}
        await self.app.create_server(port=8000,
                                     ssl=None,
                                     return_asyncio_server=True)


def setup(bot):
    bot.add_cog(SanicVerificationCog(bot))
