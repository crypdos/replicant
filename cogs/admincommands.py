import discord
from discord.ext import commands
from urllib.request import Request, urlopen
from datetime import datetime
from utils.customerrors import NotEnoughMessages, AlreadyScraping
import utils.customconverters as customconverters
from utils.helpers import username_from_db, count_documents
import utils.checks as checks

class AdminCommands:

    def __init__(self, bot):
        self.bot = bot
        self.password = self.bot._cfg['discord']['password']
        assert isinstance(bot, commands.Bot)

    async def __local_check(self, ctx):
        # check whether ctx server is in list of "botservers" in config
        if not ctx.guild or str(ctx.guild.id) not in dict(self.bot._cfg.items('botservers')).values():
            return False
        if await self.bot._db['admins'].find_one({"id" : ctx.author.id}):
            # check if author is admin
            return True
        if ctx.author.permissions_in(ctx.channel).administrator and str(ctx.guild.id) in dict(self.bot._cfg.items('serveradmins')).values():
            #check whether servers admins are allowed and whether author is an admin
            return True
        await ctx.send('no')
        return False

    @commands.command()
    async def off(self, ctx):
        self.bot.unload_extension('cogs.commands')
        await ctx.send('turned off')

    @commands.command()
    async def on(self, ctx):
        self.bot.load_extension('cogs.commands')
        await ctx.send('turned on')

    @checks.avatarcd()
    @commands.command(aliases=['copy'])
    async def replicate(self, ctx, target: customconverters.GlobalUser):
        cutoff = self.bot._cfg.getint("settings", "msgcutoff", fallback=1000)
        usermsgcount = await count_documents(ctx, target.id)
        if usermsgcount < cutoff:
            raise NotEnoughMessages(target.name, usermsgcount, cutoff)
        else:
            await ctx.send(f"replicating {target.name} ({usermsgcount} messages)")
        await ctx.invoke(self.bot.get_command('model'), target.id)
        await ctx.invoke(self.bot.get_command('setavatar'), target)
        member = ctx.guild.get_member_named(target.name + "#" + target.discriminator)
        if member and member.nick:
            await ctx.invoke(self.bot.get_command('setnickname'), member.nick)
        else:
            await ctx.invoke(self.bot.get_command('setnickname'), target.name)

    @commands.command(name="model", aliases=['create_model'])
    async def create_model(self, ctx, userid: customconverters.UserID):
        username = await username_from_db(ctx, userid)
        if not username:
            username = "unknown"
        await self.bot._model.createModel(userid, username)
        await ctx.send(f"hi it's me {username} 😃 ")

    @commands.command(name="scrape")
    async def scrape(self, ctx):
        if self.bot._scraper.scraping:
            raise AlreadyScraping
        lastscrapedoc = await self.bot._db['scrapetime'].find_one({"special": True})
        if lastscrapedoc:
            lastscrape = datetime.strftime(lastscrapedoc['lastscrape'], "%d %B %H:%M")
        else:
            lastscrape = "idk"
        await ctx.send(f"updating db, scraping new messages since {lastscrape}")
        scraped = await self.bot._scraper.start_scrape()
        totalusers = await self.bot._db['statistics'].estimated_document_count()
        await ctx.send(f"{scraped} new messages added, {totalusers} users in db")

    @commands.command(name="setnickname", aliases=["changenickname"])
    async def change_nickname(self, ctx, nickname : str):
        for (coll, serverid) in self.bot._cfg.items('botservers'):
            guild = self.bot.get_guild(int(serverid))
            await guild.me.edit(nick=nickname)

    @checks.avatarcd()
    @commands.command(name='setavatar', aliases=['copyavatar'])
    async def copy_avatar(self, ctx, target : customconverters.GlobalUser):
        url = target.avatar_url_as(format='png')
        req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        avatarimage = urlopen(req).read()
        try:
            await self.bot.user.edit(password=self.password, avatar=avatarimage)
        except discord.HTTPException:
            # ratelimited by discord API, removing the last token because this function didn't complete successfully
            # ideally reaching this point should've been prevented by the avatarcd check
            self.bot._avatarcd._cooldown._tokens += 1
            await ctx.send("couldn't change avatar because of discord API ratelimit")

def setup(bot):
    bot.add_cog(AdminCommands(bot))