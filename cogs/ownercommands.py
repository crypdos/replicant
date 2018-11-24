from discord.ext import commands
import utils.customconverters as customconverters

class OwnerCommands:

    def __init__(self, bot):
        self.bot = bot

    async def __local_check(self, ctx):
        if not ctx.guild or str(ctx.guild.id) not in dict(self.bot._cfg.items('botservers')).values():
            #silently fail
            return False
        if ctx.author.id == self.bot.owner_id:
            return True
        else:
            await ctx.send("no")
            return False

    @commands.command(name="addadmin")
    async def add_admin(self, ctx, target: customconverters.GlobalUser):
        if not await self.bot._db['admins'].find_one({"id": target.id}):
            await self.bot._db['admins'].insert_one({'id' : target.id, 'name': target.name})
            await ctx.send(f"added admin {target.name}")
        else:
            await ctx.send(f"{target.name} is already admin")


    @commands.command(name="removeadmin", aliases =['deladmin', 'deleteadmin', 'rmadmin'])
    async def remove_admin(self, ctx, target: customconverters.GlobalUser):
        if await self.bot._db['admins'].find_one({"id": target.id}):
            await self.bot._db['admins'].delete_one({'id': target.id})
            await ctx.send(f"removed admin {target.name}")
        else:
            await ctx.send(f"{target.name} is not an admin")

    @commands.command(name="setaccname")
    async def change_accname(self, ctx, accname: str):
        await self.bot.user.edit(password=self.password, username=accname)

def setup(bot):
    bot.add_cog(OwnerCommands(bot))