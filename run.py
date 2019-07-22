import asyncio
import binascii
import json
import logging
import os
import random
import re
import shutil
import imageio
import sys
from datetime import datetime
from datetime import timedelta

import aiofiles
import aiohttp
import discord
import jikanpy.exceptions
import math
import matplotlib.pyplot as plt
import numpy as np
import pytz
import scipy
import scipy.cluster
import scipy.misc
from PIL import Image
from discord.ext import commands
from jikanpy import AioJikan

autism_score_format_regex = r"\((\d+|\d\?\d|(\d|\d\.\d+)\²)\/50\)$"

if not os.path.exists("./config/config.json"):
    shutil.copyfile("./config/default_config.json", "./config/config.json")
    input("Generated config file in ./config/config.json, edit this before you run the bot again.")
    exit(0)

print("Assigning variables...")
with open("./config/config.json", "r", encoding="utf-8") as config_fp:
    config_file = json.load(config_fp)
    b_token = config_file["bot"]["token"]
    owner_id = config_file["bot"]["owner_id"]
    cmd_prefix = config_file["bot"]["cmd_prefix"]
    role_dict = config_file["role_table"]
    autism_score_blue_role_id = config_file["misc_ids"]["autism_role_id"]
    main_announcement_channel_id = config_file["misc_ids"]["main_announcement_channel_id"]
    main_guild_id = config_file["misc_ids"]["main_guild_id"]
    pres_elect_gchq_id = config_file["misc_ids"]["pres_elect_id"]
    vice_pres_gchq_id = config_file["misc_ids"]["vice_pres_id"]
    protected_role_list = config_file["colour_command"]["protected_roles"]
    extra_exclusion_colours = config_file["colour_command"]["protected_colours"]
    blocked_mal_search_results = config_file["blocked_mal_search_results"]

bot = commands.Bot(command_prefix=cmd_prefix)

vote_file_in_use = False
current_mal_req_count_ps = 0
current_mal_req_count_pm = 0
vote_file_queue = []

colour_list = ["purple", "blue", "green", "yellow", "orange", "red", "irradiated_green"]

background_emoji_server_id = 192291925326299137
upvote_id = 536241661286547456
downvote_id = 536241664768081941

delete_messages_after = 60
exclusion_range = 100
# extra_exclusion_colours = ["2C2F33", "23272A", "99AAB5", "2B2B2B", "212121"]

watching = discord.Activity(type=discord.ActivityType.watching, name="you")

parsed_role_list_text = ""
for name in role_dict.keys():
    parsed_role_list_text = parsed_role_list_text + "\n- " + name

if not os.path.exists("./logs/"):
    os.mkdir("./logs/")
    print("Created ./logs/ folder for file based logging.")


async def _time_check():
    """Background deadline/task checking loop that is meant to sit on the main event loop"""
    global british_timezone
    while True:
        try:
            british_timezone = pytz.timezone('Europe/London')
            for deadline, task_meta_tuple in glob_deadline_dict.items():
                if deadline < datetime.now().isoformat():
                    if task_meta_tuple[1]:
                        eval(f"asyncio.create_task({task_meta_tuple[0]}())")
                    elif not task_meta_tuple[1]:
                        eval(f"{task_meta_tuple[0]}()")
                    logger.info(f"Finished running task: {task_meta_tuple[0]}, removed from deadline list")
                    with open("./deadlines/deadline.json", "r+") as deadlines_json:
                        deadlines_struct = json.load(deadlines_json)
                    try:
                        del deadlines_struct[deadline]
                        with open("./deadlines/deadline.json", "w") as deadlines_json:
                            json.dump(deadlines_struct, deadlines_json, indent=4)
                    except KeyError:
                        pass
                    del glob_deadline_dict[deadline]
        except Exception as e:
            logger.exception(e)
        await asyncio.sleep(30)


async def _add_deadline(datetime_obj, task, coro=False, use_file=True):
    """datetime_obj must be a timezone aware datetime object so it may be internally converted to UTC."""
    try:
        glob_deadline_dict[datetime_obj.isoformat()] = [task.__name__, coro]
        logger.info(f"Added {datetime_obj} deadline with action {task.__name__} to execution list.")
    except AttributeError:
        glob_deadline_dict[datetime_obj] = [task, coro]
        logger.info(f"Added {datetime_obj} deadline with action {task} to execution list.")

    if use_file:
        with open("./deadlines/deadline.json", "w", encoding="utf-8") as deadline_json:
            json.dump(glob_deadline_dict, deadline_json, indent=4)


async def _clean_colour_roles(context_guild):
    await asyncio.sleep(0.5)
    for crole in context_guild.roles:
        if "GCHQ[0x" in crole.name:
            if not crole.members:
                await crole.delete(reason="Automatic custom colour deletion when unused.")
    logger.info("Cleaned out empty colour roles")


async def _generate_blue_role_list(guild):
    global blue_role_id_list

    blue_role_id_list = []

    for role_obj in guild.roles:
        if role_obj.colour == discord.Colour.dark_blue():
            blue_role_id_list.append(role_obj.id)


async def mal_rate_limit_down_counter():
    global current_mal_req_count_pm
    global current_mal_req_count_ps

    await asyncio.sleep(2)
    current_mal_req_count_ps -= 1
    logger.debug("Reduced per second count.")
    await asyncio.sleep(58)
    current_mal_req_count_pm -= 1
    logger.debug("Reduced per minute count.")


async def anime_title_request(message_class):
    global current_mal_req_count_pm
    global current_mal_req_count_ps

    if message_class.content.startswith("["):
        req_type = "manga"
    elif message_class.content.startswith("{"):
        req_type = "anime"
    else:
        return None

    query_term = message_class.content.strip("{}[]")

    weeb_shit_channel = bot.get_channel(354656048218374155)

    paused = True
    while paused:
        if current_mal_req_count_pm >= 30:
            await asyncio.sleep(current_mal_req_count_pm - 30)
        elif current_mal_req_count_ps >= 2:
            await asyncio.sleep(1)
        else:
            paused = False

    current_mal_req_count_pm += 1
    current_mal_req_count_ps += 1

    logger.debug("Making API request.")
    r_obj_raw = await jikanAIO.search(search_type=req_type, query=query_term)
    logger.debug("API Request complete.")

    '''
    # Time to begin packaging the embed for returning to the user.
    pprint.pprint(r_obj_raw["results"][0])
    '''

    r_obj = r_obj_raw['results'][0]
    if r_obj['title'] in blocked_mal_search_results:
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

                logger.debug('finding clusters')
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
            else:
                colour_dec_split = [114, 137, 218]  # Discord's "Blurple", in the case that image isn't found

    os.remove(f"./tempfile_{r_obj['mal_id']}.jpg")

    item_embed = discord.Embed(title=(r_obj['title'] + " [" + r_obj['type'] + "]"), url=r_obj['url'],
                               timestamp=discord.Embed.Empty,
                               colour=discord.Colour.from_rgb(r=colour_dec_split[0],
                                                              g=colour_dec_split[1],
                                                              b=colour_dec_split[2]))

    if req_type == "anime":
        new_media_obj = await jikanAIO.anime(r_obj["mal_id"])
    else:
        new_media_obj = await jikanAIO.manga(r_obj["mal_id"])

    now = datetime.now(british_timezone)

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
        item_embed.add_field(name="Other Details:", value=f"Score: {r_obj['score']}\n"
                                                          f"Age Rating: {r_obj['rated']}\n"
                                                          f"Studio: {new_media_obj['studios'][0]['name']}\n"
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
                                                          f"Members: " + "{:,}".format(r_obj['members']), inline=True)

    # await weeb_shit_channel.send(embed=test_from_dict_embed)
    await weeb_shit_channel.send(embed=item_embed)


async def _test_for_aut_score(member_after, member_before=None):
    aut_blue_role = member_after.guild.get_role(autism_score_blue_role_id)
    if member_after.nick is None:
        return
    if member_before is not None:
        # Now we have only got member update events where nicknames have changed. Time to RegEx.
        if re.search(autism_score_format_regex, str(member_before.nick)) is not None:
            # Here the user already had an autism score.
            if re.search(autism_score_format_regex, str(member_after.nick)) is not None:
                # This is an instance where the user has not removed or added an autism score.
                return
            else:
                # In this case the user has removed their autism score and will lose their blue role.
                await member_after.remove_roles(aut_blue_role, reason="Member removed autism score from their name.")
        else:
            if re.search(autism_score_format_regex, member_after.nick) is not None:
                # In this case the member has added an autism score to their name so they will get the role.
                await member_after.add_roles(aut_blue_role, reason="Member added an autism score to their name.")
                try:
                    await member_after.send('You have been given the "{}" role for adding an autism score to your '
                                            'nickname in GCHQ. This role will be automatically removed if you take '
                                            'your autism score out of your name.'.format(aut_blue_role.name))
                except discord.errors.Forbidden:
                    pass
            else:
                # Here the user didn't have an autism score and hasn't added one either, nothing needs to be done.
                return
    elif member_before is None:
        # In this case the function is being run from startup, so we just check for people having autism scores.
        if re.search(autism_score_format_regex, str(member_after.nick)) is not None and (
                aut_blue_role not in member_after.roles):
            await member_after.add_roles(aut_blue_role, reason="Member has autism score in name on bot startup.")
            try:
                await member_after.send('You have been given the "{}" role for adding an autism score to your nickname '
                                        'in GCHQ. This role will be automatically removed if you take your autism '
                                        'score out of your name.'.format(aut_blue_role.name))
            except discord.errors.Forbidden:
                pass
        elif re.search(autism_score_format_regex, str(member_after.nick)) is None and (
                aut_blue_role in member_after.roles):
            await member_after.remove_roles(aut_blue_role, reason="Member has no autism score in name on bot startup.")


async def _auto_close_active_vote():
    global vote_ending

    if not os.path.exists("./active_votes/vote.json"):
        return "There is no currently active vote."

    vote_ending = True

    with open("./active_votes/vote.json") as vote_file:
        vote_data = json.load(vote_file)

    now_string = datetime.now(british_timezone).strftime("%Y-%m-%d_%H%M%S")

    sorted_counts = sorted(vote_data["counts"].items(), key=lambda key_val: key_val[1], reverse=True)

    main_guild = bot.get_guild(main_guild_id)
    pres_elect_role_obj = main_guild.get_role(pres_elect_gchq_id)
    vice_pres_role_obj = main_guild.get_role(vice_pres_gchq_id)

    vote_ending_announcement = f"__**VOTING FOR THE {pres_elect_role_obj.mention} HAS NOW " \
        f"ENDED.**__ \n\n__Final Results:__\n"

    sorted_dict = []
    for candidate, count in sorted_counts:
        vote_ending_announcement += f"{candidate}: {count}\n"
        sorted_dict.append([candidate, count])

    vote_ending_announcement += f"\nThank you for partaking in this democratic process and congratulate the new " \
        f"{pres_elect_role_obj.mention}"

    try:
        # new_pres_elect = bot.get_user(int(vote_data['candidate_name_id_tab'][sorted_dict[0][0].lower()]))
        new_pres_elect = main_guild.get_member(int(vote_data['candidate_name_id_tab'][sorted_dict[0][0].lower()]))
        vote_ending_announcement += f": {new_pres_elect.mention}"
        ids_used = True
    except KeyError:
        vote_ending_announcement += "."
        new_pres_elect = None
        ids_used = False

    ending_counts = {}
    for candidate_name in vote_data["counts"].keys():
        ending_counts[candidate_name] = 0

    if not os.path.exists("./vote_visuals/"):
        os.mkdir("./vote_visuals/")

    # Here we are essentially running the vote again from scratch to visualise the vote over time
    def gen_vote_graph(vote_record_obj):
        ending_counts[vote_record_obj["votes"][0].lower()] += 10
        ending_counts[vote_record_obj["votes"][1].lower()] += 5
        ending_counts[vote_record_obj["votes"][2].lower()] -= 5
        vote_fig, ax = plt.subplots()
        ax.barh(list(ending_counts.keys()), list(ending_counts.values()), height=0.2, align="edge",
                color="#004b86", edgecolor="black")
        ax.set_title(f"{vote_record_obj['datetime']}")
        ax.set(xlabel="FreddiePoints", ylabel="Candidate")
        vote_fig.canvas.draw()
        tmp_plot_img = np.frombuffer(vote_fig.canvas.tostring_rgb(), dtype="uint8")
        tmp_plot_img = tmp_plot_img.reshape(vote_fig.canvas.get_width_height()[::-1] + (3,))
        return tmp_plot_img

    kwargs_write = {"fps": 1.0, "quantizer": "nq"}

    imageio.mimsave("./vote_graph.gif",
                    [gen_vote_graph(vote_record) for vote_record in vote_data["timestamped_votes"]], fps=0.5)

    pres_roles = [pres_elect_role_obj, vice_pres_role_obj]
    for role_obj in pres_roles:
        for member in role_obj.members:
            await member.remove_roles(role_obj, reason="Automated end of term role removal")

    if ids_used:
        await new_pres_elect.add_roles(pres_elect_role_obj, reason="Automated President Elect Assignment.")

    vote_ending_announcement += '\n\nFive days of mandatory applause have been authorised by the central ' \
                                'government, please ensure you remain within the guidelines of Article 14.65b.91a ' \
                                'Part III Section XI of the "Handbook of Citizenship" for the duration, penalties ' \
                                'associated with failing to meet these simple requirements are detailed in Article ' \
                                '141.45a.12 Part II Section V List III of the "GCHQ Penal Charter."\n\n'

    main_announcement_channel_obj = bot.get_channel(main_announcement_channel_id)

    await main_announcement_channel_obj.send(vote_ending_announcement, file=discord.File("./vote_graph.gif"))

    shutil.move("./vote_graph.gif", f"./vote_graph_{now_string}.gif")

    os.rename("./active_votes/vote.json", "./ended_votes/vote_{}.json".format(now_string))

    vote_ending = False


@bot.event
async def on_connect():
    global jikanAIO
    global british_timezone
    global glob_deadline_dict
    global time_check_task
    await bot.change_presence(activity=watching)
    mainloop = asyncio.get_event_loop()
    logger.info("Opening MAL API event loop.")
    jikanAIO = AioJikan(loop=mainloop)
    british_timezone = pytz.timezone('Europe/London')
    glob_deadline_dict = {}
    time_check_task = asyncio.create_task(_time_check())


@bot.event
async def on_ready():
    global upvote_emoji_obj
    global downvote_emoji_obj
    global author_object
    # Any crap that needs to be done on startup can go here.
    author_object = bot.get_user(103595773379223552)
    upvote_emoji_obj = discord.utils.get(bot.emojis, id=upvote_id)
    downvote_emoji_obj = discord.utils.get(bot.emojis, id=downvote_id)
    logger.info("Bot process ready, running autism score checks and generating deadline tasks.")
    for member in bot.get_guild(main_guild_id).members:
        await _test_for_aut_score(member)
    if not os.path.exists("./deadlines/deadline.json"):
        with open("./deadlines/deadline.json", "w") as temp_json_create_fp:
            json.dump({}, temp_json_create_fp)
    with open("./deadlines/deadline.json", "r") as deadline_json_fp:
        deadline_json_loaded = json.load(deadline_json_fp)
    for task_datetime, task_package in deadline_json_loaded.items():
        await _add_deadline(task_datetime, task_package[0], coro=task_package[1], use_file=False)
    logger.info("Welcome to GCHQ Bot, for all your data harvesting needs.")


@bot.event
async def on_message(received_message):
    global current_mal_req_count_pm
    global current_mal_req_count_ps
    global jikanAIO
    if received_message.channel.id == 357259932472573956:
        # Upvote downvote BS
        if (re.search(r"[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)",
                      received_message.content) is None) and \
                not (received_message.attachments and received_message.embeds):
            return
        await received_message.add_reaction(upvote_emoji_obj)
        await received_message.add_reaction(downvote_emoji_obj)
        logger.debug("Reacted to message in #memes.")
        return

    if received_message.channel.id == 354656048218374155:
        if ((received_message.content.startswith("{") or received_message.content.startswith("[")) and
                (received_message.content[-1] == "}" or received_message.content[-1] == "]")):
            logger.info('{0.author} sent the MAL request: "{0.content}" in "{0.channel}" on the server "{0.guild}".'
                        .format(received_message))
            async with bot.get_channel(354656048218374155).typing():
                try:
                    await anime_title_request(received_message)
                except jikanpy.exceptions.APIException:
                    logger.exception("jikanpy.exceptions.APIException raised, attempting API restart.")
                    await jikanAIO.close()
                    jikanAIO = AioJikan(loop=asyncio.get_event_loop())
                    await anime_title_request(received_message)
            reduce_req_counters = asyncio.ensure_future(mal_rate_limit_down_counter())
            await reduce_req_counters
            return

    if received_message.channel.id == 354774298172325893 or received_message.channel.id == 364799469130219521 or \
            received_message.channel.id == 192291925326299137 or received_message.channel.id == 602560624542744642 or \
        received_message.channel.id == 602560399597895693:
        if received_message.content.startswith(cmd_prefix) and received_message.author != bot.user:
            logger.info('{0.author} sent the command: "{0.content}" in "{0.channel}" on the server "{0.guild}".'
                        .format(received_message))
            await asyncio.sleep(0.5)
            try:
                await bot.process_commands(received_message)
            except commands.PrivateMessageOnly:
                await received_message.delete()
                await received_message.author.send(f"The `{received_message.contents}` command "
                                                   f"should be used in DMs only.")
                logger.info(f"Deleted command from {received_message.author} intended for DMs.")
        else:
            return

    elif received_message.guild is None:  # Indicates a private message
        if received_message.content.startswith(cmd_prefix) and received_message.author != bot.user:
            logger.info('{0.author} sent the command: "{0.content}" in "{0.channel}".'.format(received_message))
            await asyncio.sleep(0.5)
            await bot.process_commands(received_message)

    else:
        return


@bot.event
async def on_member_join(member):
    logger.info("{} has joined the server.".format(member))
    await member.send('Welcome to GCHQ, this bot will provide commands allowing you to gain access to '
                      'hidden text channels in the GCHQ server, use `{0}help` to see commands.'
                      '\n\nTo see how role based commands work use: `{0}help role`.\n\n'
                      'It is also **STRONGLY RECOMMENDED** that you read #welcome to find out about the DBAC ruleset '
                      'and the Constitution of GCHQ.'
                      .format(cmd_prefix))
    pingrole_obj = discord.utils.get(member.guild.roles, name="Pingrole")
    await asyncio.sleep(600)  # The server this bot is used on has a wait period before you can talk.
    await member.add_roles(pingrole_obj, reason="New members automatically get Pingrole")
    logger.info("Successfully messaged and added new user to Pingrole.")


@bot.event
async def on_member_update(member_before, member_after):
    if member_before.nick == member_after.nick:
        return

    await _test_for_aut_score(member_after, member_before)


@bot.group(name="cog")
async def cog_grp(ctx):
    """Cog command group, includes the onload an offload sub-commands, invoking the group directly has no effect."""
    if ctx.invoked_subcommand is None:
        logger.info("Command: {0.content} from user {0.author} had no subcommand.".format(ctx.message))
        await ctx.send("You need to include a subcommand with this one, use `{}help cog` if you need further "
                       "assistance.".format(cmd_prefix))


@cog_grp.command()
@commands.has_permissions(administrator=True)
async def load(ctx, cog):
    """Loads a new cog onto the bot, persists between runs."""
    pass


@cog_grp.command()
@commands.has_permissions(administrator=True)
async def unload(ctx, cog):
    """Unloads a loaded cog from the bot."""
    pass


@bot.group()
async def role(ctx):
    """Role is a command group that houses the common use role commands like: "role get" and "role lose"."""
    if ctx.invoked_subcommand is None:
        logger.info("Command: {0.content} from user {0.author} had no subcommand.".format(ctx.message))
        await ctx.send("You need to include a subcommand with this one, use `{}help role` if you need further "
                       "assistance.".format(cmd_prefix))


@role.command()
async def get(ctx, req_role=""):
    """Get the bot to give you a chosen role"""
    try:
        req_role = req_role.lower()
    except TypeError:
        pass
    if req_role not in role_dict.keys():
        await ctx.send("You need to include a valid role id in this subcommand, use `{}role list` to see them."
                       .format(cmd_prefix))
        return

    target_role_object = await commands.RoleConverter().convert(ctx, role_dict[req_role])
    target_user_object = ctx.author

    if req_role in colour_list:
        logger.info("User requested colour role, generating object list and checking ownership.")
        colour_role_objects = []
        for individual_role in ctx.message.guild.roles:
            if individual_role.name.lower() in colour_list:
                colour_role_objects.append(individual_role)
        await asyncio.sleep(0.2)
        for colour_role in colour_role_objects:
            if colour_role in target_user_object.roles:
                logger.info("User already owns a colour role, removing said role now.")
                await ctx.send("You already have the role: {}, it will be removed.".format(colour_role))
                role_to_remove = discord.utils.get(ctx.message.guild.roles, name=colour_role.name)
                await target_user_object.remove_roles(role_to_remove, reason="User may only have one colour role.")
                logger.info("Removed the role {0} from user: {1}.".format(role_to_remove, target_user_object))
        await asyncio.sleep(0.2)

    if target_role_object in target_user_object.roles:
        await ctx.send("You already have the requested role, to remove a role use: `{}role lose <role>`."
                       .format(cmd_prefix))
        return

    logger.info('Now attempting to add {} to the role: "{}".'.format(ctx.message.author, role_dict[req_role]))
    await target_user_object.add_roles(target_role_object, reason="Role requested by user")
    logger.info('Addition of {} to role: "{}" completed successfully.'.format(ctx.message.author, role_dict[req_role]))
    await ctx.send("You have been added to the group: " + role_dict[req_role])


@role.command()
async def lose(ctx, req_role=""):
    """Get the bot to take away one of your roles."""
    try:
        req_role = req_role.lower()
    except TypeError:
        pass
    if req_role not in role_dict.keys():
        await ctx.send("You need to include a valid role id in this subcommand, use `{}role list` to see them."
                       .format(cmd_prefix))
        return

    target_role_object = await commands.RoleConverter().convert(ctx, role_dict[req_role])
    if target_role_object not in ctx.message.author.roles:
        await ctx.send("You don't have the requested role, to add a role use: `{}role get <role>`.".format(cmd_prefix))
        return

    logger.info('Now attempting to remove {} from the role: "{}".'.format(ctx.message.author, role_dict[req_role]))
    await ctx.author.remove_roles(target_role_object)
    logger.info('Removal of {} from role: "{}" completed successfully.'.format(ctx.message.author, role_dict[req_role]))
    await ctx.send("You have been removed from the group: " + role_dict[req_role])


@role.command(name="list")
async def list_roles(ctx):
    """Lists the currently working roles that the bot can give/take."""
    await ctx.send("Role list:\n```\n{}```\nTo use these role names, simply type: `{}role get <role>` in this channel."
                   .format(parsed_role_list_text, cmd_prefix))


@bot.command()
async def stop_process(ctx):
    if ctx.message.author.id == owner_id:
        await ctx.send(":wave:")
        await jikanAIO.close()
        time_check_task.cancel()
        await bot.logout()
        logger.warning("Bot has now logged out and is shutting down!")
        await asyncio.sleep(5)
        sys.exit(0)
    else:
        logger.warning("User: {} attempted to shut the bot down but doesn't have correct permissions!"
                       .format(ctx.message.author))
        return


@bot.command(pass_context=True)
@commands.dm_only()
async def vote_for(ctx, first_choice="", second_choice="", last_choice=""):
    """Used for special votes configured by bot owner, usage example: !vote_for Freddie Kim_Jong-Un Mao."""

    global vote_file_in_use
    global vote_file_queue

    await ctx.trigger_typing()

    vote_time = datetime.now(british_timezone).strftime("%Y-%m-%d %H:%M:%S")

    waiting_message_sent = False
    thread_id = random.randint(1, 10000)

    while thread_id in vote_file_queue:
        thread_id = random.randint(1, 10000)

    main_guild_obj = bot.get_guild(main_guild_id)

    await _generate_blue_role_list(main_guild_obj)

    author_vote_authorised = False

    author_main_guild = main_guild_obj.get_member(ctx.author.id)

    for role_obj in author_main_guild.roles:
        if role_obj.id in blue_role_id_list:
            author_vote_authorised = True
            break

    if not author_vote_authorised:
        await ctx.author.send("You do not have the authorisation to vote. Please contact party leadership to establish "
                              "why this is the case.")
        return

    if not vote_file_queue:
        vote_file_queue.append(thread_id)
        await asyncio.sleep(0.5)
    else:
        vote_file_queue.append(thread_id)

    logging.debug("Thread with ID: {} has been opened in a list of length: {}.".format(thread_id, len(vote_file_queue)))

    while vote_file_queue[0] != thread_id or vote_file_in_use:
        if not waiting_message_sent:
            logger.info("Thread ID: {} has been stopped from accessing the file and is in position {} of the queue."
                        .format(thread_id, vote_file_queue.index(thread_id)))
            waiting_message_sent = True
        await asyncio.sleep(0.05)

    logger.debug(f"Thread ID: {thread_id}, Thread List: {vote_file_queue}.")

    vote_file_in_use = True
    vote_file_queue.pop(0)

    if vote_ending:
        await ctx.send("Vote is currently ending, your vote can not be counted.")
        logger.info("User attempted to vote while the vote was ending.")
        vote_file_in_use = False
        return

    votes = [first_choice.lower(), second_choice.lower(), last_choice.lower()]

    if votes[0] == votes[1] or votes[1] == votes[2] or votes[2] == votes[0]:
        await ctx.send("You have attempted to vote for the same person more than once.")
        logger.info("User attempted to vote for the same candidate more than once.")
        vote_file_in_use = False
        return

    if os.path.exists("./active_votes/vote.json"):
        with open("./active_votes/vote.json", "r") as json_file:
            vote_data = json.load(json_file)
    else:
        vote_file_in_use = False
        logger.info("User attempted to vote when there was no vote running.")
        await ctx.send("There is currently no vote running.")
        return

    for user in vote_data["votes"].keys():
        if ctx.author.id == user[1]:
            await ctx.send("You have already voted in this election, please do not attempt to vote again.")
            vote_file_in_use = False
            logger.info("User attempted to vote twice.")
            return

    valid_vote_targets = []

    for key, value in vote_data["counts"].items():
        valid_vote_targets.append(key)

    for key in votes:  # ensures all vote targets are valid and handles if it's not.
        if key.lower() not in valid_vote_targets:
            await ctx.send("One or more of your votes are on invalid targets, check the main message for valid "
                           "candidates and try again.")
            logger.info("User failed to select all valid candidates in their vote.")
            vote_file_in_use = False
            return

    try:
        vote_data["counts"][first_choice.lower()] += 10
        vote_data["counts"][second_choice.lower()] += 5
        vote_data["counts"][last_choice.lower()] -= 5
    except NameError:
        await ctx.send("One or more of your votes are on invalid targets, check the main message for valid "
                       "candidates and try again.")
        logger.info("User failed to select all valid candidates in their vote.")
        vote_file_in_use = False
        return

    vote_data["votes"][ctx.author.id] = votes
    vote_data["timestamped_votes"].append({"datetime": vote_time, "user_id": ctx.author.id, "votes": votes,
                                           "name": "{0.name}#{0.discriminator}".format(ctx.author)})

    with open("./active_votes/vote.json", "w") as json_votes:
        json.dump(vote_data, json_votes, indent=4)
        logger.info("Dumped vote data into file, opening up for next command.")

    vote_file_in_use = False
    await ctx.send("Your votes have been registered, thank you for being an active member of our democracy.")


@bot.command(pass_context=True)
@commands.is_owner()
async def start_vote(ctx, target_role, time_till_close, *, candidate_list=""):
    """time_till_close is in hours only"""

    time_till_close = int(time_till_close)

    if time_till_close <= 0:
        return

    candidate_list = candidate_list.split()

    try:
        int(candidate_list[0])
        candidate_ids_in_use = True
    except ValueError:
        candidate_ids_in_use = False

    logger.info("Successfully finished parsing list of candidates.\n" + str(candidate_list))

    announce_message = "Welcome to GCHQ's Government programmed Conditionally Universal National Term vote System! " \
                       "Below will be the valid candidates for you to vote for, below that the voting format and " \
                       "how to take part in GCHQ's democratic process.\n\n" \
                       "__Eligible Candidates__:\n"

    try:
        target_role_obj = await discord.ext.commands.RoleConverter().convert(ctx, target_role)
    except discord.ext.commands.CommandError:
        logger.exception("Failed to start vote due to improper target role.")
        return

    close_datetime = datetime.now(tz=british_timezone) + timedelta(hours=time_till_close)

    vote_storage = {
        "counts": {},
        "votes": {},
        "target_role_id": target_role_obj.id,
        "timestamped_votes": [],
        "vote_close_datetime": close_datetime.isoformat()
    }

    if candidate_ids_in_use:
        vote_storage["candidate_name_id_tab"] = {}
        for candidate_id in candidate_list:
            candidate_obj = bot.get_user(int(candidate_id))
            announce_message += candidate_obj.name + "\n"
            vote_storage["counts"][candidate_obj.name.lower()] = 0
            vote_storage["candidate_name_id_tab"][candidate_obj.name.lower()] = candidate_id
    else:
        for candidate in candidate_list:
            announce_message += candidate + "\n"
            vote_storage["counts"][candidate.lower()] = 0

    logger.info("Successfully completed the candidates listed on the announcement message and in storage.")

    announce_message = announce_message + "\nTo vote, send this command to GCHQBot: " \
                                          "`{0}vote_for <first_choice> <second_choice> <last_choice>`. " \
                                          "Please understand that while the choice names are not case sensitive, " \
                                          "they __**must be in order and must be spelt the same way, spaces split up " \
                                          "your votes**__.\n\nHere's an example of its use: " \
                                          "`{0}vote_for Freddie Kim_Jong-Un Mao`, here you are voting for Freddie " \
                                          "as your first choice, Lil' Kimmy as your second and Mao as your last " \
                                          "choice.".format(cmd_prefix)

    # Now need to handle directories for vote storage under the vote_name
    if not os.path.exists("./active_votes/"):
        os.mkdir("./active_votes/")
        logger.info("Generated directory for active votes.")
    if not os.path.exists("./ended_votes/"):
        os.mkdir("./ended_votes/")
        logger.info("Generated directory for ended votes.")

    with open("./active_votes/vote.json", mode="w") as json_file:
        json.dump(vote_storage, json_file, indent=4)
        logger.info("Written JSON file to ./active_votes/vote.json.")

    target_announce_channel = await commands.TextChannelConverter().convert(ctx, str(main_announcement_channel_id))

    await target_announce_channel.send(announce_message)
    await _add_deadline(close_datetime, _auto_close_active_vote, coro=True)


@bot.command()
@commands.is_owner()
async def end_vote(ctx):
    """Ends the currently active vote, cba to refactor such that multiple votes can be simultaneously ongoing because
    I'm lazy. This is a wrapping function that doesn't generally need to be used, set a time on the start_vote instead.
    """
    global vote_ending

    vote_ending = True
    closure_output = await _auto_close_active_vote()

    if closure_output == "There is no currently active vote.":
        await ctx.send("There is no currently active vote.")


@bot.command(name="colourme")
async def colour_me(ctx, colour_hex: str):
    """Gives the command invoker a custom colour role if they satisfy given conditions.
    If colour_hex is given as "remove", the bot will remove the colour role and exit the
    operation.
    """

    # Preprocess the colour
    if colour_hex.lower() == "remove":
        for arole in ctx.author.roles:
            if "GCHQ[0x" in arole.name:
                await ctx.author.remove_roles(arole, reason="User requested colour role removal.")

        await _clean_colour_roles(ctx.guild)
        return

    if len(colour_hex) > 6:
        await ctx.send("The colour string requested is invalid.", delete_after=delete_messages_after)
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
                              delete_after=delete_messages_after)
            return
        colour_dec_split.append(colour_dec)

    exclusion_cube_origins = []

    # Set up exclusion zones for colours
    for admin_role_name in protected_role_list:
        # Let's first gather all the admin role
        try:
            admin_role = await commands.RoleConverter().convert(ctx, admin_role_name)
            # Now find its colour and add it to the list of exclusion origins
            admin_role_colour = admin_role.colour.to_rgb()
            exclusion_cube_origins.append(list(admin_role_colour))
        except discord.ext.commands.errors.BadArgument:
            logger.info("Admin role defined in config not found in guild.")

    for extra_exclusion_colour in extra_exclusion_colours:
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
            dim_min_max = [cube_center[i] - exclusion_range, cube_center[i] + exclusion_range]
            if not (dim_min_max[0] < colour_dec_split[i] < dim_min_max[1]):
                in_cube = False
                break
        if colour_dec == cube_center:
            in_cube = True
        if in_cube:
            await ctx.send(f"The colour you have selected is too close to that of an admin role or "
                           f"protected colour.\n\nYour colour (decimal): {colour_dec_split} "
                           f"was too close to {cube_center}. \nChange one or more of the components "
                           f"such that they are {math.ceil(exclusion_range / 2)} away from the protected colour.")
            return

    # Not much left to do, only need to create the custom colour role and make sure that it
    # sits below the lowest defined admin role.
    admin_role_obj_list = {}
    for admin_role in protected_role_list:
        try:
            admin_role_object = await commands.RoleConverter().convert(ctx, admin_role)
            admin_role_obj_list[admin_role_object.position] = admin_role_object
        except discord.ext.commands.errors.BadArgument:
            logger.info("Admin role defined in config not found in guild.")

    sorted_admin_list_pos = sorted(admin_role_obj_list)

    # Now we have the sorted list of admin roles, let's query all roles and see if we already have
    # the requested colour created. GCHQBot colour roles have the naming convention: CPS[0x<R><G><B>] in hex.
    try:
        prev_colour = await commands.RoleConverter().convert(ctx, f"GCHQ[0x{colour_hex.upper()}]")
        await prev_colour.edit(position=sorted_admin_list_pos[0])
        await ctx.author.add_roles(prev_colour, reason="Custom colour requested.")
        return
    except commands.BadArgument:
        # The role doesn't already exist, let's pass.
        pass

    # Now to create the role we wanted all along.
    new_colour_role = await ctx.guild.create_role(name=f"GCHQ[0x{colour_hex.upper()}]",
                                                  reason="Custom colour role generation by GCHQBot.",
                                                  colour=discord.Colour.from_rgb(r=colour_dec_split[0],
                                                                                 g=colour_dec_split[1],
                                                                                 b=colour_dec_split[2]))

    await new_colour_role.edit(position=sorted_admin_list_pos[0])
    await new_colour_role.edit(position=sorted_admin_list_pos[0])

    for invoker_role in ctx.author.roles:
        if "GCHQ[0x" in invoker_role.name:
            await ctx.author.remove_roles(invoker_role, reason="Removing old colour role from user.")

    await ctx.author.add_roles(new_colour_role, reason="Automatic custom colour allocation by request.")

    await _clean_colour_roles(ctx.guild)


# Begin logging
print("Logging startup...")
logger = logging.getLogger("GCHQBot")
logger.setLevel(logging.INFO)
formatter = logging.Formatter('[{asctime}] [{levelname:}] {name}: {message}', '%Y-%m-%d %H:%M:%S', style='{')
file_log = logging.FileHandler("./logs/bot.log", encoding="utf-8", mode="w")
console_log = logging.StreamHandler()
file_log.setFormatter(formatter)
console_log.setFormatter(formatter)
logger.addHandler(file_log)
logger.addHandler(console_log)
logger.info("Logging configured, running rest of startup.")

if not os.path.exists("./cogs/"):
    os.mkdir("./cogs/")
    logger.info("Created ./cogs/ directory.")
if not os.path.exists("./cogs/loaded/"):
    os.mkdir("./cogs/loaded/")
    logger.info("Created ./cogs/loaded/ directory.")
if not os.path.exists("./cogs/unloaded/"):
    os.mkdir("./cogs/unloaded/")
    logger.info("Created ./cogs/unloaded/ directory.")
if not os.path.exists("./deadlines/"):
    os.mkdir("./deadlines/")
    logger.info("Created ./deadlines/ directory.")

logger.info("Starting bot process.")
vote_ending = False
bot.run(b_token)
