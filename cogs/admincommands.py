import discord
from discord.ext import commands
from datetime import datetime
from utils.customerrors import NotEnoughMessages, AlreadyScraping
import utils.customconverters as customconverters
from utils.helpers import username_from_db, count_documents, forum_id_from_name
import utils.checks as checks
import aiohttp
from bs4 import BeautifulSoup

class AdminCommands(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.password = self.bot._cfg['discord']['password']
        assert isinstance(bot, commands.Bot)

    async def cog_check(self, ctx):
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
        self.bot.unload_extension('cogs.votecommand')
        await ctx.send('turned off')

    @commands.command()
    async def on(self, ctx):
        self.bot.load_extension('cogs.commands')
        self.bot.load_extension('cogs.votecommand')
        await ctx.send('turned on')

    @checks.avatarcd()
    @commands.command(aliases=['copy'])
    async def replicate(self, ctx, target: customconverters.GlobalUser):
        cutoff = self.bot._cfg.getint("settings", "msgcutoff", fallback=1000)
        usermsgcount = await count_documents(ctx, target.id)
        if usermsgcount < cutoff:
            raise NotEnoughMessages(target.name, usermsgcount, cutoff)
        await ctx.invoke(self.bot.get_command('setavatar'), target)
        member = ctx.guild.get_member_named(target.name + "#" + target.discriminator)
        if member and member.nick:
            await ctx.invoke(self.bot.get_command('setnickname'), member.nick)
        else:
            await ctx.invoke(self.bot.get_command('setnickname'), target.name)
        await ctx.invoke(self.bot.get_command('model'), target)

    @commands.command(name="model", aliases=['create_model'])
    async def create_model(self, ctx, target: customconverters.GlobalUser):
        cutoff = self.bot._cfg.getint("settings", "msgcutoff", fallback=1000)
        usermsgcount = await count_documents(ctx, target.id)
        if usermsgcount < cutoff:
            raise NotEnoughMessages(target.name, usermsgcount, cutoff)
        else:
            await ctx.send(f"replicating {target.name} ({usermsgcount} messages)")
        await self.bot._model.create_discord_model(target.id, target.name)
        await ctx.send(f"hi it's me {target.name} 😃 ")

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
        url = str(target.avatar_url_as(format='png'))
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                assert response.status == 200
                avatarimage = await response.read()
        try:
            await self.bot.user.edit(password=self.password, avatar=avatarimage)
        except discord.HTTPException:
            # ratelimited by discord API, removing the last token because this function didn't complete successfully
            # ideally reaching this point should've been prevented by the avatarcd check
            self.bot._avatarcd._cooldown._tokens += 1
            await ctx.send("couldn't change avatar because of discord API ratelimit")

    @checks.avatarcd()
    @commands.command(name='forumavatar')
    async def copy_forum_avatar(self, ctx, f_user: customconverters.ForumUser):
        base_url = str("http://www.mordhau.com/forum/user/")
        url = base_url + str(f_user.id)
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    return None
                comment_html = await response.text()
        soup = BeautifulSoup(comment_html, 'html.parser')
        avatar_url = soup.find(class_="profile-avatar").get('src')
        async with aiohttp.ClientSession() as session:
            async with session.get(avatar_url) as response:
                assert response.status == 200
                avatarimage = await response.read()
        try:
            await self.bot.user.edit(password=self.password, avatar=avatarimage)
        except discord.HTTPException:
            # ratelimited by discord API, removing the last token because this function didn't complete successfully
            # ideally reaching this point should've been prevented by the avatarcd check
            self.bot._avatarcd._cooldown._tokens += 1
            await ctx.send("couldn't change avatar because of discord API ratelimit")

    @commands.command(name="forummodel")
    async def forum_create_model(self, ctx, f_user: customconverters.ForumUser):
        cutoff = self.bot._cfg.getint("settings", "forumcutoff", fallback=50)
        if f_user.messages < cutoff:
            raise NotEnoughMessages(f_user.name, f_user.messages, cutoff)
        else:
            await ctx.send(f"replicating {f_user.name} ({f_user.messages} posts)")
        await self.bot._model.create_forum_model(f_user.id, f_user.name)
        await ctx.send(f"hi it's me {f_user.name} 😃 ")

    @commands.command(name="forumcopy", aliases = ["forumreplicate"])
    async def forum_replicate(self, ctx, f_user: customconverters.ForumUser):
        cutoff = self.bot._cfg.getint("settings", "forumcutoff", fallback=50)
        if f_user.messages < cutoff:
            raise NotEnoughMessages(f_user.name, f_user.messages, cutoff)
        await ctx.invoke(self.bot.get_command('forumavatar'), f_user)
        await ctx.invoke(self.bot.get_command('setnickname'), f_user.name)
        await ctx.invoke(self.bot.get_command('forummodel'), f_user)


def setup(bot):
    bot.add_cog(AdminCommands(bot))