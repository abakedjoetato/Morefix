"""
Premium features and management commands for the Discord bot.
This module handles premium tier subscription management, feature access, and status commands.
"""
import logging
import traceback
from datetime import datetime, timedelta
from typing import Union, Optional, Dict, Any, List

import discord
from discord import app_commands
from discord.ext import commands

from config import Config
from utils.premium_mongodb_models import PremiumGuild

logger = logging.getLogger(__name__)

class PremiumCog(commands.Cog):
    """Premium features and management commands"""
    
    def __init__(self, bot):
        self.bot = bot
        logger.info("Premium cog initialized")
        
    @commands.hybrid_group(name="premium", description="Premium management commands")
    @commands.guild_only()
    async def premium(self, ctx):
        """Premium command group"""
        if ctx.invoked_subcommand is None:
            await ctx.send("Please specify a subcommand. Use `/premium status` to check your premium status.")

    @premium.command(name="status", description="Check premium status")
    async def status(self, ctx):
        """Check guild's premium tier status"""
        try:
            # Get guild premium tier directly
            tier = "free"  # Default tier
            
            embed = discord.Embed(
                title="Premium Status",
                description=f"Current Premium Tier: **{tier.capitalize()}**",
                color=Config.EMBED_COLOR
            )
            
            # Add tier information
            embed.add_field(
                name="Available Tiers",
                value="Use `/premium info` to see available premium tiers and features."
            )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error getting premium status: {e}", exc_info=True)
            await ctx.send("An error occurred while checking premium status. Please try again later.")
    
    @premium.command(name="info", description="Get information about premium tiers")
    async def info(self, ctx):
        """View premium tier information"""
        embed = discord.Embed(
            title="Premium Tiers Information",
            description="Choose the premium tier that best fits your server's needs.",
            color=Config.EMBED_COLOR
        )
        
        # Add each tier's information
        for tier_id, tier_data in Config.PREMIUM_TIERS.items():
            features_text = "\n".join([f"• {feature}" for feature in tier_data["features"]])
            
            embed.add_field(
                name=f"{tier_data['name']} Tier - ${tier_data['price']}/month",
                value=features_text,
                inline=False
            )
        
        await ctx.send(embed=embed)

async def setup(bot):
    """Add the premium cog to the bot"""
    await bot.add_cog(PremiumCog(bot))
    logger.info("Premium cog loaded")