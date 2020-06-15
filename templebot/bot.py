import asyncio
import logging
import datetime
import os
from motor import motor_asyncio
from pymongo import errors as pymongoerrors

from logging import handlers
from collections import OrderedDict

from discord.ext import commands
from shutil import copy
from configobj import ConfigObj
from datetime import timedelta
import discord


class TempleBot(commands.Bot):
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
    def parse_hms_str_to_timedelta(hms_str: str) -> timedelta:
        # Uses ordereddict to make sure we go in the correct order, divinely inspired
        if hms_str == "-1":
            return timedelta(weeks=10000)
        hms_letter_kwarg_table = OrderedDict([
            ("w", "weeks"),
            ("d", "days"),
            ("h", "hours"),
            ("m", "minutes"),
            ("s", "seconds")
        ])
        dt_kwarg_dict = {}
        for delim, kwarg in hms_letter_kwarg_table.items():
            split_str = hms_str.split(delim)
            if len(split_str) > 2:
                raise commands.BadArgument(f"Improper duration string given, supports up to w (weeks), passed: "
                                           f"{hms_str}")
            hms_str = split_str[-1]
            if len(split_str) != 1:
                # in this case we have a datetime delimiter to worry about
                dt_kwarg_dict[kwarg] = int(split_str[0])
        if dt_kwarg_dict == {}:
            raise commands.BadArgument(f"Improper duration string given, supports up to w (weeks), passed: "
                                       f"{hms_str}")
        return timedelta(**dt_kwarg_dict)

    def get_cog_config(self, config_name):
        cog_config_loc = f"./extensions/extensions_configs/{config_name}"
        config_extension = ".config"
        example_cog_config_loc = cog_config_loc + "_example" + config_extension
        cog_config_loc += config_extension
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
        # if ConfigObj(cog_config_loc)["version"]
        # backup_cog_config_loc = cog_config_loc + "_backup" + config_extension
        # copy(cog_config_loc, backup_cog_config_loc)
        return ConfigObj(cog_config_loc)

    @staticmethod
    def __config_logging(logging_level=logging.INFO, outdir="./logs"):
        logger = logging.getLogger("TempleBot")
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
