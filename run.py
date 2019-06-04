import logging
from discord.ext import commands
import discord
import asyncio
import os
import sys
import json
import random
import math

print("Assigning variables...")
b_token = "Your bot token in here"
cmd_prefix = "!"
bot = commands.Bot(command_prefix=cmd_prefix)
owner_id = 103595773379223552
vote_file_in_use = False
vote_file_queue = []

role_dict = {"soton":               "Houthsampton (Soton)",
             "uea":                 "UAE (Uni of East Anglia)",
             "cymru":               "The Cymru Cooperative (Swansea)",
             "exeter":              "Southest Westest WouthSest (Exeter)",
             "manchester":          "Wildlings 1 (Manchester)",
             "liverpool":           "Wildlings A (Liverpool)",
             "leeds":               "REEEEEEEEEDS (Leeds)",
             "surrey":              "Soorreey (Surrey)",
             "bristol":             "Brihstool (Bristol)",
             "weeaboo":             "ðŸŽŒWeeabooðŸŽŒ",
             "hearthstone":         "Hearthstone",
             "purple":              "Purple",
             "blue":                "Blue",
             "green":               "Green",
             "yellow":              "Yellow",
             "orange":              "Orange",
             "red":                 "Red",
             "irradiated_green":    "Irradiated Green",
             "pingable":            "Pingrole"}

colour_list = ["purple", "blue", "green", "yellow", "orange", "red", "irradiated_green"]

background_emoji_server_id = 192291925326299137
upvote_id = 536241661286547456
downvote_id = 536241664768081941

delete_messages_after = 60
exclusion_range = 100
protected_role_list = ["❄ Snowflake ❄",
                       "President Elect of GCHQ",
                       "Glorious Leaders",
                       "Vice-President of GCHQ",
                       "OC Memer",
                       "Ascended"]
extra_exclusion_colours = ["2C2F33", "23272A", "99AAB5", "2B2B2B", "212121"]
watching = discord.Activity(type=discord.ActivityType.watching, name="you")

parsed_role_list_text = ""
for name in role_dict.keys():
    parsed_role_list_text = parsed_role_list_text+"\n- "+name

if not os.path.exists("./logs/"):
    os.mkdir("./logs/")
    print("Created ./logs/ folder for file based logging.")


async def clean_colour_roles(context_guild):
    await asyncio.sleep(0.5)
    for crole in context_guild.roles:
        if "GCHQ[0x" in crole.name:
            if not crole.members:
                await crole.delete(reason="Automatic custom colour deletion when unused.")
    logger.info("Cleaned out empty colour roles")


@bot.event
async def on_connect():
    await bot.change_presence(activity=watching)


@bot.event
async def on_ready():
    global upvote_emoji_obj
    global downvote_emoji_obj
    # Any crap that needs to be done on startup can go here.
    upvote_emoji_obj = discord.utils.get(bot.emojis, id=upvote_id)
    downvote_emoji_obj = discord.utils.get(bot.emojis, id=downvote_id)
    logger.info("Bot process ready!")
    logger.info("Welcome to GCHQ Bot, for all your data harvesting needs.")


@bot.event
async def on_message(received_message):
    if received_message.channel.id == 357259932472573956:
        # Upvote downvote BS
        await received_message.add_reaction(upvote_emoji_obj)
        await received_message.add_reaction(downvote_emoji_obj)
        logger.info("Reacted to message in #memes.")
        return
    if received_message.channel.id == 354774298172325893 or received_message.channel.id == 364799469130219521 or \
            received_message.channel.id == 192291925326299137:
        if received_message.content.startswith(cmd_prefix) and received_message.author != bot.user:
            logger.info('{0.author} sent the command: "{0.content}" in "{0.channel}" on the server "{0.guild}".'
                        .format(received_message))
            await asyncio.sleep(0.5)
            await bot.process_commands(received_message)
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
    await ctx.send("You have been added to the group: "+role_dict[req_role])


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
    await ctx.send("You have been removed from the group: "+role_dict[req_role])


@role.command(name="list")
async def list_roles(ctx):
    """Lists the currently working roles that the bot can give/take."""
    await ctx.send("Role list:\n```\n{}```\nTo use these role names, simply type: `{}role get <role>` in this channel."
                   .format(parsed_role_list_text, cmd_prefix))


@bot.command()
async def stop_process(ctx):
    if ctx.message.author.id == owner_id:
        await ctx.send(":wave:")
        await bot.logout()
        logger.warning("Bot has now logged out and is shutting down!")
        await asyncio.sleep(1)
        sys.exit(0)
    else:
        logger.warning("User: {} attempted to shut the bot down but doesn't have correct permissions!"
                       .format(ctx.message.author))
        return


@bot.command(pass_context=True)
async def vote_for(ctx, first_choice="", second_choice="", last_choice=""):
    """Used for special votes configured by bot owner, usage example: !vote_for Freddie Kim_Jong-Un Mao."""

    global vote_file_in_use
    global vote_file_queue

    waiting_message_sent = False
    thread_id = random.randint(1, 10000)

    while thread_id in vote_file_queue:
        thread_id = random.randint(1, 10000)

    logging.info("Thread with ID: {} has been opened in a list of length: {}.".format(thread_id, len(vote_file_queue)))

    if not vote_file_queue:
        vote_file_queue.append(thread_id)
        await asyncio.sleep(0.5)
    else:
        vote_file_queue.append(thread_id)

    while vote_file_queue[0] != thread_id or vote_file_in_use:
        if not waiting_message_sent:
            logger.info("Thread ID: {} has been stopped from accessing the file and is in position {} of the queue."
                        .format(thread_id, vote_file_queue.index(thread_id)))
            waiting_message_sent = True
        await asyncio.sleep(0.05)

    logger.info(f"Thread ID: {thread_id}, Thread List: {vote_file_queue}.")

    vote_file_in_use = True
    vote_file_queue.pop(0)

    votes = [first_choice, second_choice, last_choice]

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
        return

    have_voted = [*vote_data["votes"]]
    if ctx.author.name+"#"+ctx.author.discriminator in have_voted:
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

    vote_data["votes"]["{0.name}#{0.discriminator}".format(ctx.author)] = votes

    with open("./active_votes/vote.json", "w") as json_votes:
        json.dump(vote_data, json_votes, indent=4)
        logger.info("Dumped vote data into file, opening up for next command.")

    vote_file_in_use = False
    await ctx.send("Your votes have been registered, thank you for partaking in this incredible change to GCHQ's "
                   "political landscape.")


@bot.command(pass_context=True)
async def start_vote(ctx, candidate_list=""):
    if ctx.message.author.id != owner_id:
        logger.warning("User: {} attempted to run a vote but doesn't have correct permissions!"
                       .format(ctx.message.author))
        return
    candidate_list = candidate_list.split()

    logger.info("Successfully finished parsing list of candidates.\n" + str(candidate_list))

    announce_message = "Welcome to GCHQ's Government programmed Conditionally Universal National Term vote System! " \
                       "Below will be the valid candidates for you to vote for, below that the voting format and " \
                       "how to take part in this landmark shift in GCHQ's political landscape.\n\n" \
                       "__Eligible Candidates__:\n"

    for candidate in candidate_list:
        announce_message = announce_message+candidate+"\n"

    logger.info("Successfully completed the candidates listed on the announcement message.")

    announce_message = announce_message + "\nTo vote, send this command to GCHQBot: " \
                                          "`{0}vote_for <first_choice> <second_choice> <last_choice>`. " \
                                          "Please understand that while the choice names are not case sensitive, " \
                                          "they __**must be in order and must be spelt the same way, spaces split up " \
                                          "your votes**__.\n\nHere's an example of its use: " \
                                          "`{0}vote_for Freddie Kim_Jong-Un Mao`, here you are voting for Freddie " \
                                          "as your first choice, Lil' Kimmy as your second and Mao as your last " \
                                          "choice.".format(cmd_prefix)

    vote_storage = {"counts": {}, "votes": {}}

    for candidate in candidate_list:
        vote_storage["counts"][candidate.lower()] = 0

    logger.info("Set up dictionary for holding vote count information.")

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

    target_announce_channel = await commands.TextChannelConverter().convert(ctx, "355070253643988992")

    await target_announce_channel.send(announce_message)


@bot.command(name="colourme")
async def colour_me(ctx, colour_hex: str):
    """Gives the command invoker a custom colour role if they satisfy given conditions.
    If colour_hex is given as remove, the bot will remove the colour role and exit the
    operation.
    """

    # Preprocess the colour
    if colour_hex.lower() == "remove":
        for arole in ctx.author.roles:
            if "GCHQ[0x" in arole.name:
                await ctx.author.remove_roles(arole, reason="User requested colour role removal.")

        await clean_colour_roles(ctx.guild)
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
                           f"such that they are {math.ceil(exclusion_range/2)} away from the protected colour.")
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

    await clean_colour_roles(ctx.guild)


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
logger.info("Starting bot process.")
bot.run(b_token)
