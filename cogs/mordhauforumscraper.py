from bs4 import BeautifulSoup
from discord.ext import commands
from datetime import datetime
import aiohttp
import threading

class MordhauForumScraper:

    def __init__(self, bot):
        self.bot=bot

    async def remove_quotes(self, ctx, soup):
        "Remove quotes"
        for child in soup.find_all('blockquote'):
            child.decompose()


    async def remove_polls(self, ctx, soup):
        "Remove polls"
        for child in soup.find_all(class_='comment-poll'):
            child.decompose()


    async def comment_to_db(self, ctx, comment):
        "Parse the html for each comment and add relevant information to the db"
        comment_id = int(comment.get('data-pk'))
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



    async def process_page(self, ctx, comment_id):
        """Each comment links to the threadpage it is posted in, process all comments in this threadpage
        Returns response status"""
        base_url = "https://mordhau.com/forum/comment/"
        async with aiohttp.ClientSession() as session:
            async with session.get(base_url + str(comment_id) + '/find') as response:
                if response.status != 200:
                    return response.status
                comment_html = await response.text()
        soup = BeautifulSoup(comment_html, 'html.parser')
        await self.remove_quotes(ctx, soup)
        await self.remove_polls(ctx, soup)
        comments = soup.find_all(class_='comment')
        for comment in comments:
            if int(comment.get('data-pk')) >= comment_id:
                await self.comment_to_db(ctx, comment)
        return response.status


    @commands.command(name="mordhauscrape")
    async def scrape(self, ctx, i : int = 0):
        print(f"Starting mordhauforum scrape, i={i}")
        error_buffer = 0
        #i = 37100
        #max = 187272
        while error_buffer < 100:
            response = await self.process_page(ctx, i)
            if response != 200:
                error_buffer += 1
            elif error_buffer > 0:
                error_buffer -= 1
            if i% 50 == 0:
                print(f" i = {i}")
            i += 1
        print(f"Done looping, error buffer = {error_buffer}")



def setup(bot):
    bot.add_cog(MordhauForumScraper(bot))
