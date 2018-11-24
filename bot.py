import discord
from discord.ext import commands
import traceback
import configparser
from motor import motor_asyncio
from utils.textmodel import TextModel
from utils.scraper import Scraper
from os import listdir
from os.path import isfile, join
import utils.checks as checks

if not isfile("config.ini"):
    print("No config.ini file found! Exiting")
    raise SystemExit

cfg = configparser.ConfigParser()
cfg.read('config.ini')
token = cfg.get('discord', 'token')
password = cfg.get('discord', 'password', fallback="")
prefix = cfg.get('discord', 'commandprefix', fallback="?")

mongoserver = cfg.get("mongodb", "server", fallback="localhost")
mongoport = cfg.getint("mongodb", "port", fallback=27017)
mongodatabase = cfg.get("mongodb", "database", fallback="discord")
mongotimeout = cfg.getint("mongodb", "timeout", fallback=10000)
motorclient = motor_asyncio.AsyncIOMotorClient(mongoserver, mongoport, serverSelectionTimeoutMS=mongotimeout)

bot = commands.Bot(command_prefix=prefix)
bot.owner_id = cfg.getint("discord", "ownerid")
bot.remove_command('help')

# pass attributes to bot instance
bot._db = motorclient[mongodatabase]
bot._cfg = cfg
bot._model = TextModel(bot)
bot._scraper = Scraper(bot)
bot._avatarcd = commands.CooldownMapping.from_cooldown(2, 10*60, commands.BucketType.default)
bot._votecd = commands.CooldownMapping.from_cooldown(1, 10*60, commands.BucketType.default)

cogs_dir = "cogs"
# load all cogs in cogs_dir
async def load_cogs():
    for extension in [f.replace('.py', '') for f in listdir(cogs_dir) if isfile(join(cogs_dir, f))]:
        try:
            bot.load_extension(cogs_dir + "." + extension)
        except (discord.ClientException, ModuleNotFoundError):
            print(f'Failed to load extension {extension}.')
            traceback.print_exc()

async def checkMongo():
    try:
        await motorclient.admin.command('ismaster')
        print("Successfully connected to mongodb")
    except Exception:
        print("Could not connect to mongodb, check server settings or consider increasing the timeout value.")

@bot.event
async def on_ready():
    print(f"Logged in to discord as {bot.user.name} with userid {bot.user.id}")
    print(f"discord.py version {discord.__version__}")
    print("Loading cogs ... ", end='')
    await load_cogs()
    print("successfully loaded all cogs")
    await checkMongo()
    print("Ready")

@checks.is_owner()
@bot.command(hidden=True)
async def reload(ctx):
    cfg.read('config.ini')
    for extension in [f.replace('.py', '') for f in listdir(cogs_dir) if isfile(join(cogs_dir, f))]:
        try:
            bot.unload_extension(cogs_dir + "." + extension)
        except (discord.ClientException, ModuleNotFoundError):
            print(f'Failed to unload extension {extension}.')
            traceback.print_exc()
    await load_cogs()
    print("Reloaded all cogs")
    await ctx.send('\N{OK HAND SIGN}')


if cfg.get('discord', 'userbot', fallback="no").lower() == "yes":
    bot.run(token, reconnect=True, bot=False)
else:
    bot.run(token, reconnect=True)
