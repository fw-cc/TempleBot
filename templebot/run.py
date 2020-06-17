from templebot.bot import TempleBot

import yaml
import os
import shutil


if __name__ == "__main__":
    with open("base_config.yml", "r") as base_config:
        config_values = yaml.safe_load(base_config)
    if not os.path.exists("token.yml"):
        shutil.copyfile("./token.example.yml", "token.yml")
        print("Define token before running")
        exit(-1)
    with open("token.yml", "r") as token_file:
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
