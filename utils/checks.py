from discord.ext import commands

def is_admin():
    async def predicate(ctx):
        return ctx.author.permissions_in(ctx.channel).administrator
    return commands.check(predicate)

def is_owner():
    async def predicate(ctx):
        ownerid = ctx.bot.owner_id
        if ctx.author.id == ownerid:
            return True
        else:
            await ctx.send("no")
    return commands.check(predicate)

def avatarcd():
    async def predicate(ctx, undo : str = None):
        if undo: # this gets called by errorhandler so that when a user is not found, the command doens't go on cooldown
            ctx.bot._avatarcd._cooldown._tokens += 1
            return True
        bucket = ctx.bot._avatarcd.get_bucket(ctx.message)
        retry_after = bucket.update_rate_limit()
        if retry_after:
            # rate limited
            minutes = round(retry_after / 60)
            await ctx.send(f"cd on avatarchange, wait {minutes} minutes")
            return False
        # not rate limited
        return True
    return commands.check(predicate)

def votecd():
    async def predicate(ctx, undo : str = None):
        if undo: # this gets called by errorhandler so that when a user is not found, the command doens't go on cooldown
            ctx.bot._avatarcd._cooldown._tokens += 1
            ctx.bot._votecd._cooldown._tokens += 1
            return True
        # check if there's a cooldown on avatarchange, then check if there's a cooldown on votecommand
        # only when this is succesful, add a token to avatarcd bucket to prevent putting it on cooldown for no reason
        avatarbucket = ctx.bot._avatarcd.get_bucket(ctx.message)
        votebucket = ctx.bot._votecd.get_bucket(ctx.message)
        if avatarbucket._tokens == 0:
            retry_after = avatarbucket.update_rate_limit()
            # rate limited
            # this needs fixing, sometimes retry_after = None
            minutes = round(retry_after / 60)
            await ctx.send(f"cd on avatar change, wait {minutes} minutes")
            return False
        else:
            retry_after = votebucket.update_rate_limit()
            if retry_after:
                # rate limited
                minutes = round(retry_after / 60)
                await ctx.send(f"cd on vote, wait {minutes} minutes")
                return False
            # not rate limited, remove 1 token to avatarbucket because vote function uses avatarchange
            avatarbucket.update_rate_limit()
            return True
    return commands.check(predicate)