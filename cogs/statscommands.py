from discord.ext import commands
import pandas as pd
import matplotlib.pyplot as plt
import utils.customconverters as customconverters
import io
import discord

class StatsCommands:

    def __init__(self, bot):
        self.bot = bot

    async def __local_check(self, ctx):
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

    @commands.command()
    async def msgperday(self, ctx, target : customconverters.GlobalUser):
        ## slasher is hardcoded for now, change later
        cursor = ctx.bot._db['slasher'].find({"author_id": target.id}, {"_id": 0, 'timestamp': 1})
        df = pd.DataFrame([i async for i in cursor])
        binsize = 3
        counts = df['timestamp'].value_counts(sort=False)
        resampled = (counts.resample(str(binsize) + "D").sum() / binsize)

        fig, ax = plt.subplots(figsize=(10, 5))
        fig, ax = await self.setstyle(fig, ax)
        ax.set_ylabel("messages/day")
        fig.suptitle(target.name + "#" + target.discriminator + "\nmessages/day over time", color="white")
        ax.plot(resampled, color="white")
        buf = io.BytesIO()
        plt.savefig(buf, bbox_inches="tight", format="png")
        buf.seek(0)
        await ctx.send(file=discord.File(buf, filename=target.name + "_graph.png"))


def setup(bot):
    bot.add_cog(StatsCommands(bot))
