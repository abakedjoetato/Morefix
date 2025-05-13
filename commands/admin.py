import logging
import discord
from discord import app_commands
from discord.ext import commands
import config
from database import get_collection

logger = logging.getLogger(__name__)

def register_admin_commands(bot):
    """Register admin commands with the bot"""
    
    # Admin check function
    def is_admin():
        """Check if the user is an admin"""
        async def predicate(ctx):
            return ctx.author.id in config.ADMIN_IDS
        return commands.check(predicate)
    
    # Stats command
    @bot.hybrid_command(name="stats", description="Show bot statistics")
    @is_admin()
    async def stats(ctx):
        """Show bot statistics (admin only)"""
        try:
            # Get stats from database
            users_collection = get_collection("users")
            user_count = users_collection.count_documents({})
            
            # Create embed with stats
            embed = discord.Embed(
                title=f"{config.BOT_NAME} Statistics",
                color=config.COLORS["INFO"]
            )
            
            embed.add_field(name="Servers", value=str(len(bot.guilds)), inline=True)
            embed.add_field(name="Users in Database", value=str(user_count), inline=True)
            embed.add_field(name="Bot Latency", value=f"{round(bot.latency * 1000)}ms", inline=True)
            
            embed.add_field(name="Python Version", value=discord.__version__, inline=True)
            embed.add_field(name="Uptime", value="Coming soon", inline=True)
            
            await ctx.send(embed=embed)
        
        except Exception as e:
            logger.error(f"Error showing stats: {e}", exc_info=True)
            embed = discord.Embed(
                title="Error",
                description="An error occurred while retrieving statistics.",
                color=config.COLORS["ERROR"]
            )
            await ctx.send(embed=embed)
    
    # Clear messages command
    @bot.hybrid_command(name="clear", description="Clear messages (Admin only)")
    @app_commands.describe(amount="Number of messages to clear (default: 5)")
    @is_admin()
    async def clear(ctx, amount: int = 5):
        """Clear a specified number of messages (admin only)"""
        try:
            # Validate amount
            if amount <= 0:
                embed = discord.Embed(
                    title="Error",
                    description="Please specify a positive number of messages to clear.",
                    color=config.COLORS["ERROR"]
                )
                await ctx.send(embed=embed, ephemeral=True)
                return
            
            if amount > 100:
                embed = discord.Embed(
                    title="Warning",
                    description="You can only delete up to 100 messages at once. Setting amount to 100.",
                    color=config.COLORS["WARNING"]
                )
                await ctx.send(embed=embed, ephemeral=True)
                amount = 100
            
            # Delete command message if it's not a slash command
            if not ctx.interaction:
                await ctx.message.delete()
            
            # Delete messages
            deleted = await ctx.channel.purge(limit=amount)
            
            # Send confirmation
            embed = discord.Embed(
                title="Messages Cleared",
                description=f"Successfully deleted {len(deleted)} messages.",
                color=config.COLORS["SUCCESS"]
            )
            await ctx.send(embed=embed, ephemeral=True, delete_after=5)
            
            # Log the action
            logger.info(f"{ctx.author} cleared {len(deleted)} messages in {ctx.channel}")
        
        except discord.Forbidden:
            embed = discord.Embed(
                title="Error",
                description="I don't have permission to delete messages in this channel.",
                color=config.COLORS["ERROR"]
            )
            await ctx.send(embed=embed, ephemeral=True)
        
        except Exception as e:
            logger.error(f"Error clearing messages: {e}", exc_info=True)
            embed = discord.Embed(
                title="Error",
                description="An error occurred while clearing messages.",
                color=config.COLORS["ERROR"]
            )
            await ctx.send(embed=embed, ephemeral=True)
