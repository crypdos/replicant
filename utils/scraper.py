from discord.ext import commands
from datetime import datetime
from utils.customerrors import AlreadyScraping

class Scraper:
    def __init__(self, bot):
        self.bot = bot
        assert isinstance(bot, commands.Bot)
        self.scraping = False

    async def start_scrape(self):
        if self.scraping:
            raise AlreadyScraping
        self.scraping = True
        total=0
        for (coll, serverid) in self.bot._cfg.items('scrapeservers'):
            server = self.bot.get_guild(int(serverid))
            if server:
                channels = server.text_channels
                for channel in channels:
                    if server.me.permissions_in(channel).read_message_history:
                        total += await self.scrape_channel(channel, self.bot._db[coll])
        if await self.bot._db['scrapetime'].find_one({"special" : True}):
            await self.bot._db['scrapetime'].update_one({"special": True}, {"$set": {"lastscrape": datetime.utcnow()}})
        else:
            await self.bot._db['scrapetime'].insert_one({"special": True, "lastscrape": datetime.utcnow()})

        print("-------------------------------")
        print("Finished scraping all channels!\nNow updating statistics")
        await self.update_statistics()
        print("Finished updating statistics")
        self.scraping = False
        return total


    async def scrape_channel(self, channel, coll):
        print(f"Scraping logs from channel {channel.name}")

        lastscrapedoc = await self.bot._db['scrapetime'].find_one({'channel_id': channel.id}, {'_id':0, 'lastscrape':1})
        if lastscrapedoc:
            last = lastscrapedoc['lastscrape']
            print(f"Scraping messages after {last}")
        else:
            last = channel.created_at
            print(f"Scraping since creation date of channel: {last}")

        total = 0
        while True:
            docs = []

            async for message in channel.history(limit=500, after=last):
                docs.append({
                    'id': message.id,
                    'timestamp': message.created_at,
                    'edited_timestamp': message.edited_at,
                    'author_id': message.author.id,
                    'author_name': message.author.name,
                    'content': message.content
                })
            if len(docs) == 0:
                break
            total += len(docs)
            last = docs[-1].get("timestamp")

            if not await coll.find_one({"id": docs[0]['id']}): # check for duplicates
                await coll.insert_many(docs)
            else:
                for doc in docs:
                    if not await coll.find_one({"id": doc['id']}):
                        await coll.insert_one(doc)

            if await self.bot._db['scrapetime'].find_one({'channel_id': channel.id}): #update scrapetime in db for channel
                await self.bot._db['scrapetime'].update_one({'channel_id':channel.id}, {"$set": {"lastscrape" : last}})
            else:
                await self.bot._db['scrapetime'].insert_one({'channel_name': channel.name, 'channel_id': channel.id, 'lastscrape': last})

            print(f"{total} messages scraped")
        print(f"Done scraping messages for channel {channel.name}")
        return total

    async def update_statistics(self):
        newdict = {}
        for (coll, serverid) in self.bot._cfg.items('scrapeservers'):
            agg = self.bot._db[coll].aggregate([{"$group": {"_id": "$author_id", "count": {"$sum": 1}}}])
            async for x in agg:
                if x['_id'] in newdict:
                    newdict[x['_id']] += x['count']
                else:
                    newdict[x['_id']] = x['count']
        for authorid, messagecount in newdict.items():
            if await self.bot._db['statistics'].find_one({"author_id" : authorid}):
                await self.bot._db['statistics'].update_one({"author_id" : authorid}, {"$set": {"messagecount": messagecount}})
            else:
                await self.bot._db['statistics'].insert_one({"author_id" : authorid, "messagecount": messagecount})

