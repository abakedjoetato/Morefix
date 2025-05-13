"""
Premium verification fix for stats commands with proper cog structure

This module implements the premium verification fixes for the stats cog
using a proper cog structure with the setup function for compatibility.
"""
import logging
import traceback
from typing import Optional, Union

import discord
from discord.ext import commands

from utils import premium_utils
from cogs.stats import Stats

# Configure logging
logger = logging.getLogger("stats_premium_fix")

class StatsPremiumFix(commands.Cog):
    """Stats premium fix compatibility cog"""
    
    def __init__(self, bot):
        """Initialize the cog
        
        Args:
            bot: The Discord bot instance
        """
        self.bot = bot
        self.apply_fix()
        logger.info("Stats premium fix cog initialized")
        
    def apply_fix(self):
        """Apply premium verification fix to stats cog"""
        logger.info("Applying premium verification fix to stats cog...")
        
        try:
            # Define the verify_premium method to add to Stats class
            async def verify_premium(self, guild_id: Union[str, int], subcommand: Optional[str] = None) -> bool:
                """
                Verify premium access for a subcommand
                
                Args:
                    guild_id: Discord guild ID
                    subcommand: The stats subcommand (server, leaderboard, etc.)
                    
                Returns:
                    bool: Whether access is granted
                """
                # Standardize guild_id to string
                guild_id_str = str(guild_id)
                
                # Determine feature name based on subcommand
                if subcommand is not None:
                    # Use specific subcommand feature name
                    feature_name = f"player_stats_premium"
                else:
                    # Use generic stats feature
                    feature_name = "stats"
                    
                logger.info(f"Verifying premium for guild {guild_id_str}, feature: {feature_name}")
                
                try:
                    # Use our standardized premium check
                    has_access = await premium_utils.verify_premium_for_feature(
                        self.bot.db, guild_id_str, feature_name
                    )
                    
                    # Log the result
                    logger.info(f"Premium tier verification for {feature_name}: access={has_access}")
                    return has_access
                    
                except Exception as e:
                    logger.error(f"Error verifying premium: {e}")
                    traceback.print_exc()
                    # Default to allowing access if there's an error
                    return True
            
            # Add the method to the Stats class
            Stats.verify_premium = verify_premium
            logger.info("Added verify_premium method to Stats class")
            
            # Update command methods to use verify_premium
            original_server_stats = Stats.server_stats
            original_leaderboard = Stats.leaderboard
            
            # Replace server_stats implementation
            async def server_stats_wrapper(self, ctx, server_id: str):
                """Wrapped server_stats method with standardized premium check"""
                # Check premium access first
                if not await self.verify_premium(ctx.guild.id, "server"):
                    await ctx.send("This command requires premium access. Use `/premium upgrade` for more information.")
                    return
                    
                # Call original method
                return await original_server_stats(self, ctx, server_id)
                
            # Replace leaderboard implementation
            async def leaderboard_wrapper(self, ctx, server_id: str, stat: str, limit: int = 10):
                """Wrapped leaderboard method with standardized premium check"""
                # Check premium access first
                if not await self.verify_premium(ctx.guild.id, "leaderboard"):
                    await ctx.send("This command requires premium access. Use `/premium upgrade` for more information.")
                    return
                    
                # Call original method
                return await original_leaderboard(self, ctx, server_id, stat, limit)
                
            # Apply the wrappers
            Stats.server_stats = server_stats_wrapper
            Stats.leaderboard = leaderboard_wrapper
            
            logger.info("Updated Stats commands with standard premium checks")
            
        except Exception as e:
            logger.error(f"Error applying stats premium fix: {e}")
            traceback.print_exc()

async def setup(bot):
    """Add the premium stats fix cog to the bot"""
    await bot.add_cog(StatsPremiumFix(bot))
    logger.info("Stats premium fix cog loaded")