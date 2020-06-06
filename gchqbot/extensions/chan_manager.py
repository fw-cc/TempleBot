import logging
import re

from num2words import num2words
from discord.ext import commands

import os
from configparser import ConfigParser


class ChannelManagerCog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("GCHQBot.ChannelManager")
        # super().__init__("./extensions/extensions_configs/chan_manager_config.ini", self.config_schema)
        self.cog_config = self.bot.get_cog_config("chan_manager_config")
        self.main_guild_id = self.bot.config_data
        if len(self.cog_config["initial-managed-channels"].keys()) == 0:
            self.logger.info("No initial managed channel defined, channel management disabled")
            self.bot.remove_cog("ChannelManagerCog")
        self.managed_channels_dict = self.cog_config["initial-managed-channels"]
        self.managed_category = None
        self.logger.info("Loaded ChannelManagerCog")

    @commands.Cog.listener()
    async def on_ready(self):
        self.managed_channels_dict = {guild_id: [int(channel_id)]
                                      for guild_id, channel_id in self.cog_config["initial-managed-channels"].items()}
        for guild_id, initial_channel_id in self.managed_channels_dict.items():
            voice_channel_obj = self.bot.get_channel(int(initial_channel_id[0]))
            if voice_channel_obj.category is None:
                guild_obj = self.bot.get_guild(int(guild_id))
                if guild_obj is None:
                    self.logger.exception(f"Guild id {guild_id} is invalid.")
                else:
                    managed_voice_cat = await guild_obj.create_category("Managed Voice")
                    await voice_channel_obj.edit(category=managed_voice_cat)
            for voice_channel_obj in self.bot.get_channel(int(initial_channel_id[0])).category.voice_channels:
                if re.search(r"The\s\S+\sCall", voice_channel_obj.name) is not None:
                    if voice_channel_obj.id not in self.managed_channels_dict[guild_id]:
                        self.managed_channels_dict[guild_id].append(voice_channel_obj.id)
            self.managed_category = self.bot.get_channel(self.managed_channels_dict[guild_id][0]).category
        await self.check_managed_channels()

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        try:
            # Filter out deaf/mutes
            if before.channel.id == after.channel.id:
                return
            # Filter out cases where channels of reference are both not under bot management:
            if before.channel.id not in self.managed_channels_dict[str(member.guild.id)] and \
                    after.channel.id not in self.managed_channels_dict[str(member.guild.id)]:
                return
        except AttributeError:
            pass

        if (before is None and after is not None) or (before is not None and after is None) or \
                (before is not None and after is not None):
            work_depth = await self.check_managed_channels(target_guild=member.guild)
            self.logger.debug(f"Completed channel rearrangement for guild: {member.guild} depth: {work_depth}")

    async def check_managed_channels(self, target_guild=None, depth=0):
        if target_guild is None:
            for guild_id in self.managed_channels_dict.keys():
                await self.check_managed_channels(target_guild=self.bot.get_guild(int(guild_id)),
                                                  depth=(depth + 1))
            return

        # Iterate through all managed channels except the persistent base channel,
        # generating a list of up to date voice channel objects under management.
        channel_obj_list = [self.bot.get_channel(channel_id)
                            for channel_id in self.managed_channels_dict[str(target_guild.id)]]
        await channel_obj_list[0].edit(position=0)
        # for channel_id in self.managed_channels_dict[str(target_guild.id)][1:]:
        #     channel_obj = self.bot.get_channel(channel_id)
        #     channel_obj_list.append(channel_obj)
        self.logger.debug(f"{channel_obj_list}")

        # Check to see if a channel in the middle of the list is empty
        for channel_obj in channel_obj_list[1:-1]:
            if not channel_obj.members:
                del self.managed_channels_dict[str(target_guild.id)][channel_obj_list.index(channel_obj)]
                await channel_obj.delete()
                self.logger.debug("Deleted channel")
                # Run this method again to shuffle channels to correct their names
                return await self.check_managed_channels(target_guild=target_guild, depth=(depth + 1))

        # Check if the last channel has users in it
        if channel_obj_list[-1].members:
            # Make sure we aren't about to exceed the maximum number of voice channels
            if len(self.managed_channels_dict[str(target_guild.id)]) > int(self.cog_config["max_managed_channels"]):
                return
            new_channel_position = channel_obj_list[-1].position + 1
            new_channel_obj = await channel_obj_list[-1].clone(
                name="The {} Call".format(
                    num2words(len(self.managed_channels_dict[str(target_guild.id)]) + 1,
                              to='ordinal', lang='en').capitalize()))
            self.managed_channels_dict[str(target_guild.id)].append(new_channel_obj.id)
            await new_channel_obj.edit(position=new_channel_position)
            self.logger.debug("Created channel")
            return await self.check_managed_channels(target_guild=target_guild, depth=(depth + 1))

        # Check to see if each channel's name matches with the pattern, rename if needed
        # also does channel reordering in the same loop, because efficiency.
        channels_reordered = False
        for i in range(len(channel_obj_list[1:])):
            index = i + 1
            current_channel = channel_obj_list[index]
            # Channel names are in the format: "The <ordinal> Channel"
            ordinal_in_chan_name = current_channel.name.split()[1]
            true_channel_ordinal = num2words(index + 1, to="ordinal", lang="en").capitalize()
            if ordinal_in_chan_name.lower() != true_channel_ordinal.lower():
                await current_channel.edit(name=f"The {true_channel_ordinal} Call")
                self.logger.debug("Renamed channel")
            if index + channel_obj_list[0].position != current_channel.position:
                await current_channel.edit(position=(index + channel_obj_list[0].position))
                self.logger.debug("Changed channel position")
                channels_reordered = True
        if channels_reordered:
            return await self.check_managed_channels(target_guild=target_guild, depth=(depth + 1))

        return depth


def setup(bot):
    bot.add_cog(ChannelManagerCog(bot))
