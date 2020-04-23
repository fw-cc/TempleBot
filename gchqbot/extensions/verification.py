from discord.ext import commands
from quart import Quart, render_template, Response

import discord

import logging
import asyncio
import os
import uuid


class WebVerificationCog(commands.Cog):
    app = Quart(__name__)

    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("GCHQBot.Sanic")
        self.db_client = self.bot.db_client
        self.captcha_keys = self.bot.recaptcha_keypair

    @app.route("/<uuid:verif_id>")
    async def handle_verification(self, verif_id):
        member_record = self.db_client["gchqbot"].find_one({"uuid": verif_id})
        if member_record is None:
            return Response("Page Not Found", 404)
        else:
            return Response("Success", 200)

    @commands.command()
    async def test_add_member(self, ctx):
        self.logger.debug("Test member command called")
        await self.on_member_join(ctx.member)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        self.logger.info(f"{member} joined the guild: {member.guild}")
        member_record = self.db_client["gchqbot"].find_one({"user_id": member.id, "guild_id": member.guild.id})
        remind_verification = True
        member_uuid = None
        if member_record is None:
            member_uuid = uuid.uuid4()
            member_record = {
                "uuid": member_uuid,
                "user_id": member.id,
                "guild_id": member.guild.id,
                "roles": [],
                "verified": False
            }
            self.db_client["gchqbot"].insert_one(member_record)
        elif member_record.verified is False:
            member_uuid = member_record.uuid
        else:
            remind_verification = False

        if remind_verification:
            await member.message(f"You are yet to verify on {member.guild.name}. To do so, please visit the "
                                 f"following URL: {self.bot.verification_domain}/{member_uuid}")

    async def __repatriate_member(self, member, record):
        """Internal function used to return roles owned by a member before they left the server back to them
        after they rejoin, based on the most recent backup in the Database."""
        pass

    @commands.Cog.listener()
    async def on_ready(self):
        ssl_placeholder = {"cert": "", "key": ""}
        await self.app.run_task(host="0.0.0.0", port=5000)


def setup(bot):
    bot.add_cog(WebVerificationCog(bot))
