from discord.ext import commands
import asyncio
import datetime
import random
from utils.customerrors import ModelAlreadyExists, NotEnoughMessages
from utils.helpers import username_from_db
import utils.customconverters as customconverters
import utils.checks as checks

class VoteCommand(commands.Cog):

    def __init__(self, bot):
        self.bot=bot

    async def __local_check(self, ctx):
        if not ctx.guild or str(ctx.guild.id) not in dict(self.bot._cfg.items('botservers')).values():
            #silently fail
            return False
        return True

    @checks.votecd()
    @commands.command()
    async def vote(self, ctx, target: customconverters.GlobalUser = None):
        emojis = ["\u0031\u20E3", "\u0032\u20E3", "\u0033\u20E3", "\u0034\u20E3", "\u0035\u20E3"]
        candidates = await self.make_candidate_list(ctx, target)
        candidatenames = await self.get_candidate_names(ctx, candidates)
        votestring = ""
        for x in range(5):
            votestring += f"\n{x+1}: {candidatenames[x]}"
        votemsg = await ctx.send(f"Vote user to replicate, vote ends in 20seconds: {votestring}")
        for emoji in emojis:
            await votemsg.add_reaction(emoji)
        await asyncio.sleep(20)
        results = {emoji: 0 for emoji in emojis}
        # have to use ctx.channel.history to get the updated message, editing the message does not return it anymore
        # in rewrite
        async for message in ctx.channel.history(limit=1, after=votemsg.created_at - datetime.timedelta(microseconds=1)):
            if message.id == votemsg.id:
                for reaction in message.reactions:
                    if reaction.emoji in emojis:
                        results[reaction.emoji] += reaction.count
        max_value = max(results.values())
        windexlist = [emojis.index(key) for key, value in results.items() if value == max_value]
        if len(windexlist) > 1:
            if target and candidates.index(target.id) in windexlist:
                winner = target.id
                await ctx.send(f"draw, preferring voted user {target.name}")
            else:
                winnerindex = random.choice(windexlist)
                winner = candidates[winnerindex]
                await ctx.send(f"draw, selecting random winner: {candidatenames[winnerindex]}")
        else:
            winner = candidates[windexlist[0]]
            await ctx.send(f"winner: {candidatenames[windexlist[0]]}")
        if winner:
            winneruser = await self.bot.fetch_user(winner)
            await ctx.invoke(self.bot.get_command('replicate'), winneruser)
        else:
            # winner is 0 which is "keep current model", add 1 token to avatarcd bucket
            self.bot._avatarcd._cooldown._tokens += 1


    async def make_candidate_list(self, ctx, target):
        candidates = []
        cutoff = self.bot._cfg.getint("settings", "msgcutoff", fallback=1000)
        userpopcursor = self.bot._db['statistics'].find({"messagecount": {"$gt": cutoff}})
        userpop = []
        async for user in userpopcursor:
            userpop.append(user)
        if target:
            if target.id == self.bot._model.authorid:
                raise ModelAlreadyExists
            msgcountdoc = await self.bot._db['statistics'].find_one({"author_id": target.id})
            msgcount = msgcountdoc['messagecount']
            if msgcount < cutoff:
                raise NotEnoughMessages(target.name, msgcount, cutoff)
            else:
                candidates.append(target.id)
        if self.bot._model.model:
            candidates.append(0)
        sample = random.sample(userpop, 5 - len(candidates))
        for user in sample:
            candidates.append(user['author_id'])
        return candidates

    async def get_candidate_names(self, ctx, candidates):
        candidatenames = []
        for candidate in candidates:
            if candidate == 0:
                candidatenames.append("Keep current model")
            else:
                username = await username_from_db(ctx, candidate)
                if username:
                    candidatenames.append(username)
                else:
                    candidatenames.append("unknown user")
        return candidatenames


def setup(bot):
    bot.add_cog(VoteCommand(bot))