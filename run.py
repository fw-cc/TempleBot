from templebot.bot import TempleBot

import yaml
import os
import shutil


if __name__ == "__main__":
    if not os.path.exists("./templebot/base_config.yml"):
        shutil.copyfile("./templebot/base_config.example.yml", "./templebot/base_config.yml")
        print("Define base config options")
    else:
        with open("./templebot/base_config.yml", "r") as base_config:
            config_values = yaml.safe_load(base_config)
    if not os.path.exists("./templebot/token.yml"):
        shutil.copyfile("./templebot/token.example.yml", "./templebot/token.yml")
        print("Define token before running")
        exit(-1)
    with open("./templebot/token.yml", "r") as token_file:
        loaded_tokenfile = yaml.safe_load(token_file)
        token = loaded_tokenfile["token"]
        if token == "":
            print("Define token before running")
            exit(-1)
        captcha_pair = loaded_tokenfile["recaptchakeypair"]
        if captcha_pair == {} or captcha_pair is None or captcha_pair["sitekey"] == "" or \
                captcha_pair["privatekey"] == "":
            print("Define captcha keypair before running")
            exit(-1)
    bot = TempleBot(config_values["command_prefix"],
                    base_config_options=config_values,
                    captcha_keypair=captcha_pair)
    bot.run(token)
