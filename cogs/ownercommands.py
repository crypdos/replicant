from discord.ext import commands
import utils.customconverters as customconverters
import utils.helpers as helpers
import subprocess

class OwnerCommands:

    def __init__(self, bot):
        self.bot = bot
        self.password = self.bot._cfg.get('discord', 'password', fallback="")

    async def __local_check(self, ctx):
        if ctx.author.id == self.bot.owner_id:
            return True
        elif not ctx.guild or str(ctx.guild.id) not in dict(self.bot._cfg.items('botservers')).values():
            return False
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

    @commands.command(name="invite")
    async def invite(self, ctx, inviteurl : str):
        result = await helpers.accept_invite(ctx, inviteurl)
        if result.status == 200:
            await ctx.send('\N{OK HAND SIGN}')
        else:
            await ctx.send(result)

    @commands.command(name="gitupdate")
    async def gitupdate(self, ctx):
        output = subprocess.check_output(['git', 'pull'])
        decoded = output.decode("utf-8")
        await ctx.send(decoded)
        await ctx.invoke(self.bot.get_command('reload'))



def setup(bot):
    bot.add_cog(OwnerCommands(bot))