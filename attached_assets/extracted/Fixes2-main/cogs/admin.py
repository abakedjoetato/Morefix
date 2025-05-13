import discord
from discord.ext import commands
import logging
from utils.database import Database

logger = logging.getLogger("discord_bot")

class Admin(commands.Cog):
    """Administrative commands for the bot"""
    
    def __init__(self, bot):
        self.bot = bot
        self.db = Database()
    
    @commands.command(name="stats")
    @commands.has_permissions(administrator=True)
    async def stats(self, ctx):
        """Display database statistics for the bot"""
        stats = await self.db.get_bot_stats()
        
        embed = discord.Embed(
            title="Bot Statistics",
            color=discord.Color.blue(),
            description="Statistics from the database"
        )
        
        # Use .get() with default values for safer dict access
        # Convert integer values to strings for embed fields
        embed.add_field(name="Total Users", value=str(stats.get("user_count", 0)), inline=True)
        embed.add_field(name="Total Servers", value=str(stats.get("server_count", 0)), inline=True)
        embed.add_field(name="Total Commands Used", value=str(stats.get("total_commands", 0)), inline=True)
        embed.add_field(name="Total Messages Logged", value=str(stats.get("message_count", 0)), inline=True)
        
        await ctx.send(embed=embed)
    
    @commands.command(name="clearlogs")
    @commands.has_permissions(administrator=True)
    async def clearlogs(self, ctx, days: int = 30):
        """Clear message logs older than specified days (default: 30 days)"""
        result = await self.db.clear_old_logs(days)
        
        if result:
            await ctx.send(f"✅ Successfully cleared {result} message logs older than {days} days.")
        else:
            await ctx.send("❌ Failed to clear logs. Check the bot logs for details.")
    
    @commands.command(name="setconfigvalue")
    @commands.has_permissions(administrator=True)
    async def setconfigvalue(self, ctx, key: str, value: str):
        """Set a configuration value in the database"""
        await self.db.set_config(key, value)
        await ctx.send(f"✅ Configuration updated: `{key}` set to `{value}`")
    
    @commands.command(name="getconfigvalue")
    @commands.has_permissions(administrator=True)
    async def getconfigvalue(self, ctx, key: str):
        """Get a configuration value from the database"""
        value = await self.db.get_config(key)
        
        if value is not None:
            await ctx.send(f"Configuration `{key}` = `{value}`")
        else:
            await ctx.send(f"❌ Configuration key `{key}` not found.")

async def setup(bot):
    await bot.add_cog(Admin(bot))
    logger.info("Admin commands cog loaded")
