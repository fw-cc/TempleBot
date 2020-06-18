from discord.ext import commands
from jikanpy import AioJikan

import pytz
import discord
import aiohttp
import jikanpy

from datetime import datetime

import logging
import asyncio
import random
import os
import re


async def _clean_temp_files():
    for name in os.listdir("./"):
        if name.startswith("tempfile"):
            os.remove(f"./{name}")


class WeebCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("TempleBot.weeb")
        self.british_timezone = pytz.timezone('Europe/London')
        self.logger.info("Opening MAL API event loop.")
        self.jikan_aio = AioJikan()
        self.cog_config = self.bot.get_cog_config("anime_manga_search_config")
        self.message_reaction_waiting_h_table = {}
        self.current_mal_req_count_ps = 0
        self.current_mal_req_count_pm = 0
        # self.logger.info("Loaded WeebCog")

    @commands.command(name="weeb_search", hidden=True)
    async def weeb_search_command(self, ctx):
        ctx.message.content = ctx.message.content.strip(self.bot.command_prefix).strip("weeb_search ")
        try:
            await self.anime_title_request_func(ctx.message, ctx.message)
        except jikanpy.exceptions.APIException:
            self.logger.exception("jikanpy.exceptions.APIException raised, attempting API "
                                  "restart.")
            await self.jikan_aio.close()
            self.jikan_aio = AioJikan()
            await self.anime_title_request_func(ctx.message, ctx.message)
        asyncio.create_task(self.mal_rate_limit_down_counter())

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        elif message.guild is None:
            return
        elif str(message.guild.id) not in self.cog_config["anime_manga_channel_id"].keys():
            return None
        elif str(message.channel.id) in self.cog_config["anime_manga_channel_id"][str(message.guild.id)]:
            search_regex = r"(^{.+}$|^\[.+\]$)"
            self.logger.debug(f"{message.content}")
            if re.search(search_regex, message.content) is not None:
                # We now have a totally valid query of either anime or manga, so it's going to be
                # repackaged and allowed to invoke the search function.
                message.content = self.bot.command_prefix + "weeb_search " + message.content
                self.logger.debug(f"{message.content}")
                await self.bot.process_commands(message)

    def cog_unload(self):
        asyncio.run(self.jikan_aio.close())

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, raw_reaction_event):
        try:
            if raw_reaction_event.member.bot:
                return
        except AttributeError:
            pass

        message_id_in_use = None
        for waiting_message in self.message_reaction_waiting_h_table.values():
            if raw_reaction_event.message_id == waiting_message["msg_id"]:
                message_id_in_use = waiting_message

        if message_id_in_use is None:
            return

        allowed_emoji = ["0⃣", "1⃣", "2⃣", "3⃣", "4⃣", "5⃣", "🇽"]

        if raw_reaction_event.emoji.name not in allowed_emoji:
            return

        reverse_word_to_numeral_hash_table = {"0⃣": 0, "1⃣": 1, "2⃣": 2, "3⃣": 3, "4⃣": 4, "5⃣": 5, "🇽": 999}

        if self.message_reaction_waiting_h_table[message_id_in_use["msg_rand_id"]]["user_id"] != \
                raw_reaction_event.user_id:
            return

        self.message_reaction_waiting_h_table[message_id_in_use["msg_rand_id"]]["user_reaction"] = \
            reverse_word_to_numeral_hash_table[raw_reaction_event.emoji.name]
        self.message_reaction_waiting_h_table[message_id_in_use["msg_rand_id"]]["user_reacted"] = True

    async def mal_rate_limit_down_counter(self):
        await asyncio.sleep(2)
        self.current_mal_req_count_ps -= 1
        self.logger.debug("Reduced per second count.")
        await asyncio.sleep(58)
        self.current_mal_req_count_pm -= 1
        self.logger.debug("Reduced per minute count.")

    async def anime_title_request_func(self, message_class, initial_command):

        def m_a_type(msg_object):
            if msg_object.content.startswith("["):
                return "manga"
            elif msg_object.content.startswith("{"):
                return "anime"
            else:
                return None

        req_type = m_a_type(message_class)
        query_term = message_class.content.strip("{}[]")

        weeb_shit_channel = message_class.channel
        self.logger.debug(query_term)

        paused = True
        while paused:
            if self.current_mal_req_count_pm >= 30:
                await asyncio.sleep(self.current_mal_req_count_pm - 30)
            elif self.current_mal_req_count_ps >= 2:
                await asyncio.sleep(1)
            else:
                paused = False

        self.current_mal_req_count_pm += 1
        self.current_mal_req_count_ps += 1

        self.logger.debug("Making API request.")
        r_obj_raw = await self.jikan_aio.search(search_type=req_type, query=query_term)
        self.logger.debug("API Request complete.")

        # PLACEHOLDER FOR BETTER RESULT OPTIONS
        w_to_n_h_tab = {0: "zero", 1: "one", 2: "two", 3: "three", 4: "four", 5: "five"}
        item_selection_embed = discord.Embed(title=f"TempleBot {m_a_type(message_class).capitalize()} Selection.")
        options_list_string = ""
        number_to_title = {}

        if len(r_obj_raw["results"]) == 0:
            await weeb_shit_channel.send("No results found")
            self.logger.debug(f"{r_obj_raw}")
            return

        try:
            for i in range(5):
                options_list_string += f":{w_to_n_h_tab[i]}: - {r_obj_raw['results'][i]['title']}\n"
        except Exception:
            pass

        options_list_string += f":regional_indicator_x: - None of the above"
        item_selection_embed.add_field(name="Are any of these correct?",
                                       value=options_list_string)

        initial_option_message = await weeb_shit_channel.send(embed=item_selection_embed)

        msg_rand_id = random.randint(0, 100000)
        while msg_rand_id in self.message_reaction_waiting_h_table.keys():
            msg_rand_id = random.randint(0, 100000)
        self.message_reaction_waiting_h_table[msg_rand_id] = {"number_to_title": number_to_title,
                                                              "msg_id": initial_option_message.id,
                                                              "msg_rand_id": msg_rand_id,
                                                              "user_reacted": False,
                                                              "user_reaction": 0,
                                                              "user_id": message_class.author.id}
        unicode_emote_hash_table = {":zero:": "0⃣", ":one:": "1⃣", ":two:": "2⃣",
                                    ":three:": "3⃣", ":four:": "4⃣", "five": "5⃣"}
        try:
            for i in range(5):
                emoji_name = f":{w_to_n_h_tab[i]}:"
                number_to_title[f"{emoji_name}"] = r_obj_raw['results'][i]
        except Exception:
            pass

        self.logger.debug(f"{number_to_title}")
        early_reacted = False
        for emote in number_to_title.keys():
            if self.message_reaction_waiting_h_table[msg_rand_id]["user_reacted"]:
                early_reacted = True
                break
            await initial_option_message.add_reaction(unicode_emote_hash_table[emote])
        if not early_reacted:
            await initial_option_message.add_reaction("\N{Regional Indicator Symbol Letter X}")

        loop_sleep_time_s = 0.05
        max_loop_runtime_s = 30
        loop_runtime_s = 0
        while not self.message_reaction_waiting_h_table[msg_rand_id]["user_reacted"]:
            await asyncio.sleep(loop_sleep_time_s)
            loop_runtime_s += loop_sleep_time_s
            if loop_runtime_s >= max_loop_runtime_s:
                await initial_option_message.delete()
                return

        if self.message_reaction_waiting_h_table[msg_rand_id]["user_reaction"] == 999:
            await initial_option_message.delete()
            return

        r_obj = r_obj_raw['results'][self.message_reaction_waiting_h_table[msg_rand_id]["user_reaction"]]
        # if r_obj['title'] in CONFIG_VAR.blocked_mal_search_results or (
        #         r_obj["rated"].lower() == 'rx' and CONFIG_VAR.explicit_search_protection_on):
        #     await initial_option_message.delete()
        #     await initial_command.delete()
        #     return

        prepro_img_url = r_obj['image_url'].rsplit("?", 1)[0].rsplit(".", 1)
        new_img_url = prepro_img_url[0] + "l." + prepro_img_url[1]

        async with aiohttp.ClientSession() as session:
            async with session.get(new_img_url) as target_image_res:
                if target_image_res.status == 200:
                    found_image = True
                else:
                    found_image = False
                colour_dec_split = [38, 66, 133]

        item_embed = discord.Embed(title=(r_obj['title'] + " [" + r_obj['type'] + "]"), url=r_obj['url'],
                                   timestamp=discord.Embed.Empty,
                                   colour=discord.Colour.from_rgb(r=colour_dec_split[0],
                                                                  g=colour_dec_split[1],
                                                                  b=colour_dec_split[2]))

        if req_type == "anime":
            new_media_obj = await self.jikan_aio.anime(r_obj["mal_id"])
        else:
            new_media_obj = await self.jikan_aio.manga(r_obj["mal_id"])

        self.british_timezone = pytz.timezone('Europe/London')
        now = datetime.now(self.british_timezone)

        def date_ordinal_letter(day_num: int) -> str:
            if 4 <= day_num <= 20 or 24 <= day_num <= 30:
                return "th"
            else:
                return ["st", "nd", "rd"][int(str(day_num)[-1]) - 1]

        brit_day_in = now.strftime('%d').lstrip("0")
        now_brit_day = brit_day_in + date_ordinal_letter(int(brit_day_in))
        now_brit = now.strftime(f'%a %b {now_brit_day}, %Y at %H:%M:%S')

        """
        embed_pregen_dict = {
            "title": r_obj['title']+" ["+r_obj['type']+"]",
            "url": r_obj['url'],
            "type": "rich",
            "timestamp": discord.Embed.Empty,
            "color": int(colour_dec_concat),
            "description": discord.Embed.Empty,
            "footer": {
                "text": f"Data scraped with JikanPy | {now_brit} {now.tzname()}",
                "icon_url": "https://i.imgur.com/fSPtnoP.png"
            },
            "image": {},
            "video": {},
            "provider": {}
        }"""

        def id_letter(req_form):
            if req_form == "anime":
                return "a"

            return "m"

        if r_obj["synopsis"] == "":
            r_obj["synopsis"] = f"No synopsis information has been added to this title. " \
                                f"Help improve the MAL database by adding a synopsis " \
                                f"[here](https://myanimelist.net/dbchanges.php?{id_letter(req_type)}" \
                                f"id={r_obj['mal_id']}&t=synopsis)."

        # test_from_dict_embed = discord.Embed.from_dict(embed_pregen_dict)
        # test_from_dict_embed.set_author(name="Pytato/GCHQBot",
        #                                 icon_url="https://i.imgur.com/5zaQwWr.jpg",
        #                                 url="https://github.com/Pytato/GCHQBot")
        # test_from_dict_embed.add_field(name="Synopsis:", value=r_obj['synopsis'], inline=False)
        # test_from_dict_embed.set_thumbnail(url=new_img_url)

        item_embed.set_footer(text=f"Data scraped with JikanPy | {now_brit} {now.tzname()}",
                              icon_url="https://i.imgur.com/fSPtnoP.png")
        item_embed.set_author(name="Pytato/TempleBot", icon_url="https://lithi.io/file/XVKH.png",
                              url="https://github.com/Pytato/TempleBot")
        if found_image:
            item_embed.set_thumbnail(url=new_img_url)

        char_limit = 300
        if len(r_obj["synopsis"]) > char_limit:
            if r_obj["synopsis"][char_limit - 1] == ".":
                r_obj["synopsis"] = r_obj["synopsis"][:(char_limit - 2)].rstrip(" ") + "..."
            r_obj["synopsis"] = r_obj["synopsis"][:(char_limit - 1)].rstrip(" ") + "..."

        item_embed.add_field(name="Synopsis:", value=r_obj['synopsis'], inline=False)

        date_format = "%Y-%m-%d"
        now = datetime.now()

        start_obj = None

        try:
            if r_obj['end_date'] is None:
                end = "?"
            else:
                end = r_obj['end_date'].split("T")[0]
        except KeyError:
            end = "?"
        try:
            if r_obj['start_date'] is None:
                start = "?"
            else:
                start = r_obj['start_date'].split("T")[0]
                start_obj = datetime.strptime(start, date_format)
        except KeyError:
            start = "?"

        rating_hash_table = {
            "G - All Ages": "G",
            "PG - Children": "PG",
            "PG-13 - Teens 13 or older": "PG-13",
            "R - 17+ (violence & profanity)": "R",
            "R+ - Mild Nudity": "R+",
            "Rx - Hentai": "Rx",
            "No Rating": "No Rating"
        }
        try:
            rating = rating_hash_table[r_obj['rated']]
        except KeyError:
            rating = "No Rating"

        if req_type == "anime":
            if r_obj['episodes'] == 0:
                r_obj['episodes'] = "?"

            if r_obj['airing']:
                release_status = "Airing"
                if start_obj > now and start != "?":
                    release_status = "Not Yet Airing"
            else:
                release_status = "Finished"
                if start == "?" or start_obj > now:
                    release_status = "Not Yet Airing"

            item_embed.add_field(name="Airing Details:",
                                 value=f"From: {start}\n"
                                       f"To: {end}\n"
                                       f"Status: {release_status}\n"
                                       f"Episode Count: {r_obj['episodes']}", inline=True)
            try:
                item_embed.add_field(name="Other Details:",
                                     value=f"Score: {r_obj['score']}\n"
                                           f"Age Rating: {rating}\n"
                                           f"Studio: {new_media_obj['studios'][0]['name']}\n"
                                           f"Members: " + "{:,}".format(r_obj['members']),
                                     inline=True)
            except IndexError:
                item_embed.add_field(name="Other Details:",
                                     value=f"Score: {r_obj['score']}\n"
                                           f"Age Rating: {rating}\n"
                                           f"Studio: Not Yet Defined\n"
                                           f"Members: " + "{:,}".format(r_obj['members']),
                                     inline=True)

        else:
            if r_obj['volumes'] == 0:
                r_obj['volumes'] = "?"

            if r_obj['publishing']:
                release_status = "Publishing"
                if start_obj > now and start != "?":
                    release_status = "Not Yet Publishing"
            else:
                release_status = "Finished"
                if start == "?" or start_obj > now:
                    release_status = "Not Yet Publishing"

            try:
                r_obj['rated']
            except KeyError:
                r_obj['rated'] = "No Rating"

            item_embed.add_field(name="Publishing Details:",
                                 value=f"From: {start}\n"
                                       f"To: {end}\n"
                                       f"Status: {release_status}\n"
                                       f"Volume Count: {r_obj['volumes']}", inline=True)
            item_embed.add_field(name="Other Details:",
                                 value=f"Score: {r_obj['score']}\n"
                                       f"Age Rating: {rating}\n"
                                       f"My Anime List ID: {r_obj['mal_id']}\n"
                                       f"Members: " + "{:,}".format(r_obj['members']), inline=True)

        await initial_option_message.delete()
        # await initial_command.delete()
        await weeb_shit_channel.send(embed=item_embed)
        await _clean_temp_files()


def setup(bot):
    bot.add_cog(WeebCog(bot))
