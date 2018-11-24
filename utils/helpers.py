import re


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
