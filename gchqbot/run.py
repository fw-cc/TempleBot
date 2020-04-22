from gchqbot import GCHQBot
import yaml
import os
import shutil


if __name__ == "__main__":
    with open("./base_config.yml", "r") as base_config:
        config_values = yaml.safe_load(base_config)
    if not os.path.exists("./token.yml:"):
        shutil.copyfile("./token.example.yml", "token.yml")
        print("Define token before running")
        input()
        exit(-1)
    with open("./token.yml", "r") as token_file:
        token = yaml.safe_load(token_file)["token"]
        if token == "your_token_here":
            print("Define token before running")
            input()
            exit(-1)
    bot = GCHQBot(config_values["command_prefix"], base_config_options=config_values)
    bot.run(token)
