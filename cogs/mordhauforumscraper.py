from bs4 import BeautifulSoup
from discord.ext import commands
from datetime import datetime
import aiohttp
from pymongo import DESCENDING, ASCENDING
import threading


class MordhauForumScraper(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.scraping = False

    async def cog_check(self, ctx):
        # check whether ctx server is in list of "botservers" in config
        if not ctx.guild or str(ctx.guild.id) not in dict(self.bot._cfg.items('botservers')).values():
            return False
        if await self.bot._db['admins'].find_one({"id": ctx.author.id}):
            # check if author is admin
            return True
        if ctx.author.permissions_in(ctx.channel).administrator and str(ctx.guild.id) in dict(
                self.bot._cfg.items('serveradmins')).values():
            # check whether servers admins are allowed and whether author is an admin
            return True
        await ctx.send('no')
        return False

    async def remove_quotes(self, soup):
        "Remove quotes"
        for child in soup.find_all('blockquote'):
            child.decompose()


    async def remove_polls(self, soup):
        "Remove polls"
        for child in soup.find_all(class_='comment-poll'):
            child.decompose()

    async def comment_to_db(self, comment, comment_id):
        "Parse the html for each comment and add relevant information to the db"
        if await self.bot._db['mordhauforum'].find_one({"comment_id": comment_id}):
            return # this comment is already added to the db
        try:
            user_id = int(comment.find(class_='username').get('href').split('/')[3])
            content = comment.find(class_='comment-text').get_text().strip()
            user_name = comment.find(class_='username').get_text().strip()
            timestamp = comment.find(class_='comment-date').find(class_='text-muted').get('data-date')[:-6]
            timestamp = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S.%f")
            #print(timestamp, comment_id, user_id, user_name, content)
            self.bot._db['mordhauforum'].insert_one({"comment_id": comment_id, "author_name": user_name, "user_id": user_id, "timestamp": timestamp,
                               "content": content})
        except:
            #print(f"Comment {comment_id} is invalid")
            return

    async def process_page(self, comment_id):
        """Each comment links to the threadpage it is posted in, process all comments in this threadpage
        Returns response status"""
        soup = await self.soup_from_page(comment_id)
        if soup is None:
            return
        comments = soup.find_all(class_='comment')
        for comment in comments:
            comment_id = int(comment.get('data-pk'))
            if comment_id >= comment_id:
                await self.comment_to_db(comment, comment_id)

    async def process_single_comment(self, comment_id):
        "In a forumpage, find the comment matching the comment_id and add it to the db"
        soup = await self.soup_from_page(comment_id)
        if soup is None:
            return 404
        comment = soup.find(class_="comment", attrs={"data-pk": str(comment_id)})
        await self.comment_to_db(comment, comment_id)

    async def soup_from_page(self, comment_id):
        """Return soup of a forumpage containing the comment with the given comment_id"""
        base_url = "https://mordhau.com/forum/comment/"
        async with aiohttp.ClientSession() as session:
            async with session.get(base_url + str(comment_id) + '/find') as response:
                if response.status != 200:
                    return None
                comment_html = await response.text()
        soup = BeautifulSoup(comment_html, 'html.parser')
        await self.remove_quotes(soup)
        await self.remove_polls(soup)
        return soup

    async def update_message_counts(self):
        "Store message count in a seperate DB collection"
        newdict = {}
        for forum in self.bot._cfg.get("scrapeforums", "forums", fallback=["mordhauforum"]).split(','):
            agg = self.bot._db[forum].aggregate([{"$group": {"_id": "$user_id", "count": {"$sum": 1}}}])
            async for x in agg:
                if x['_id'] in newdict:
                    newdict[x['_id']] += x['count']
                else:
                    newdict[x['_id']] = x['count']
        for user_id, messagecount in newdict.items():
            if await self.bot._db['statistics'].find_one({"user_id": user_id}):
                await self.bot._db['statistics'].update_one({"user_id": user_id}, {
                    "$set": {"messagecount": messagecount, "discord": False}})
            else:
                await self.bot._db['statistics'].insert_one(
                    {"user_id": user_id, "messagecount": messagecount, "discord": False})

    @commands.command(name="mordhauscrape")
    async def scrape(self, ctx):
        """Look for comment_id with highest value in the db, start scraping from that point on.
        Process comments one by one, ignoring the rest of the forumpage that the comment is on """
        if self.scraping:
            await ctx.send("already scraping forums")
            return
        self.scraping = True
        try:
            async for x in self.bot._db['mordhauforum'].find().sort("comment_id", DESCENDING).limit(1):
                start = int(x['comment_id'])
            print(f"Starting mordhauforum scrape, start={start}")
            error_buffer = 0
            error_max = 100
            i = start
            while (error_buffer < error_max):
                response = await self.process_single_comment(i)
                if response == 404:
                    error_buffer += 1
                else:
                    error_buffer = 0
                if i% 50 == 0:
                    print(f"i = {i}")
                i += 1
            print("Done looping")
            await self.update_message_counts()
            print("Done updating message counts")
            await ctx.send("done scraping forums")
            self.scraping = False
        except:
            self.scraping = False
            print("something went wrong during forum scrape")


def setup(bot):
    bot.add_cog(MordhauForumScraper(bot))
