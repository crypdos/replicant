import re
import aiohttp
import asyncio

async def clean_content(ctx, message):
    p = re.compile("\<\D{1,2}(\d*)\>")
    for x in p.finditer(message): #replace mentions
        try:
            user = await ctx.bot.get_user_info(int(x.group(1)))
            username = user.name
        except (TypeError, AttributeError):
            username = "unknown_user"
        message = message.replace(x.group(0), '@' + username)

    message = message.replace('@everyone', "\@everyone")
    message = message.replace("@here", "\@here")
    return message

async def count_documents(ctx, userid):
    total=0
    for (coll, serverid) in ctx.bot._cfg.items('scrapeservers'):
        total += await ctx.bot._db[coll].count_documents({"author_id": userid})
    return total

async def username_from_db(ctx, userid):
    user = await ctx.bot.get_user_info(userid)
    if user:
        return user.name
    for (coll, serverid) in ctx.bot._cfg.items('scrapeservers'):
        doc = await ctx.bot._db[coll].find_one({"author_id" : userid})
        if doc:
            return doc['author_name']
    return None

async def userid_in_db(ctx, userid):
    for (coll, serverid) in ctx.bot._cfg.items('scrapeservers'):
        doc = await ctx.bot._db[coll].find_one({"author_id" : userid})
        if doc:
            return doc['author_id']
    return None

async def accept_invite(ctx, invitestring):
    invite = re.search(r'discord.gg\/(\S*)', invitestring).group(1)
    botToken = ctx.bot._cfg['discord']['token']
    url = f"https://discordapp.com/api/v6/invite/{invite}"
    headers = {"Authorization": f"{botToken}",
               "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36"}
    async with aiohttp.ClientSession() as session:
        with aiohttp.Timeout(10):
            return await session.post(url, headers=headers)
