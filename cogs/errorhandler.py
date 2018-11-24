import traceback
import sys
from discord.ext import commands
import utils.customerrors as customerrors
import discord
from pymongo.errors import ServerSelectionTimeoutError, AutoReconnect

class ErrorHandler:
    def __init__(self, bot):
        self.bot = bot

    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            return
        if isinstance(error, commands.BadArgument):  # can't find member
            return await ctx.send(error)
        if isinstance(error, commands.CommandOnCooldown):
            seconds = error.retry_after
            seconds = round(seconds, 2)
            hours, remainder = divmod(int(seconds), 3600)
            minutes, seconds = divmod(remainder, 60)
            await ctx.send(f"wait {minutes}")

        if isinstance(error, commands.CheckFailure):
            return # error is handled locally in check functions

        if hasattr(error, "original"):
            if isinstance(error.original, (ServerSelectionTimeoutError, AutoReconnect)):
                # can't connect to MongoDB
                print(error)
                return await ctx.send("can't connect to db")
            if isinstance(error.original, discord.Forbidden):
                print(error)
                return
            if isinstance(error.original, customerrors.ModelDoesntExist):
                prefix = ctx.bot.command_prefix
                return await ctx.send(f"create model first, type {prefix}vote or {prefix}replicate (admin-only)")
            if isinstance(error.original, customerrors.ModelAlreadyExists):
                return await ctx.send("same model already exists")
            if isinstance(error.original, customerrors.Busy):
                return await ctx.send("busy creating model")
            if isinstance(error.original, customerrors.AlreadyScraping):
                return await ctx.send("already scraping")
            if isinstance(error.original, customerrors.NotEnoughMessages):
                return await ctx.send(f"{username} does not have enough messages ({error.original.msgcount} < {error.original.cutoff})")


        print('Ignoring exception in command {}:'.format(ctx.command), file=sys.stderr)
        traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)

def setup(bot):
    bot.add_cog(ErrorHandler(bot))