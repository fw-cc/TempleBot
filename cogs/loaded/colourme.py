import discord
import logging
import asyncio
import math
from discord.ext import commands

from config.config_reader import ConfigReader


class ColourMeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("GCHQBot.colours")
        self.CONFIG_VAR = ConfigReader()
        self.logger.info("Loaded ColourMeCog")

    async def _clean_colour_roles(self, context_guild):
        await asyncio.sleep(0.5)
        for crole in context_guild.roles:
            if "GCHQ[0x" in crole.name:
                if not crole.members:
                    await crole.delete(reason="Automatic custom colour deletion when unused.")
        self.logger.info("Cleaned out empty colour roles")

    @commands.command(name="colourme")
    async def colour_me(self, ctx, colour_hex: str):
        """Gives the command invoker a custom colour role if they satisfy given conditions.
        If colour_hex is given as "remove", the bot will remove the colour role and exit the
        operation.
        """

        # Preprocess the colour
        if colour_hex.lower() == "remove":
            for arole in ctx.author.roles:
                if "GCHQ[0x" in arole.name:
                    await ctx.author.remove_roles(arole, reason="User requested colour role removal.")

            await self._clean_colour_roles(ctx.guild)
            return

        if len(colour_hex) > 6:
            await ctx.send("The colour string requested is invalid.",
                           delete_after=self.CONFIG_VAR.delete_messages_after)
            return
        colour_hex_split = [colour_hex[0:2], colour_hex[2:4], colour_hex[4:6]]
        colour_dec_split = []
        colour_dec = 0
        for colour in colour_hex_split:
            try:
                colour_dec = int(colour, 16)
            except ValueError:
                await ctx.send("Invalid colour input. If you have included #, omit it and try again.")
                return
            if not (0 <= colour_dec <= 255):
                await ctx.message(f"The colour: {colour_hex[0:6]} sits outside of permitted ranges.",
                                  delete_after=self.CONFIG_VAR.delete_messages_after)
                return
            colour_dec_split.append(colour_dec)

        exclusion_cube_origins = []

        # Set up exclusion zones for colours
        for admin_role_name in self.CONFIG_VAR.protected_role_list:
            # Let's first gather all the admin role
            try:
                admin_role = await commands.RoleConverter().convert(ctx, admin_role_name)
                # Now find its colour and add it to the list of exclusion origins
                admin_role_colour = admin_role.colour.to_rgb()
                exclusion_cube_origins.append(list(admin_role_colour))
            except discord.ext.commands.errors.BadArgument:
                self.logger.debug("Admin role defined in config not found in guild.")

        for extra_exclusion_colour in self.CONFIG_VAR.extra_exclusion_colours:
            hex_exclusion_colour_split = [extra_exclusion_colour[0:2],
                                          extra_exclusion_colour[2:4],
                                          extra_exclusion_colour[4:6]]
            exclusion_colour_dec = []
            for colour in hex_exclusion_colour_split:
                exclusion_colour_dec.append(int(colour, 16))
            exclusion_cube_origins.append(exclusion_colour_dec)

        # Now we have all of the required cube origins, time to check our colour against each.
        for cube_center in exclusion_cube_origins:
            in_cube = True
            for i in range(3):
                dim_min_max = [cube_center[i] - self.CONFIG_VAR.exclusion_range,
                               cube_center[i] + self.CONFIG_VAR.exclusion_range]
                if not (dim_min_max[0] < colour_dec_split[i] < dim_min_max[1]):
                    in_cube = False
                    break
            if colour_dec == cube_center:
                in_cube = True
            if in_cube:
                await ctx.send(f"The colour you have selected is too close to that of an admin role or "
                               f"protected colour.\n\nYour colour (decimal): {colour_dec_split} "
                               f"was too close to {cube_center}. \nChange one or more of the "
                               f"components such that they are {math.ceil(self.CONFIG_VAR.exclusion_range / 2)} away "
                               f"from the protected colour.")
                return

        # Not much left to do, only need to create the custom colour role and make sure that it
        # sits below the lowest defined admin role.
        admin_role_obj_list = {}
        for admin_role in self.CONFIG_VAR.protected_role_list:
            try:
                admin_role_object = await commands.RoleConverter().convert(ctx, admin_role)
                admin_role_obj_list[admin_role_object.position] = admin_role_object
            except discord.ext.commands.errors.BadArgument:
                self.logger.debug("Admin role defined in config not found in guild.")

        sorted_admin_list_pos = sorted(admin_role_obj_list)

        # Now we have the sorted list of admin roles, let's query all roles and see if we already have
        # the requested colour created. GCHQBot colour roles have the naming convention:
        # CPS[0x<R><G><B>] in hex.
        try:
            prev_colour = await commands.RoleConverter().convert(ctx, f"GCHQ[0x{colour_hex.upper()}]")
            await prev_colour.edit(position=sorted_admin_list_pos[0])
            await ctx.author.add_roles(prev_colour, reason="Custom colour requested.")
            return
        except commands.BadArgument:
            # The role doesn't already exist, let's pass.
            pass

        # Now to create the role we wanted all along.
        new_colour_role = await ctx.guild.create_role(
            name=f"GCHQ[0x{colour_hex.upper()}]",
            reason="Custom colour role generation by GCHQBot.",
            colour=discord.Colour.from_rgb(r=colour_dec_split[0],
                                           g=colour_dec_split[1],
                                           b=colour_dec_split[2]))

        await new_colour_role.edit(position=sorted_admin_list_pos[0])
        await new_colour_role.edit(position=sorted_admin_list_pos[0])

        for invoker_role in ctx.author.roles:
            if "GCHQ[0x" in invoker_role.name:
                await ctx.author.remove_roles(invoker_role,
                                              reason="Removing old colour role from user.")

        await ctx.author.add_roles(new_colour_role,
                                   reason="Automatic custom colour allocation by request.")

        await self._clean_colour_roles(ctx.guild)


def setup(bot):
    bot.add_cog(ColourMeCog(bot))
