from discord.ext import commands
import pandas as pd
import matplotlib.pyplot as plt
import utils.customconverters as customconverters
import io
import discord
from wordcloud import WordCloud, STOPWORDS

class StatsCommands(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx):
        if not ctx.guild or str(ctx.guild.id) not in dict(self.bot._cfg.items('botservers')).values():
            return False
        return True

    async def setstyle(self, fig, ax):
        discordbg = "#36393E"
        plt.rcParams['savefig.facecolor'] = discordbg
        ax.set_facecolor(discordbg)
        fig.set_facecolor(discordbg)
        ax.spines['bottom'].set_color("white")
        ax.spines['top'].set_color('white')
        ax.spines['left'].set_color('white')
        ax.spines['right'].set_color('white')
        ax.xaxis.label.set_color('white')
        ax.yaxis.label.set_color('white')
        ax.tick_params(colors='white')
        return fig, ax

    @commands.cooldown(1, 15, commands.BucketType.user)
    @commands.command(aliases=["msgsperday"])
    async def msgperday(self, ctx, target : customconverters.GlobalUser = None):
        if target is None:
            target=ctx.author
        async with ctx.channel.typing():
            # slasher is hardcoded for now, change later
            rollingwindow = 5 # rolling mean of width 5
            cursor = ctx.bot._db['slasher'].find({"author_id": target.id}, {"_id": 0, 'timestamp': 1})
            series = pd.Series(index = [i['timestamp'] async for i in cursor], data=1)
            perday = series.resample("1D").sum()
            resampled = perday.rolling(rollingwindow).mean()
            fig, ax = plt.subplots(figsize=(10, 5))
            fig, ax = await self.setstyle(fig, ax)
            ax.set_ylabel("messages/day")
            fig.suptitle(target.name + "#" + target.discriminator + "\nmessages/day over time", color="white")
            ax.plot(resampled, color="white")
            buf = io.BytesIO()
            plt.savefig(buf, bbox_inches="tight", format="png")
            buf.seek(0)
            plt.close()
            await ctx.send(file=discord.File(buf, filename=target.name + "_graph.png"))

    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.command(name ="find", aliases=["finduserid", "finduser"])
    async def finduserid(self, ctx, tofind : str):
        server = "slasher" # hardcoded to slasher for now, change later
        query = self.bot._db[server].aggregate([{"$match": {'author_name': {'$regex': tofind, '$options': 'i'}}},
                              {"$group": {"_id": "$author_name", "userid": {"$addToSet": "$author_id"},
                                          "count": {"$sum": 1}}},
                              {"$sort": {"count": -1}}])
        output = f"Results for \"{tofind}\":\n"
        i, maxiter = 0, 5
        async for x in query:
            output += f"\"{x['_id']}\", userid: {x['userid']}, msgcount: {x['count']}\n"
            i += 1
            if i >= maxiter:
                break
        await ctx.send(output)

    @commands.command(name="forumfind", aliases=["forumsearch"])
    async def find_forum_user(self, ctx, tofind: str):
        server = "mordhauforum"  # hardcoded to slasher for now, change later
        query = self.bot._db[server].aggregate([{"$match": {'author_name': {'$regex': tofind, '$options': 'i'}}},
                                                {"$group": {"_id": "$author_name",
                                                            "userid": {"$addToSet": "$user_id"},
                                                            "count": {"$sum": 1}}},
                                                {"$sort": {"count": -1}}])
        output = f"Results for \"{tofind}\":\n"
        i, maxiter = 0, 5
        async for x in query:
            output += f"\"{x['_id']}\", userid: {x['userid']}, msgcount: {x['count']}\n"
            i += 1
            if i >= maxiter:
                break
        await ctx.send(output)

    @commands.command(name="wordcloud")
    async def make_wordcloud(self, ctx, target: customconverters.GlobalUser = None):
        async with ctx.channel.typing():
            if target is None:
                target = ctx.author
            wordlist = ""
            stopwords = set(STOPWORDS)
            for (coll, serverid) in self.bot._cfg.items('scrapeservers'):
                query = self.bot._db[coll].find({"author_id": target.id}, {"_id": 0, "content": 1})
                async for doc in query:
                    wordlist += doc['content'] + '\n'
            wordcloud = WordCloud(max_font_size=50, max_words=100, background_color="#36393E",
                                  stopwords=stopwords, collocations=False).generate(wordlist)
            buf = io.BytesIO()
            img = wordcloud.to_image()
            img.save(buf, format="PNG")
            buf.seek(0)
            await ctx.send(f"{target.name}'s wordcloud:", file=discord.File(buf, filename=target.name + "_wordcloud.png"))


def setup(bot):
    bot.add_cog(StatsCommands(bot))
