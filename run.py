import logging
from discord.ext import commands
import discord
import asyncio
import os
import sys
import json
import random

print("Assigning variables...")
b_token = "bot token goes here"
cmd_prefix = "!"
bot = commands.Bot(command_prefix=cmd_prefix)
owner_id = "Your discord account ID"
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
             "weeaboo":             "🎌Weeaboo🎌",
             "hearthstone":         "Hearthstone",
             "purple":              "Purple",
             "blue":                "Blue",
             "green":               "Green",
             "yellow":              "Yellow",
             "orange":              "Orange",
             "red":                 "Red",
             "irradiated_green":    "Irradiated Green",
             "pingable":            "Pingrole"}

role_list = ["pingable", "soton", "uea", "cymru", "exeter", "leeds",
             "manchester", "liverpool", "surrey", "bristol", "nottingham", "weeaboo", "hearthstone",
             "purple", "blue", "green", "yellow", "orange", "red", "irradiated_green"]

colour_list = ["purple", "blue", "green", "yellow", "orange", "red", "irradiated_green"]

parsed_role_list_text = ""
for name in role_list:
    parsed_role_list_text = parsed_role_list_text+"\n- "+name

if not os.path.exists("./logs/"):
    os.mkdir("./logs/")
    print("Created ./logs/ folder for file based logging.")


@bot.event
async def on_ready():
    # Any crap that needs to be done on startup can go here.
    logger.info("Bot process ready!")
    logger.info("Welcome to GCHQ Bot, for all your data harvesting needs.")


@bot.event
async def on_message(received_message):
    # Fill the empty strings with the IDs of channels that you want GCHQBot to respond to.
    if received_message.channel.id == "" or received_message.channel.id == "" or \
            received_message.channel.id == "":
        if received_message.content.startswith(cmd_prefix) and received_message.author != bot.user:
            logger.info('{0.author} sent the command: "{0.content}" in "{0.channel}" on the server "{0.server}".'
                        .format(received_message))
            await asyncio.sleep(0.5)
            await bot.process_commands(received_message)
        else:
            return
    elif received_message.server is None:  # Indicates a private message
        if received_message.content.startswith(cmd_prefix) and received_message.author != bot.user:
            logger.info('{0.author} sent the command: "{0.content}" in "{0.channel}".'.format(received_message))
            await asyncio.sleep(0.5)
            await bot.process_commands(received_message)
    else:
        return


@bot.event
async def on_member_join(member):
    logger.info("{} has joined the server.".format(member))
    await bot.send_message(member, 'Welcome to GCHQ, this bot will provide commands allowing you to gain access to'
                                   'hidden text channels in the GCHQ server, use `{0}help` to see commands.'
                                   '\n\nTo see how role based commands work use: `{0}help role`.'
                           .format(cmd_prefix))
    pingrole_obj = discord.utils.get(member.server.roles, name="Pingrole")
    await asyncio.sleep(120) # The server this bot is used on has a 10 minute wait period before you can talk, this enforces it.
    await bot.add_roles(member, pingrole_obj)
    logger.info("Successfully messaged and added new user to Pingrole.")


@bot.group(pass_context=True)
async def role(ctx):
    '''Role is a command group that houses the common use role commands like: "role get" and "role lose".'''
    if ctx.invoked_subcommand is None:
        logger.info("Command: {0.content} from user {0.author} had no subcommand.".format(ctx.message))
        await bot.reply("You need to include a subcommand with this one, use `{}help role` if you need further "
                        "assistance.".format(cmd_prefix))


@role.command(pass_context=True)
async def get(ctx, req_role=""):
    '''Get the bot to give you a chosen role'''
    try:
        req_role = req_role.lower()
    except TypeError:
        pass
    if req_role not in role_dict.keys():
        await bot.reply("You need to include a valid role id in this subcommand, use `{}role list` to see them."
                        .format(cmd_prefix))
        return

    target_role_object = discord.utils.get(ctx.message.server.roles, name=role_dict[req_role])
    target_user_object = ctx.message.author

    if req_role in colour_list:
        logger.info("User requested colour role, generating object list and checking ownership.")
        colour_role_objects = []
        for individual_role in ctx.message.server.roles:
            if individual_role.name.lower() in colour_list:
                colour_role_objects.append(individual_role)
        await asyncio.sleep(0.2)
        for colour_role in colour_role_objects:
            if colour_role in target_user_object.roles:
                logger.info("User already owns a colour role, removing said role now.")
                await bot.reply("You already have the role: {}, it will be removed.".format(colour_role))
                role_to_remove = discord.utils.get(ctx.message.server.roles, name=colour_role.name)
                await bot.remove_roles(target_user_object, role_to_remove)
                logger.info("Removed the role {0} from user: {1}.".format(role_to_remove, target_user_object))
        await asyncio.sleep(0.2)

    if target_role_object in target_user_object.roles:
        await bot.reply("You already have the requested role, to remove a role use: `{}role lose <role>`."
                        .format(cmd_prefix))
        return

    logger.info('Now attempting to add {} to the role: "{}".'.format(ctx.message.author, role_dict[req_role]))
    await bot.add_roles(target_user_object, target_role_object)
    logger.info('Addition of {} to role: "{}" completed successfully.'.format(ctx.message.author, role_dict[req_role]))
    await bot.reply("You have been added to the group: "+role_dict[req_role])


@role.command(pass_context=True)
async def lose(ctx, req_role=""):
    '''Get the bot to take away one of your roles.'''
    try:
        req_role = req_role.lower()
    except TypeError:
        pass
    if req_role not in role_dict.keys():
        await bot.reply("You need to include a valid role id in this subcommand, use `{}role list` to see them."
                        .format(cmd_prefix))
        return

    target_role_object = discord.utils.get(ctx.message.server.roles, name=role_dict[req_role])
    if target_role_object not in ctx.message.author.roles:
        await bot.reply("You don't have the requested role, to add a role use: `{}role get <role>`.".format(cmd_prefix))
        return

    logger.info('Now attempting to remove {} from the role: "{}".'.format(ctx.message.author, role_dict[req_role]))
    await bot.remove_roles(ctx.message.author, target_role_object)
    logger.info('Removal of {} from role: "{}" completed successfully.'.format(ctx.message.author, role_dict[req_role]))
    await bot.reply("You have been removed from the group: "+role_dict[req_role])


@role.command(name="list")
async def list_roles():
    '''Lists the currently working roles that the bot can give/take.'''
    await bot.say("Role list:\n```\n{}```\nTo use these role names, simply type: `{}role get <role>` in this channel."
                  .format(parsed_role_list_text, cmd_prefix))


@bot.command(pass_context=True)
async def stop_process(ctx):
    if ctx.message.author.id == owner_id:
        await bot.say(":wave:")
        await bot.logout()
        logger.warning("Bot has now logged out and is shutting down!")
        sys.exit()
    else:
        logger.warning("User: {} attempted to shut the bot down but doesn't have correct permissions! E.0001"
                       .format(ctx.message.author))
        return


@bot.command(pass_context=True)
async def vote_for(ctx, first_choice="", second_choice="", last_choice=""):
    '''Used for special votes configured by bot owner, usage example: !vote_for Freddie Kim_Jong-Un Mao.'''

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

    vote_file_in_use = True
    vote_file_queue.pop(0)

    votes = []

    votes.append(first_choice)
    votes.append(second_choice)
    votes.append(last_choice)

    if votes[0] == votes[1] or votes[1] == votes[2] or votes[2] == votes[0]:
        await bot.say("You have attempted to vote for the same person more than once.")
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
    if ctx.message.author.name+"#"+ctx.message.author.discriminator in have_voted:
        await bot.say("You have already voted in this election, please do not attempt to vote.")
        vote_file_in_use = False
        logger.info("User attempted to vote twice.")
        return

    valid_vote_targets = []

    for key, value in vote_data["counts"].items():
        valid_vote_targets.append(key)

    for key in votes:  # ensures all vote targets are valid and handles if it's not.
        if key.lower() not in valid_vote_targets:
            await bot.say("One or more of your votes are on invalid targets, check the main message for valid "
                          "candidates and try again.")
            logger.info("User failed to select all valid candidates in their vote.")
            vote_file_in_use = False
            return

    try:
        vote_data["counts"][first_choice.lower()] += 10
        vote_data["counts"][second_choice.lower()] += 5
        vote_data["counts"][last_choice.lower()] -= 5
    except NameError:
        await bot.say("One or more of your votes are on invalid targets, check the main message for valid "
                      "candidates and try again.")
        logger.info("User failed to select all valid candidates in their vote.")
        vote_file_in_use = False
        return

    vote_data["votes"]["{0.name}#{0.discriminator}".format(ctx.message.author)] = votes

    with open("./active_votes/vote.json", "w") as json_votes:
        json.dump(vote_data, json_votes, indent=4)
        logger.info("Dumped vote data into file, opening up for next command.")

    vote_file_in_use = False
    await bot.say("Your votes have been registered, thank you for partaking in this incredible change to GCHQ's "
                  "political landscape.")


@bot.command(pass_context=True)
async def start_vote(ctx, candidate_list=""):
    if ctx.message.author.id != owner_id:
        logger.warning("User: {} attempted to shut the bot down but doesn't have correct permissions!"
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

    # I know this is bad, blame PEP 8
    announce_message = announce_message + "\nTo vote, send this command to GCHQBot: " \
                                          "`{0}vote_for <first_choice> <second_choice> <last_choice>`. " \
                                          "Please understand that while the choice names are not case sensitive, " \
                                          "they __**must be in order and must be spelt the same way, spaces split up " \
                                          "your votes**__.\n\nHere's an example of its use: " \
                                          "`{0}vote_for Freddie Kim_Jong-Un Mao`, here you are voting for Freddie " \
                                          "as your first choice, Lil' Kimmy as your second and Mao as your last " \
                                          "choice.".format(cmd_prefix)

    vote_storage = {}
    vote_storage["counts"] = {}
    for candidate in candidate_list:
        vote_storage["counts"][candidate.lower()] = 0

    vote_storage["votes"] = {}

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

    await bot.send_message(discord.Object(id='355070253643988992'), announce_message)

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
