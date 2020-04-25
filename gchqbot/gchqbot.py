import asyncio
import logging
import datetime
import os
from motor import motor_asyncio
from pymongo import errors as pymongoerrors

from logging import handlers

from discord.ext import commands
import discord


class GCHQBot(commands.Bot):
    def __init__(self, command_prefix, base_config_options, captcha_keypair, **options):
        super().__init__(command_prefix, **options)
        self.start_datetime = datetime.datetime.now()
        self.verification_domain = base_config_options["verification_domain"]
        self.recaptcha_keypair = captcha_keypair
        self.config_data = {"base": base_config_options, "captcha": captcha_keypair}
        self.logger = self.__config_logging(
            logging_level=logging.getLevelName(base_config_options["logging_level"].upper()))
        self.logger.info(f"Command prefix: {command_prefix}")
        self.db_client = None
        for extension in base_config_options["extensions"]:
            self.load_extension(extension)

    @staticmethod
    def __config_logging(logging_level=logging.INFO, outdir="./logs"):
        logger = logging.getLogger("GCHQBot")
        logger.setLevel(logging_level)
        formatter = logging.Formatter('[{asctime}] [{levelname:}] {name}: {message}',
                                      '%Y-%m-%d %H:%M:%S', style='{')
        # file_log = handlers.RotatingFileHandler(f'{outdir}/{self.start_datetime.strftime("%Y%m%d_%H%M%S")}.log',
        #                                         encoding="utf-8", mode="a", backupCount=3, maxBytes=10000000)
        console_log = logging.StreamHandler()
        # file_log.setFormatter(formatter)
        console_log.setFormatter(formatter)
        # logger.addHandler(file_log)
        logger.addHandler(console_log)
        logger.debug("Logging configured")
        return logger


if __name__ == "__main__":
    input("This script is not to be called directly, invoke ./run.py instead.\n\nPress any key to exit.")
    exit()
