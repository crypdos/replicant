from bs4 import BeautifulSoup
from discord.ext import commands
from datetime import datetime
import aiohttp
from pymongo import DESCENDING, ASCENDING
import threading


class MordhauForumScraper(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

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
            return
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

    @commands.command(name="mordhauscrape")
    async def scrape(self, ctx, start: int):
        # "Look for comment_id with highest value in the db, start scraping from that point on"
        # async for x in self.bot._db['mordhauforum'].find().sort("comment_id", DESCENDING).limit(1):
        #     start = int(x['comment_id'])

        """Process comments one by one, ignoring the rest of the forumpage that the comment is on"""
        print(f"Starting mordhauforum scrape, start={start}")
        end = 197677
        for i in range(start, end):
            await self.process_single_comment(i)
            if i% 50 == 0:
                print(f"i = {i}")
        print("Done looping")


def setup(bot):
    bot.add_cog(MordhauForumScraper(bot))
