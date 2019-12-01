import discord
import logging
import asyncio
import re
from num2words import num2words
from discord.ext import commands

from config.config_reader import ConfigReader


class ChannelManagerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("GCHQBot.ChannelManager")
        if CONFIG_VAR.initial_managed_channel == 0:
            self.logger.info("No initial managed channel defined, channel management disabled")
            self.bot.remove_cog("ChannelManagerCog")
        self.managed_channels_list = [CONFIG_VAR.initial_managed_channel]
        self.channel_managed_guild = None
        self.managed_category = None
        self.logger.info("Loaded ChannelManagerCog")

    @commands.Cog.listener()
    async def on_ready(self):
        self.managed_channels_list = [CONFIG_VAR.initial_managed_channel]
        self.channel_managed_guild = self.bot.get_guild(CONFIG_VAR.main_guild_id)
        for voice_channel in self.bot.get_channel(self.managed_channels_list[0]).category.voice_channels:
            if re.search(r"The\s\S+\sCall", voice_channel.name) is not None:
                if not voice_channel.id in self.managed_channels_list:
                    self.managed_channels_list.append(voice_channel.id)
        self.managed_category = self.bot.get_channel(self.managed_channels_list[0]).category
        await self.check_managed_channels()

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        # Filter out deaf/mutes
        if before.channel.id == after.channel.id:
            return
        # Filter out cases where channels of reference are both not under bot management:
        if before.channel.id not in self.managed_channels_list and \
                after.channel.id not in self.managed_channels_list:
            return

        await self.check_managed_channels()

    async def check_managed_channels(self):
        # Iterate through all managed channels except the persistent base channel,
        # generating a list of up to date voice channel objects under management.
        channel_obj_list = [self.bot.get_channel(self.managed_channels_list[0])]
        for channel_id in self.managed_channels_list[1:]:
            channel_obj = self.bot.get_channel(channel_id)
            channel_obj_list.append(channel_obj)

        # Check to see if a channel in the middle of the list is empty
        for channel_obj in channel_obj_list[1:-1]:
            if not channel_obj.members:
                self.logger.debug("Deleted channel")
                del self.managed_channels_list[channel_obj_list.index(channel_obj)]
                await channel_obj.delete(reason="Automatic channel deletion.")
                # Run this method again to shuffle channels to correct their names
                await self.check_managed_channels()
                return

        # Check if the last channel has users in it
        if channel_obj_list[-1].members:
            # Make sure we aren't about to exceed the maximum number of voice channels
            if len(self.managed_channels_list) > CONFIG_VAR.max_managed_channels:
                return
            new_channel_position = channel_obj_list[-1].position + 1
            new_channel_obj = await channel_obj_list[-1].clone(
                name=f"The {num2words(len(self.managed_channels_list), to='ordinal', lang='en').capitalize()} Call",
                reason="Automatic channel creation.")
            self.managed_channels_list.append(new_channel_obj.id)
            await new_channel_obj.edit(position=new_channel_position)
            await self.check_managed_channels()
            return

        # Check to see if each channel's name matches with the pattern, rename if needed
        # also does channel reordering in the same loop, because efficiency.
        for i in range(len(channel_obj_list[1:])):
            index = i + 1
            current_channel = channel_obj_list[index]
            # Channel names are in the format: "The <ordinal> Channel"
            ordinal_in_chan_name = current_channel.name.split()[1]
            true_channel_ordinal = num2words(index + 1, to="ordinal", lang="en").capitalize()
            if ordinal_in_chan_name.lower() != true_channel_ordinal.lower():
                await current_channel.edit(name=f"The {true_channel_ordinal} Call")
            if index + channel_obj_list[0].position != current_channel.position:
                await current_channel.edit(position=(index + channel_obj_list[0].position))
                await self.check_managed_channels()
                return


def setup(bot):
    global CONFIG_VAR

    CONFIG_VAR = ConfigReader()
    bot.add_cog(ChannelManagerCog(bot))
