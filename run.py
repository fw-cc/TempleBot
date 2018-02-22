import logging
from discord.ext import commands
import discord
import asyncio
import os

b_token = "le toucan has arrived"
cmd_prefix = "!"
bot = commands.Bot(command_prefix=cmd_prefix)
owner_id = "is you"

role_dict = {"soton":       "Houthsampton (Soton)",
             "uea":         "UAE (Uni of East Anglia)",
             "cymru":       "The Cymru Cooperative (Swansea)",
             "exeter":      "Southest Westest WouthSest (Exeter)",
             "manchester":  "Wildlings 1 (Manchester)",
             "liverpool":   "Wildlings A (Liverpool)",
             "leeds":       "REEEEEEEEEDS (Leeds)",
             "surrey":      "Soorreey (Surrey)",
             "bristol":     "Brihstool (Bristol)",
             "weeaboo":     "🎌Weeaboo🎌",
             "purple":      "Purple",
             "blue":        "Blue",
             "green":       "Green",
             "yellow":      "Yellow",
             "orange":      "Orange",
             "red":         "Red",
             "pingable":    "Pingrole"}

role_list = ["pingable", "soton", "uea", "cymru", "exeter", "leeds",
             "manchester", "liverpool", "surrey", "bristol", "nottingham", "weeaboo",
             "purple", "blue", "green", "yellow", "orange", "red"]

parsed_role_list_text = ""
for name in role_list:
    parsed_role_list_text = parsed_role_list_text+"\n- "+name


@bot.event
async def on_ready():
    # Any crap that needs to be done on startup can go here.
    if not os.path.exists("./logs/"):
        os.mkdir("./logs/")
        logger.info("Created ./logs/ folder for file based logging.")
    logger.info("Bot process running.")
    logger.info("Welcome to GCHQ Bot, for all your data harvesting needs.")


@bot.event
async def on_message(received_message):
    if received_message.channel.id == "354774298172325893" or received_message.channel.id == "364799469130219521":
        if received_message.content.startswith(cmd_prefix) and received_message.author != bot.user:
            logger.info('{0.author} sent the command: "{0.content}" in "{0.channel}" on the server "{0.server}".'
                        .format(received_message))
            await asyncio.sleep(0.5)
            await bot.process_commands(received_message)


@bot.event
async def on_member_join(member):
    logger.info("{} has joined the server.".format(member))
    await bot.send_message(member, 'Welcome to GCHQ, this bot will provide commands allowing you to gain access to'
                                   'hidden text channels in the GCHQ server, use `{0}help` to see commands.'
                                   '\n\nTo see how role based commands work use: `{0}help role`.'
                           .format(cmd_prefix))
    pingrole_obj = discord.utils.get(member.server.roles, name="Pingrole")
    await bot.add_roles(member, pingrole_obj)
    logger.info("Successfully messaged and added new user to pingrole.")


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
        exit()
    else:
        logger.warning("User: {} attempted to shut the bot down but doesn't have correct permissions!"
                       .format(ctx.message.author))
        return


# Begin logging
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
