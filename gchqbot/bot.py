import asyncio
import logging
import datetime
import os
from motor import motor_asyncio
from pymongo import errors as pymongoerrors

from logging import handlers

from discord.ext import commands
from shutil import copy
from configobj import ConfigObj
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

    def get_cog_config(self, config_name):
        cog_config_loc = f"./extensions/extensions_configs/{config_name}"
        example_cog_config_loc = cog_config_loc + "_example.cfg"
        backup_cog_config_loc = cog_config_loc + "_backup.cfg"
        cog_config_loc += ".cfg"
        example_exists = os.path.exists(example_cog_config_loc)
        main_config_exists = os.path.exists(cog_config_loc)
        if not example_exists and not main_config_exists:
            self.logger.exception(f"{cog_config_loc} does not have a valid example config or in use config.")
            return
        elif example_exists and not main_config_exists:
            self.logger.warning(f"No usable config exists, duplicating example config {cog_config_loc}.")
            copy(example_cog_config_loc, cog_config_loc)
            return
        elif not example_exists and main_config_exists:
            self.logger.warning(f"In use config exists {cog_config_loc} but no example was found, if "
                                f"issues are encountered download an updated example config.")
            copy(cog_config_loc, backup_cog_config_loc)
        return ConfigObj(cog_config_loc)

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
