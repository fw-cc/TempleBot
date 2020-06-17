from discord.ext import commands
from motor import motor_asyncio
from pymongo import errors as pymongoerrors

import discord

import asyncio
import os
import logging


class DBSetup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("TempleBot.DBSetup")
        self.db_client = None

    @commands.Cog.listener()
    async def on_ready(self):
        await self.__get_db_client(os.getenv("MONGOD_UNAME"), os.getenv("MONGOD_UPASS"))

    async def __get_db_client(self, uname, upass):
        self.logger.debug("Authenticating with mongodb instance")
        mongo_address = "localhost"
        try:
            if uname is not None and upass is not None:
                client_inst = motor_asyncio.AsyncIOMotorClient(
                    ("mongodb://%s:%s@%s:27017/templebot" % (uname, upass, mongo_address)),
                    io_loop=asyncio.get_event_loop())
            else:
                client_inst = motor_asyncio.AsyncIOMotorClient(
                    ("mongodb://%s:27017/templebot" % mongo_address),
                    io_loop=asyncio.get_event_loop())
            self.logger.debug(str(client_inst))
            self.db_client = client_inst
        except pymongoerrors.PyMongoError as error:
            self.logger.exception(f"Exception occurred while attempting to connect to mongodb:\n\n{error}")
            return None


def setup(bot):
    bot.add_cog(DBSetup(bot))
