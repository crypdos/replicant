import aiohttp
from bs4 import BeautifulSoup
import json
import re
from discord.ext import commands
from utils.checks import is_admin
import random
import time

ARCHIVE_URL = "https://www.hel-looks.com/archive/"
JSON_URL = "https://www.hel-looks.com/json/"
IMG_URL = "https://www.hel-looks.com/big-photos/"
RELATION_TIME = 10


class Hellooks(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.usercache = dict()  # found bf/gf needs to be remembered for each user for certain amount of time

    async def download_page(self, url):
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    raise aiohttp.ClientConnectionError
                return await response.text()

    @is_admin()
    @commands.command("hellooksupdate")
    async def scrape(self, ctx):
        await ctx.send("scraping hel-looks.com")
        print("scraping hel-looks.com")
        req = await self.download_page(ARCHIVE_URL)
        soup = BeautifulSoup(req, 'html.parser')
        imges = soup.find_all(class_="v")
        for div in imges:
            img = dict()  # make new dict containing cleaned key-value pairs
            img['name'] = div.get('n')
            # replace m and f by Male and Female + separated by comma and space
            img['gender'] = ', '.join(div.get('g')).replace("m", "Male").replace("f", "Female")
            img['link'] = IMG_URL + div.get('href').replace("#", '') + '.jpg'
            jsonreq = await self.download_page(JSON_URL + div.get('href').replace("#", '') + ".json")
            json_obj = json.loads(jsonreq)
            try:
                img['age'] = json_obj['poser0_age']
            except KeyError: # some imgs don't have age
                pass
            img['description'] = json_obj['description']
            img['description'] = re.sub('(\&.*?\;)','', img['description'])  # remove escaped characters
            img['description'] = re.sub('<.*?>', '', img['description'])   # remove html stuff between <>
            await self.to_db(img)
        await ctx.send("done scraping hel-looks.com")

    async def to_db(self, img):
        if await self.bot._db['hellooks'].find_one({"link" : img['link']}):  # already exists in db
            return
        self.bot._db['hellooks'].insert_one(img)  # img is a dict ready to be added to the db

    @commands.command("findbf")
    async def find_bf(self, ctx):
        authorid = ctx.message.author.id
        # check if user already has a bf, this gets cached for RELATION_TIME minutes in usercache,
        # if so return the same bf
        if authorid in self.usercache and 'bftime' in self.usercache[authorid] and (time.time() - \
                self.usercache[authorid]['bftime']) < (60 * RELATION_TIME):
            choice = await self.bot._db['hellooks'].find_one({"link": self.usercache[authorid]['bf']})
        else:
            men = self.bot._db['hellooks'].find({"gender": "Male"})
            menlist = await men.to_list(None)
            choice = random.choice(menlist)
            if authorid not in self.usercache:
                self.usercache[authorid] = dict()
            self.usercache[authorid]['bf'] = choice['link']
            self.usercache[authorid]['bftime'] = time.time()
        name_and_age = choice['name']
        if 'age' in choice:
            name_and_age += ', ' + choice['age']
        await ctx.send(f"{ctx.message.author.mention} {choice['link']}\n{name_and_age}\n\"{choice['description']}\"")

    @commands.command("findgf")
    async def find_gf(self, ctx):
        authorid = ctx.message.author.id
        # check if user already has a gf, this gets cached for RELATION_TIME minutes in usercache,
        # if so return the same gf
        if authorid in self.usercache and 'gftime' in self.usercache[authorid] and (time.time() - \
                self.usercache[authorid]['gftime']) < (60 * RELATION_TIME):
            choice = await self.bot._db['hellooks'].find_one({"link": self.usercache[authorid]['gf']})
        else:
            men = self.bot._db['hellooks'].find({"gender": "Female"})
            menlist = await men.to_list(None)
            choice = random.choice(menlist)
            if authorid not in self.usercache:
                self.usercache[authorid] = dict()
            self.usercache[authorid]['gf'] = choice['link']
            self.usercache[authorid]['gftime'] = time.time()
        name_and_age = choice['name']
        if 'age' in choice:
            name_and_age += ', ' + choice['age']
        await ctx.send(f"{ctx.message.author.mention} {choice['link']}\n{name_and_age}\n\"{choice['description']}\"")


def setup(bot):
    bot.add_cog(Hellooks(bot))