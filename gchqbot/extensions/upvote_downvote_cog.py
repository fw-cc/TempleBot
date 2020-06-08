from discord.ext import commands

import logging
import re


class UpvoteDownvoteCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = self.bot.get_cog_config("upvote_downvote_cog_config")
        self.vote_prepped_data = None
        self.logger = logging.getLogger("GCHQBot.UpvoteDownvoteCog")

    @commands.Cog.listener()
    async def on_ready(self):
        await self.__re_prep_vote_objects()

    async def __re_prep_vote_objects(self, retried=False):
        self.vote_prepped_data = {}
        try:
            for guild_id, guild_config_data in self.config["vote_configs"].items():
                guild_obj = self.bot.get_guild(int(guild_id))
                if guild_obj is None:
                    self.logger.warning(f"Guild with ID given in config: {guild_id} was not found.")
                else:
                    upvote_obj = self.bot.get_emoji(int(guild_config_data["upvote_emoji_id"]))
                    downvote_obj = self.bot.get_emoji(int(guild_config_data["downvote_emoji_id"]))
                    vote_channel_id = int(guild_config_data["vote_channel_id"])
                    react_filter = guild_config_data["react_only_memes"].lower()
                    self.logger.debug(f"upvote/downvote {guild_obj}, {upvote_obj}, {downvote_obj}, {vote_channel_id}")
                    if None in [upvote_obj, downvote_obj, vote_channel_id, react_filter]:
                        self.logger.warning(f"Invalid configuration for guild id: {guild_id}, {guild_obj}")
                    else:
                        self.vote_prepped_data[str(guild_id)] = {
                            "up": upvote_obj,
                            "down": downvote_obj,
                            "channel_id": vote_channel_id,
                            "filter": react_filter
                        }
            self.logger.debug(f"{self.vote_prepped_data} final data up/downvote")
        except TypeError:
            self.logger.exception("Cog load failed due to improper configuration")
            if not retried:
                await self.__re_prep_vote_objects(retried=True)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        if str(message.guild.id) not in self.vote_prepped_data.keys():
            return
        if message.channel.id == self.vote_prepped_data[str(message.guild.id)]["channel_id"]:
            guild_config_data = self.vote_prepped_data[str(message.guild.id)]
            await self.apply_votes(message, guild_config_data["filter"], guild_config_data["up"],
                                   guild_config_data["down"])

    async def apply_votes(self, message, meme_filter, upvote, downvote):
        self.logger.debug(f"{message} {meme_filter}")
        if meme_filter == "true" and not self.__is_meme_message(message):
            return
        await message.add_reaction(upvote)
        await message.add_reaction(downvote)

    @staticmethod
    def __is_meme_message(message):
        url_regex = r"https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}" \
                    r"\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)"
        return True if (message.attachments or message.embeds or
                        re.search(url_regex, message.content) is not None) else False


def setup(bot):
    bot.add_cog(UpvoteDownvoteCog(bot))
