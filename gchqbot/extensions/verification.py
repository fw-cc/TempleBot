import quart.flask_patch

from flask_wtf import FlaskForm, RecaptchaField
from discord.ext import commands
from quart import Quart, render_template, Response, static
from secure import SecureHeaders

import discord

import logging
import asyncio
import uuid

from quart import Quart, Response, abort
from hypercorn import asyncio as asyncio_hypercorn, middleware as middleware_hypercorn


class WebVerificationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("GCHQBot.Verification")
        self.db_client = None
        self.has_called_webserver = False
        self.captcha_keys = self.bot.recaptcha_keypair

    @commands.command()
    @commands.is_owner()
    async def test_add_member(self, ctx):
        self.logger.debug("Test member command called")
        await self.__on_member_join_internal(ctx.author, force_remind=True, force_reverif=True)

    async def __on_member_join_internal(self, member, force_remind=False, force_reverif=False):
        db = self.db_client.gchqbot
        collection = db.members
        member_record = await collection.find_one(
            {"user_id": member.id, "guild_id": member.guild.id})
        self.logger.debug(f"Member record found: {member_record}")
        remind_verification = True
        member_uuid = None
        if member_record is None:
            member_uuid = uuid.uuid4()
            member_record = {
                "uuid": str(member_uuid),
                "user_id": member.id,
                "guild_id": member.guild.id,
                "roles": [],
                "verified": False
            }
            await collection.insert_one(member_record)
        elif member_record["verified"] is False:
            member_uuid = member_record["uuid"]
        else:
            remind_verification = False

        if remind_verification or force_remind:
            await member.send(f"You are yet to verify on {member.guild.name}. To do so, please visit the "
                              f"following URL: {self.bot.verification_domain}/{member_uuid}")
        elif force_reverif:
            await collection.update_one({"uuid": str(member_uuid)}, {"$set": {"verified": False}})
        else:
            await self.__repatriate_member(member, member_record)

    async def verify_member(self, member_uuid):
        self.logger.info(f"UUID {member_uuid} passed the verification test.")
        await self.db_client.gchqbot.members.update_one(
            {"uuid": str(member_uuid)},
            {"$set": {"verified": True}}
        )

    @commands.Cog.listener()
    async def on_member_join(self, member):
        self.logger.info(f"{member} joined the guild: {member.guild}")
        await self.__on_member_join_internal(member)

    async def __repatriate_member(self, member, record):
        """Internal function used to return roles owned by a member before they left the server back to them
        after they rejoin, based on the most recent backup in the Database."""
        self.logger.info(f"Repatriating member {member} on {member.guild}")

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

    async def run_server(self):
        secure_headers = SecureHeaders()
        # redir_obj = middleware_hypercorn.HTTPToHTTPSRedirectMiddleware(Quart(__name__), "localhost:8000")
        # app = redir_obj.app
        app = Quart(__name__)
        db_client = self.db_client
        event_loop = asyncio.get_event_loop()
        config_data = self.bot.config_data
        # if self.bot.config_data["base"]["verification_domain"] != "":
        #     app.config["SERVER_NAME"] = self.bot.config_data["base"]["verification_domain"]
        #     app.config["SUBDOMAIN"] = self.bot.config_data["base"]["verification_subdomain"]
        app.config["SECRET_KEY"] = config_data["base"]["webserver_secret_session_key"]
        app.config["RECAPTCHA_USE_SSL"] = True
        app.config['RECAPTCHA_PUBLIC_KEY'] = config_data["captcha"]["sitekey"]
        app.config['RECAPTCHA_PRIVATE_KEY'] = config_data["captcha"]["privatekey"]
        app.config['RECAPTCHA_DATA_ATTRS'] = {"theme": 'dark'}
        configuration = asyncio_hypercorn.Config().from_mapping({
            "host": self.bot.config_data["base"]["verification_domain"],
            "port": 8000,
            # "subdomain": self.bot.config_data["base"]["verification_subdomain"],
            # "insecure_bind": "localhost:80",
            # "certfile": "./cert.pem",
            # "keyfile": "./key.pem",
            "use_reloader": True,
            "secret_key": config_data["base"]["webserver_secret_session_key"]
        })
        # event_loop.create_task(asyncio_hypercorn.serve(redir_obj, configuration))
        event_loop.create_task(asyncio_hypercorn.serve(app, configuration))

        class VerifyForm(FlaskForm):
            recaptcha = RecaptchaField()

        @app.errorhandler(404)
        async def err_404_handler(error):
            return await render_template("not_found.html")

        @app.route("/<uuid:verif_id>", methods=["GET", "POST"])
        async def handle_verification(verif_id):
            """Verification page that contains a recaptcha "form" where users must verify their humanity
            in order to gain access to the server.

            Page will 404 with an improper uuid, or a uuid that has already been verified.

            Needs rate limiting to mitigate crash attempts."""
            verif_form = VerifyForm()

            if verif_form.validate_on_submit():
                await self.verify_member(str(verif_id))
                return await render_template("verification_success.html")

            if db_client is None:
                return Response("Error occurred while fetching results, try again.", 503)
            members_collection = db_client.gchqbot.members
            member_record = await members_collection.find_one({"uuid": str(verif_id)})
            if member_record is None or member_record["verified"] is True:
                abort(404)

            # Now we have a valid user record, let's use our verification page template to help them verify
            return await render_template("verification.html", form=verif_form, verif_uuid=verif_id)

        @app.route("/.well-known/acme-challenge/<string:file_name>")
        async def acme_challenge_route(file_name):
            """Used for SSL challenge"""
            web_root = self.bot.config_data["base"]["webroot_path"]+".well-known/acme-challenge/"
            # challenge_route = static.safe_join(web_root, file_name)
            return await static.send_from_directory(web_root, file_name)

        @app.after_request
        async def apply_secure_headers(response):
            """Applies security headers"""
            secure_headers.quart(response)
            return response


def setup(bot):
    bot.add_cog(WebVerificationCog(bot))
