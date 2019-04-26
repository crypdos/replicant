from discord.ext import commands
import re
import discord


class UserID(commands.IDConverter):
    async def convert(self, ctx, argument):
        match = self._get_id_match(argument) or re.match(r'<@!?([0-9]+)>$', argument)
        result = None
        state = ctx._state

        if match is not None:
            user_id = int(match.group(1))
            result = await ctx.bot.fetch_user(user_id)
            # this is changed from the default class, allows getting users outside the global message cache
        else:
            arg = argument
            # check for discriminator if it exists
            if len(arg) > 5 and arg[-5] == '#':
                discrim = arg[-4:]
                name = arg[:-5]
                predicate = lambda u: u.name == name and u.discriminator == discrim
                result = discord.utils.find(predicate, state._users.values())
                if result is not None:
                    return result.id

            predicate = lambda u: u.name == arg
            result = discord.utils.find(predicate, state._users.values())

        if result is None: # if userid is not found by this point, try looking for ID in database
            for (coll, serverid) in ctx.bot._cfg.items('scrapeservers'):
                doc = await ctx.bot._db[coll].find_one({"author_id": user_id})
                if doc:
                    return doc['author_id']
            raise commands.BadArgument('User "{}" not found'.format(argument))

        return result.id

class GlobalUser(commands.IDConverter):
    """Converts to a :class:`User`.
    The lookup strategy is as follows (in order):
    1. Lookup by ID.
    2. Lookup by mention.
    3. Lookup by name#discrim
    4. Lookup by name
    """
    async def convert(self, ctx, argument):
        match = self._get_id_match(argument) or re.match(r'<@!?([0-9]+)>$', argument)
        result = None
        state = ctx._state

        if match is not None:
            user_id = int(match.group(1))
            result = await ctx.bot.fetch_user(user_id)
        else:
            arg = argument
            # check for discriminator if it exists
            if len(arg) > 5 and arg[-5] == '#':
                discrim = arg[-4:]
                name = arg[:-5]
                predicate = lambda u: u.name == name and u.discriminator == discrim
                result = discord.utils.find(predicate, state._users.values())
                if result is not None:
                    return result

            predicate = lambda u: u.name == arg
            result = discord.utils.find(predicate, state._users.values())

        if result is None:
            raise commands.BadArgument('User "{}" not found'.format(argument))

        return result