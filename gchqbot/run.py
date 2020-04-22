from gchqbot import GCHQBot
import yaml
import time
import os


if __name__ == "__main__":
    with open("./base_config.yml", "r") as base_config:
        config_values = yaml.load(base_config)
    with open("./token.yml", "r") as token_file:
        token = yaml.load(token_file)["token"]
        if token == "your_token_here":
            print("Define token before running")
            input()
            exit(-1)
    bot = GCHQBot(config_values["command_prefix"], base_config_options=config_values)
    bot.login(token)
