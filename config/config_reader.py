import json
import logging
import shutil
import sys


class ConfigReader:

    def __init__(self):
        logger = logging.getLogger("GCHQBot.config_reader")
        if __name__ == "__main__":
            self.run_root = "./"
        else:
            self.run_root = "./config/"
        try:
            with open(self.run_root+"config.json", "r", encoding="utf-8") as config_fp:
                config_file = json.load(config_fp)
        except FileNotFoundError:
            logger.info("Generating ./config/config.json from default_config.")
            try:
                self.regen_config()
            except FileNotFoundError:
                logger.critical("No ./config/default_config.json file exists.")
                input()
                sys.exit(-1)

        self.b_token = config_file["bot"]["token"]
        self.owner_id = config_file["bot"]["owner_id"]
        self.cmd_prefix = config_file["bot"]["cmd_prefix"]
        self.valid_command_channel_id_list = config_file["bot"]["valid_cmd_channels"]
        self.role_dict = config_file["role_table"]
        self.autism_score_blue_role_id = config_file["misc_ids"]["autism_role_id"]
        self.main_announcement_channel_id = config_file["misc_ids"]["main_announcement_channel_id"]
        self.main_guild_id = config_file["misc_ids"]["main_guild_id"]
        self.pres_elect_gchq_id = config_file["misc_ids"]["pres_elect_id"]
        self.vice_pres_gchq_id = config_file["misc_ids"]["vice_pres_id"]
        self.protected_role_list = config_file["colour_command"]["protected_roles"]
        self.extra_exclusion_colours = config_file["colour_command"]["protected_colours"]
        self.delete_messages_after = config_file["colour_command"]["delete_messages_after"]
        self.exclusion_range = config_file["colour_command"]["exclusion_range"]
        self.blocked_mal_search_results = config_file["blocked_mal_search_results"]
        self.explicit_search_protection_on = config_file["explicit_search_protection"]
        self.weeb_channel_id = config_file["misc_ids"]["weeb_channel_id"]
        self.maymay_channel_id = config_file["misc_ids"]["maymay_channel_id"]

    def refresh_config(self):
        with open("config.json", "r", encoding="utf-8") as config_fp:
            config_file = json.load(config_fp)
        self.b_token = config_file["bot"]["token"]
        self.owner_id = config_file["bot"]["owner_id"]
        self.cmd_prefix = config_file["bot"]["cmd_prefix"]
        self.valid_command_channel_id_list = config_file["bot"]["valid_cmd_channels"]
        self.role_dict = config_file["role_table"]
        self.autism_score_blue_role_id = config_file["misc_ids"]["autism_role_id"]
        self.main_announcement_channel_id = config_file["misc_ids"]["main_announcement_channel_id"]
        self.main_guild_id = config_file["misc_ids"]["main_guild_id"]
        self.pres_elect_gchq_id = config_file["misc_ids"]["pres_elect_id"]
        self.vice_pres_gchq_id = config_file["misc_ids"]["vice_pres_id"]
        self.protected_role_list = config_file["colour_command"]["protected_roles"]
        self.extra_exclusion_colours = config_file["colour_command"]["protected_colours"]
        self.delete_messages_after = config_file["colour_command"]["delete_messages_after"]
        self.exclusion_range = config_file["colour_command"]["exclusion_range"]
        self.blocked_mal_search_results = config_file["blocked_mal_search_results"]
        self.explicit_search_protection_on = config_file["explicit_search_protection"]
        self.weeb_channel_id = config_file["misc_ids"]["weeb_channel_id"]
        self.maymay_channel_id = config_file["misc_ids"]["maymay_channel_id"]

    def regen_config(self):
        shutil.copyfile(self.run_root+"default_config.json", self.run_root+"config.json")
        input("Generated config file in ./config/config.json, edit this before you run the "
              "bot again.")
        sys.exit(0)


if __name__ == "__main__":
    config_reader = ConfigReader()
    for attribute_name, value in config_reader.__dict__.items():
        print(attribute_name, value)
