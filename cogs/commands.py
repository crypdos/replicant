from discord.ext import commands
import utils.customconverters as customconverters
from utils.helpers import clean_content
from discord import Forbidden

class UserCommands(commands.Cog, name='User Commands'):

    def __init__(self, bot):
        self.bot = bot
        self.password = self.bot._cfg['discord']['password']

    async def __local_check(self,ctx):
        if not ctx.guild or str(ctx.guild.id) not in dict(self.bot._cfg.items('botservers')).values():
            return False
        return True

    @commands.command(aliases=['listcommands', 'cmdlist'])
    async def commandlist(self, ctx):
        commandstring = ""
        for cog in self.bot.cogs:
            cogcommands = self.bot.get_cog_commands(cog)
            if cogcommands:
                commandstring += "\n" + cog + ": "
                firstiter = True
                for cmd in cogcommands:
                    if firstiter:
                        commandstring += self.bot.command_prefix + cmd.name
                        firstiter = False
                    else:
                        commandstring += ", " + self.bot.command_prefix + cmd.name
        await ctx.send(commandstring)

    @commands.command(name="countmsg", aliases=['count', 'countmessages'])
    async def count_messages(self, ctx, target: customconverters.GlobalUser):
        messagecount = await self.bot._db['statistics'].find_one({"author_id": target.id})
        if messagecount:
            await ctx.send(f"{messagecount['messagecount']} messages from {target.name}")

    @commands.command(name="listadmins", aliases=['adminlist'])
    async def list_admins(self, ctx):
        admins = self.bot._db['admins'].find()
        firstiter = True
        async for admin in admins:
            if firstiter:
                adminlist = admin['name']
                firstiter = False
            else:
                adminlist += ", " + admin['name']
        if not firstiter:
            await ctx.send(f"list of admins: {adminlist}")
        else:
            await ctx.send("no admins")

    @commands.command(name="s")
    async def say(self, ctx, beginning : str = None):
        if self.bot._cfg.get('settings', 'deletesay', fallback = "no").lower() == "yes":
            try:
                await ctx.message.delete()
            except Forbidden:
                print("No permission to delete message")
        sentence = await self.bot._model.makeSentence(beginning)
        if sentence:
            if "@" in sentence:
                cleansentence = await clean_content(ctx, sentence)
            else:
                cleansentence = sentence
            await ctx.send(cleansentence)

def setup(bot):
    bot.add_cog(UserCommands(bot))

