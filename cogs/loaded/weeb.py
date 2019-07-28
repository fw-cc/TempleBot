from discord.ext import commands
import asyncio
import logging
import binascii
import scipy.cluster
import discord
from datetime import datetime
import numpy as np
from PIL import Image
import aiohttp
import aiofiles
from jikanpy import AioJikan
import pytz
from config.config_reader import ConfigReader
import jikanpy.exceptions


class WeebCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("GCHQBot.weeb")
        self.british_timezone = pytz.timezone('Europe/London')
        self.logger.info("Opening MAL API event loop.")
        self.jikanAIO = AioJikan(loop=asyncio.get_event_loop())
        self.current_mal_req_count_ps = 0
        self.current_mal_req_count_pm = 0

    @commands.command(name="weeb_search")
    async def weeb_search_command(self, ctx):
        ctx.message.content = ctx.message.content.strip(config_var.cmd_prefix).strip("weeb_search ")
        async with self.bot.get_channel(config_var.weeb_channel_id).typing():
            try:
                await self.anime_title_request_func(ctx.message)
            except jikanpy.exceptions.APIException:
                self.logger.exception("jikanpy.exceptions.APIException raised, attempting API restart.")
                await self.jikanAIO.close()
                self.jikanAIO = AioJikan(loop=asyncio.get_event_loop())
                await self.anime_title_request_func(ctx.message)
            asyncio.create_task(self.mal_rate_limit_down_counter())

    def cog_unload(self):
        self.jikanAIO.close()

    async def mal_rate_limit_down_counter(self):
        await asyncio.sleep(2)
        self.current_mal_req_count_ps -= 1
        self.logger.debug("Reduced per second count.")
        await asyncio.sleep(58)
        self.current_mal_req_count_pm -= 1
        self.logger.debug("Reduced per minute count.")

    async def anime_title_request_func(self, message_class):
        if message_class.content.startswith("["):
            req_type = "manga"
        elif message_class.content.startswith("{"):
            req_type = "anime"
        else:
            return None

        query_term = message_class.content.strip("{}[]")

        weeb_shit_channel = self.bot.get_channel(config_var.weeb_channel_id)

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
        r_obj_raw = await self.jikanAIO.search(search_type=req_type, query=query_term)
        self.logger.debug("API Request complete.")

        '''
        # Time to begin packaging the embed for returning to the user.
        pprint.pprint(r_obj_raw["results"][0])
        '''

        r_obj = r_obj_raw['results'][0]
        if r_obj['title'] in config_var.blocked_mal_search_results:
            return

        prepro_img_url = r_obj['image_url'].rsplit("?", 1)[0].rsplit(".", 1)
        new_img_url = prepro_img_url[0] + "l." + prepro_img_url[1]

        async with aiohttp.ClientSession() as session:
            async with session.get(new_img_url) as target_image_res:
                if target_image_res.status == 200:
                    temp_file = await aiofiles.open(f"./tempfile_{r_obj['mal_id']}.jpg", mode="wb")
                    await temp_file.write(await target_image_res.read())
                    await temp_file.close()

                    # CODE HERE USED FOR FINDING DOMINANT COLOUR, by Stack Overflow user: Peter Hansen
                    # https://stackoverflow.com/questions/3241929/python-find-dominant-most-common-color-in-an-image
                    num_clusters = 5
                    im = Image.open(f"./tempfile_{r_obj['mal_id']}.jpg")
                    im = im.resize((150, 210))  # optional, to reduce time
                    ar = np.asarray(im)
                    shape = ar.shape
                    ar = ar.reshape(scipy.product(shape[:2]), shape[2]).astype(float)

                    self.logger.debug('finding clusters')
                    codes, dist = scipy.cluster.vq.kmeans(ar, num_clusters)

                    vecs, dist = scipy.cluster.vq.vq(ar, codes)  # assign codes
                    counts, bins = scipy.histogram(vecs, len(codes))  # count occurrences

                    index_max = scipy.argmax(counts)  # find most frequent
                    peak = codes[index_max]
                    embed_colour = binascii.hexlify(bytearray(int(c) for c in peak)).decode('ascii')
                    # ENDS

                    im.close()
                    target_image_res.close()

                    colour_hex_split = [embed_colour[0:2], embed_colour[2:4], embed_colour[4:6]]
                    colour_dec_split = []
                    colour_dec_concat = ""
                    for colour in colour_hex_split:
                        colour_dec = int(colour, 16)
                        colour_dec_split.append(colour_dec)
                        colour_dec_concat += str(colour_dec)
                    found_image = True
                else:
                    colour_dec_split = [114, 137, 218]  # Discord's "Blurple", in the case that image isn't found
                    found_image = False

        item_embed = discord.Embed(title=(r_obj['title'] + " [" + r_obj['type'] + "]"), url=r_obj['url'],
                                   timestamp=discord.Embed.Empty,
                                   colour=discord.Colour.from_rgb(r=colour_dec_split[0],
                                                                  g=colour_dec_split[1],
                                                                  b=colour_dec_split[2]))

        if req_type == "anime":
            new_media_obj = await self.jikanAIO.anime(r_obj["mal_id"])
        else:
            new_media_obj = await self.jikanAIO.manga(r_obj["mal_id"])

        now = datetime.now(self.british_timezone)

        def date_ordinal_letter(day_num: int) -> str:
            if 4 <= day_num <= 20 or 24 <= day_num <= 30:
                return "th"
            else:
                return ["st", "nd", "rd"][int(str(day_num)[-1]) - 1]

        brit_day_in = now.strftime('%d').lstrip("0")
        now_brit_day = brit_day_in + date_ordinal_letter(int(brit_day_in))
        now_brit = now.strftime(f'%a %b {now_brit_day}, %Y at %H:%M:%S')

        '''
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
        }'''

        def id_letter(req_form):
            if req_form == "anime":
                return "a"
            else:
                return "m"

        if r_obj["synopsis"] == "":
            r_obj["synopsis"] = f"No synopsis information has been added to this title. " \
                f"Help improve the MAL database by adding a synopsis " \
                f"[here](https://myanimelist.net/dbchanges.php?{id_letter(req_type)}" \
                f"id={r_obj['mal_id']}&t=synopsis)."

        # test_from_dict_embed = discord.Embed.from_dict(embed_pregen_dict)
        # test_from_dict_embed.set_author(name="Pytato/GCHQBot", icon_url="https://i.imgur.com/5zaQwWr.jpg",
        #                                url="https://github.com/Pytato/GCHQBot")
        # test_from_dict_embed.add_field(name="Synopsis:", value=r_obj['synopsis'], inline=False)
        # test_from_dict_embed.set_thumbnail(url=new_img_url)

        item_embed.set_footer(text=f"Data scraped with JikanPy | {now_brit} {now.tzname()}",
                              icon_url="https://i.imgur.com/fSPtnoP.png")
        item_embed.set_author(name="Pytato/GCHQBot", icon_url="https://i.imgur.com/5zaQwWr.jpg",
                              url="https://github.com/Pytato/GCHQBot")
        if found_image:
            item_embed.set_thumbnail(url=new_img_url)
        item_embed.add_field(name="Synopsis:", value=r_obj['synopsis'], inline=False)

        date_format = "%Y-%m-%d"
        now = datetime.now()

        start_obj = None

        if r_obj['end_date'] is None:
            end = "?"
        else:
            end = r_obj['end_date'].split("T")[0]
        if r_obj['start_date'] is None:
            start = "?"
        else:
            start = r_obj['start_date'].split("T")[0]
            start_obj = datetime.strptime(start, date_format)

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

            item_embed.add_field(name="Airing Details:", value=f"From: {start}\n"
                                                               f"To: {end}\n"
                                                               f"Status: {release_status}\n"
                                                               f"Episode Count: {r_obj['episodes']}", inline=True)
            try:
                item_embed.add_field(name="Other Details:",
                                     value=f"Score: {r_obj['score']}\n"
                                           f"Age Rating: {r_obj['rated']}\n"
                                           f"Studio: {new_media_obj['studios'][0]['name']}\n"
                                           f"Members: " + "{:,}".format(r_obj['members']), inline=True)
            except IndexError:
                item_embed.add_field(name="Other Details:",
                                     value=f"Score: {r_obj['score']}\n"
                                           f"Age Rating: {r_obj['rated']}\n"
                                           f"Studio: Not Yet Defined\n"
                                           f"Members: " + "{:,}".format(r_obj['members']), inline=True)

            # test_from_dict_embed.add_field(name="Airing Details:", value=f"From: {start}\n"
            #                                                             f"To: {end}\n"
            #                                                             f"Status: {release_status}\n"
            #                                                             f"Episode Count: {r_obj['episodes']}",
            #                               inline=True)
            # test_from_dict_embed.add_field(name="Other Details:", value=f"Score: {r_obj['score']}\n"
            #                                                            f"Age Rating: {r_obj['rated']}\n"
            #                                                            f"My Anime List ID: {r_obj['mal_id']}\n"
            #                                                            f"Members: " + "{:,}".format(r_obj['members']),
            #                               inline=True)

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

            item_embed.add_field(name="Publishing Details:", value=f"From: {start}\n"
                                                                   f"To: {end}\n"
                                                                   f"Status: {release_status}\n"
                                                                   f"Volume Count: {r_obj['volumes']}", inline=True)
            item_embed.add_field(name="Other Details:", value=f"Score: {r_obj['score']}\n"
                                                              f"Age Rating: {r_obj['rated']}\n"
                                                              f"My Anime List ID: {r_obj['mal_id']}\n"
                                                              f"Members: " + "{:,}".format(r_obj['members']),
                                 inline=True)

        await weeb_shit_channel.send(embed=item_embed)


def setup(bot):
    global config_var

    config_var = ConfigReader()
    bot.add_cog(WeebCog(bot))
