import quart.flask_patch

from flask_wtf import FlaskForm, RecaptchaField
from discord.ext import commands
from quart import Quart, render_template, Response, static
from secure import SecureHeaders

import discord

import logging
import asyncio
import uuid
from datetime import datetime, timedelta
from pymongo import errors as mongoerrs

from typing import Tuple, Optional

from timeit import default_timer as timer

from quart import Quart, Response, abort
from hypercorn import asyncio as asyncio_hypercorn


class WebVerificationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("TempleBot.Verification")
        self.verification_role_hash_table = {}
        self.cached_owner_obj = (None, None)
        self.db_client = None
        self.has_called_webserver = False
        self.captcha_keys = self.bot.recaptcha_keypair

    @commands.command(hidden=True)
    @commands.is_owner()
    async def test_add_member(self, ctx, target: Optional[discord.Member]):
        self.logger.debug("Test member command called")
        if target is None:
            await self.__on_member_join_internal(ctx.author, force_remind=True, force_reverif=True)
        else:
            await self.__on_member_join_internal(target, force_remind=True, force_reverif=True)

    @commands.command(hidden=True, name="bulk_add")
    @commands.is_owner()
    async def bulk_verify_members(self, ctx, remind_existing: Optional[bool]):
        remind_existing = remind_existing if remind_existing is not None else False
        for member in ctx.guild.members:
            await self.__on_member_join_internal(member, force_remind=remind_existing, dont_repat=True)

    @commands.command(hidden=True, name="clean_verif")
    @commands.is_owner()
    @commands.guild_only()
    async def bulk_clean_verification_role(self, ctx):
        verification_role_id = self.verification_role_hash_table[str(ctx.guild.id)]
        verification_role_obj = ctx.guild.get_role(int(verification_role_id))
        db = self.db_client.templebot
        member_collection = db.members
        for member in verification_role_obj.members:
            member_record = await member_collection.find_one(
                {"user_id": member.id, "guild_id": ctx.guild.id})
            if member_record is None:
                await member.remove_roles(verification_role_obj)
                await self.__on_member_join_internal(member, force_remind=True)
            elif not member_record["verified"]:
                await member.remove_roles(verification_role_obj)
                try:
                    await member.send("The verification enforcement service found a mismatch "
                                      "between your discord roles and the verification database, "
                                      "this has been rectified by revoking your verified discord "
                                      "role. Please consult the software operator if this was in "
                                      "error.")
                except discord.Forbidden:
                    pass
                await self.__on_member_join_internal(member, force_remind=True)

    @commands.command(name="verify")
    @commands.dm_only()
    async def user_req_verify(self, ctx, guild_id):
        guild_obj = self.bot.get_guild(int(guild_id))
        if guild_obj is None:
            raise commands.BadArgument("Guild not found, likely the result of improper `guild_id` argument.")
        member_obj = guild_obj.get_member(ctx.author.id)
        if member_obj is None:
            raise commands.BadArgument("You are not a member of the guild supplied.")
        await self.__on_member_join_internal(member_obj, force_remind=True)

    async def __on_member_join_internal(self, member, force_remind=False, force_reverif=False, dont_repat=False):
        if member.bot:
            return
        db = self.db_client.templebot
        member_collection = db.members
        ppmp_notice_collection = db.ppmp_notice
        member_record = await member_collection.find_one(
            {"user_id": member.id, "guild_id": member.guild.id})
        self.logger.debug(f"Member record found: {member_record}")
        remind_verification = True
        member_uuid = None
        if member_record is None:
            member_uuid = uuid.uuid4()
            member_record = {
                "_id": str(member_uuid),
                "user_id": member.id,
                "guild_id": member.guild.id,
                "roles": [],
                "modifiers": {},
                "penal_record": [],
                "verified": False
            }
            await member_collection.insert_one(member_record)
        elif member_record["verified"] is False:
            member_uuid = member_record["_id"]
        elif force_reverif:
            member_uuid = member_record["_id"]
            await member_collection.update_one({"user_id": member.id, "guild_id": member.guild.id},
                                               {"$set": {"verified": False}})
            # member_uuid = new_member_uuid
        else:
            remind_verification = False

        # Attempt to add the new member to the list of users accepting ppmp notices
        try:
            await ppmp_notice_collection.insert_one({
                "_id": member.id,
                "send_notice": True
            })
        except mongoerrs.DuplicateKeyError:
            pass

        if member_uuid is None and member_record["verified"] and not dont_repat:
            await member.send("You have already been verified in this guild")
            return

        try:
            if remind_verification:
                await member.send(f"You are yet to verify on `{member.guild.name}`. To do so, please visit the "
                                  f"following URL: {self.bot.verification_domain}/{member_uuid}")
            elif force_remind:
                await member.send(f"You are yet to verify on `{member.guild.name}`. To do so, please visit the "
                                  f"following URL: {self.bot.verification_domain}/{member_uuid}")
            else:
                if not dont_repat:
                    await self.__repatriate_member(member, member_record)
        except discord.errors.Forbidden:
            pass

    async def __member_verification_flow(self, member_record) -> Tuple[discord.Guild, discord.Member]:
        guild_obj = self.bot.get_guild(member_record["guild_id"])
        role_obj = guild_obj.get_role(self.verification_role_hash_table[str(guild_obj.id)])
        member_obj = guild_obj.get_member(member_record["user_id"])
        await member_obj.add_roles(role_obj, reason="User verified")
        self.logger.debug(f"Verified {member_obj} in {guild_obj}")
        return guild_obj, member_obj

    async def verify_member(self, member_uuid):
        self.logger.info(f"UUID {member_uuid} passed the verification test.")
        member_record = await self.db_client.templebot.members.find_one({"_id": str(member_uuid)})
        guild_obj, member_obj = await self.__member_verification_flow(member_record)
        await self.db_client.templebot.members.update_one(
            {"_id": str(member_uuid)},
            {"$set": {"verified": True}}
        )
        await member_obj.send(f"You have now been verified on `{guild_obj}`.")
        return member_record

    @commands.Cog.listener()
    async def on_member_join(self, member):
        self.logger.info(f"{member} joined the guild: {member.guild}")
        await self.__on_member_join_internal(member)

    async def __repatriate_member(self, member, record):
        """Internal function used to return roles owned by a member before they left the server back to them
        after they rejoin, based on the most recent backup in the Database."""
        self.logger.info(f"Repatriating member {member} on {member.guild}")
        if record["verified"] and "temp_unverif_mute" not in record["modifiers"].keys():
            await self.__member_verification_flow(record)

    @commands.Cog.listener()
    async def on_ready(self):
        if self.bot.get_cog("DBSetup").db_client is None:
            await asyncio.sleep(0.25)
        self.db_client = self.bot.get_cog("DBSetup").db_client

        if not self.has_called_webserver:
            if self.db_client is None:
                await asyncio.sleep(0.25)
            await self.run_server()
            self.has_called_webserver = True

        for verification_role in self.bot.config_data["base"]["verification_role_ids"]:
            guild_id, role_id = verification_role.split(":")
            guild_obj = self.bot.get_guild(int(guild_id))
            if guild_obj is None:
                self.logger.warning(f"Guild id: {guild_id} defined in config not found")
            role_obj = guild_obj.get_role(int(role_id))
            if role_obj is None:
                self.logger.warning(f"Role id: {role_id} defined in config not found")
            self.verification_role_hash_table[guild_id] = int(role_id)

    @commands.group(name="ppmp")
    @commands.cooldown(1, 30, type=commands.BucketType.user)
    async def ppmp_group(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send(f"You need to use a subcommand with this command group.\n\n"
                           f"Use `{self.bot.command_prefix}help ppmp` to see child commands.")

    @ppmp_group.command(name="enable")
    async def ppmp_enable(self, ctx):
        await self.db_client.templebot.ppmp_notice.update_one({"_id": ctx.author.id}, {"$set": {"send_notice": True}})
        await ctx.author.send("You will now receive PPMP notices.")

    @ppmp_group.command(name="disable")
    async def ppmp_disable(self, ctx):
        await self.db_client.templebot.ppmp_notice.update_one({"_id": ctx.author.id}, {"$set": {"send_notice": False}})
        await ctx.author.send("You will not receive PPMP notices.")

    @commands.is_owner()
    @ppmp_group.command(name="send_notice", hidden=True)
    async def send_ppmp_notice(self, ctx, new_policy_url, *, changes=""):
        ppmp_start = timer()
        ppmp_message_string = f"__**PPMP Notice Service Message:**__\n\nTo disable these notices, send " \
                              f"`{self.bot.command_prefix}ppmp disable` in this Direct Message channel.\n\n" \
                              f"The Operator of this Software has made modifications to the Privacy Policy that " \
                              f"require prior notice to be given to Users of the PPMP Notice Service. " \
                              f"A copy of the new Privacy Policy may be found at {new_policy_url}.\n\n"
        if changes != "":
            ppmp_message_string += f"The Operator of this Software has given a list of changes made, please see " \
                                   f"below:\n" \
                                   f"```{changes}```\n\n"

        ppmp_message_string += "In the case these changes are not within the bounds you deem acceptable, please " \
                               "contact the Operator of this Software or revoke consent under Section 2 of the " \
                               "Privacy Policy."

        ppmp_send_to_list = await self.db_client.templebot.ppmp_notice.find({"send_notice": True}).to_list(None)
        for user_db_object in ppmp_send_to_list:
            user_obj = self.bot.get_user(user_db_object["_id"])
            if user_obj is not None:
                try:
                    await user_obj.send(ppmp_message_string)
                except discord.HTTPException:
                    pass

        self.logger.info(f"Sent {len(ppmp_send_to_list)} PPMP notice messages in {(timer() - ppmp_start):.2f}s")

    def __cache_owner_object(self, owner_id):
        cache_datetime, owner_obj = self.cached_owner_obj
        new_cache_datetime = datetime.now()
        requires_refresh = False
        if cache_datetime is None:
            requires_refresh = True
        elif new_cache_datetime - cache_datetime > timedelta(minutes=15):
            requires_refresh = True

        if requires_refresh:
            owner_obj = self.bot.get_user(owner_id)
            self.cached_owner_obj = (new_cache_datetime, owner_obj)

        return owner_obj

    async def run_server(self):
        secure_headers = SecureHeaders()
        app = Quart(__name__)
        db_client = self.db_client
        event_loop = asyncio.get_event_loop()
        config_data = self.bot.config_data
        app.config["SECRET_KEY"] = config_data["base"]["webserver_secret_session_key"]
        app.config["RECAPTCHA_USE_SSL"] = True
        app.config['RECAPTCHA_PUBLIC_KEY'] = config_data["captcha"]["sitekey"]
        app.config['RECAPTCHA_PRIVATE_KEY'] = config_data["captcha"]["privatekey"]
        app.config['RECAPTCHA_DATA_ATTRS'] = {"theme": 'dark'}
        configuration = asyncio_hypercorn.Config().from_mapping({
            "host": self.bot.config_data["base"]["verification_domain"],
            "port": 8000,
            "use_reloader": True,
            "secret_key": config_data["base"]["webserver_secret_session_key"]
        })
        event_loop.create_task(asyncio_hypercorn.serve(app, configuration))

        class VerifyForm(FlaskForm):
            recaptcha = RecaptchaField()

        @app.errorhandler(404)
        async def err_404_handler(error):
            return await render_template("not_found.html")

        @app.route("/privacy", methods=["GET"])
        async def return_privacy_statement():
            """Returns a plain html privacy statement to the end user."""
            owner_id = self.bot.config_data["base"]["owner_id"]
            owner_name_str = str(self.__cache_owner_object(owner_id))
            return await render_template("privacy_statement.html", owner_name=owner_name_str)

        @app.route("/<uuid:verif_id>", methods=["GET", "POST"])
        async def handle_verification(verif_id):
            """Verification page that contains a recaptcha "form" where users must verify their humanity
            in order to gain access to the server.

            Page will 404 with an improper uuid, or a uuid that has already been verified.

            Needs rate limiting to mitigate crash attempts."""
            verif_form = VerifyForm()

            if verif_form.validate_on_submit():
                member_rec_obj = await self.verify_member(str(verif_id))
                ppmp_bool = await db_client.templebot.ppmp_notice.find_one({"_id": member_rec_obj["user_id"]})
                ppmp_str = "<ppmp_status>"
                if ppmp_bool:
                    ppmp_str = "Enabled"
                else:
                    ppmp_str = "Disabled"
                return await render_template("verification_success.html", ppmp_status=ppmp_str)

            if db_client is None:
                return Response("Error occurred while fetching results, try again.", 503)
            members_collection = db_client.templebot.members
            member_record = await members_collection.find_one({"_id": str(verif_id)})
            if member_record is None or member_record["verified"] is True:
                abort(404)

            # Now we have a valid user record, let's use our verification page template to help them verify
            return await render_template("verification.html", form=verif_form, verif_uuid=verif_id)

        @app.after_request
        async def apply_secure_headers(response):
            """Applies security headers"""
            secure_headers.quart(response)
            return response


def setup(bot):
    bot.add_cog(WebVerificationCog(bot))
