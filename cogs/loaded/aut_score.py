import discord
import logging
import re
from discord.ext import commands
from config.config_reader import ConfigReader


class AutScoreCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("GCHQBot.AutScore")
        self.autism_score_format_regex = r"\((\d+|\d\?\d|(\d|\d\.\d+)\²)\/50\)$"
        self.logger.info("Loaded AutScoreCog")

    @commands.Cog.listener()
    async def on_ready(self):
        for member in self.bot.get_guild(CONFIG_VAR.main_guild_id).members:
            await self._test_for_aut_score(member)

    async def _test_for_aut_score(self, member_after, member_before=None):
        aut_blue_role = member_after.guild.get_role(CONFIG_VAR.autism_score_blue_role_id)
        if aut_blue_role is None:
            return
        if member_after.nick is None:
            return
        if member_before is not None:
            # Now we have only got member update events where nicknames have changed. Time to RegEx.
            if re.search(self.autism_score_format_regex, str(member_before.nick)) is not None:
                # Here the user already had an autism score.
                if re.search(self.autism_score_format_regex, str(member_after.nick)) is not None:
                    # This is an instance where the user has not removed or added an autism score.
                    return
                else:
                    # In this case the user has removed their autism score and
                    # will lose their blue role.
                    await member_after.remove_roles(aut_blue_role, reason="Member removed autism score "
                                                                          "from their name.")
            else:
                if re.search(self.autism_score_format_regex, member_after.nick) is not None:
                    # In this case the member has added an autism score to their name so they
                    # will get the role.
                    await member_after.add_roles(aut_blue_role, reason="Member added an autism score "
                                                                       "to their name.")
                    try:
                        await member_after.send('You have been given the "{}" role for adding an '
                                                'autism score to your '
                                                'nickname in GCHQ. This role will be automatically '
                                                'removed if you take '
                                                'your autism score out of your name.'
                                                .format(aut_blue_role.name))
                    except discord.errors.Forbidden:
                        pass
                else:
                    # Here the user didn't have an autism score and hasn't added one either,
                    # nothing needs to be done.
                    return
        elif member_before is None:
            # In this case the function is being run from startup, so we just check for people
            # having autism scores.
            if re.search(self.autism_score_format_regex, str(member_after.nick)) is not None and (
                    aut_blue_role not in member_after.roles):
                await member_after.add_roles(aut_blue_role, reason="Member has autism score in name "
                                                                   "on bot startup.")
                try:
                    await member_after.send('You have been given the "{}" role for adding an autism '
                                            'score to your nickname in GCHQ. This role will be '
                                            'automatically removed if you take your autism score '
                                            'out of your name.'.format(aut_blue_role.name))
                except discord.errors.Forbidden:
                    pass
            elif re.search(self.autism_score_format_regex, str(member_after.nick)) is None and (
                    aut_blue_role in member_after.roles):
                await member_after.remove_roles(aut_blue_role, reason="Member has no autism score in "
                                                                      "name on bot startup.")

    @commands.Cog.listener()
    async def on_member_update(self, member_before, member_after):
        if member_before.nick == member_after.nick:
            return

        await self._test_for_aut_score(member_after, member_before)


def setup(bot):
    global CONFIG_VAR

    CONFIG_VAR = ConfigReader()
    bot.add_cog(AutScoreCog(bot))
