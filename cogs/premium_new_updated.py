"""
Premium features and management commands for the Discord bot.
This module handles premium tier subscription management, feature access, and status commands.
Fixed for pycord 2.6.1 compatibility.
"""
import logging
import traceback
from datetime import datetime, timedelta
from typing import Union, Optional, Dict, Any, List

import discord
from utils.discord_patches import app_commands
from discord.ext import commands

from config import Config
from utils.premium_mongodb_models import PremiumGuild
from utils.command_handlers import handle_command_error

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
                name=f"{tier_data['name']} Tier - ${tier_data['price_gbp']}/month",
                value=features_text,
                inline=False
            )
        
        await ctx.send(embed=embed)

    @premium.command(name="activate", description="Activate premium features for this server")
    @commands.has_permissions(administrator=True)
    async def activate(self, ctx, code: str = None):
        """Activate premium features using an activation code"""
        if not code:
            await ctx.send("Please provide an activation code. Example: `/premium activate CODE123`")
            return
        
        try:
            # In a real implementation, you'd verify the code against a database
            # For now, we'll simulate a successful activation for any code
            
            # Create a mock success message
            embed = discord.Embed(
                title="Premium Activated!",
                description="Your server has been upgraded to Premium status! You now have access to all premium features.",
                color=Config.SUCCESS_COLOR
            )
            
            embed.add_field(
                name="Tier",
                value="Pro"
            )
            
            embed.add_field(
                name="Valid Until",
                value=(datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
            )
            
            embed.set_footer(text="Use /premium status to check your premium status anytime")
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await handle_command_error(ctx, e, "Error activating premium features")

    @premium.command(name="features", description="List available premium features")
    async def features(self, ctx):
        """List available premium features based on tier"""
        try:
            # Get premium tier (placeholder implementation)
            tier = 0  # Default to free tier
            
            # Get features for this tier
            feature_list = Config.PREMIUM_TIERS.get(tier, {}).get("features", [])
            
            # Build feature list
            features_text = "\n".join([f"• {feature}" for feature in feature_list])
            
            if not features_text:
                features_text = "No premium features available on your current tier."
            
            embed = discord.Embed(
                title="Available Premium Features",
                description=f"Features available on your current tier ({Config.PREMIUM_TIERS.get(tier, {}).get('name', 'Free')}):",
                color=Config.EMBED_COLOR
            )
            
            embed.add_field(
                name="Features",
                value=features_text,
                inline=False
            )
            
            embed.set_footer(text="Upgrade your tier to unlock more features with /premium upgrade")
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await handle_command_error(ctx, e, "Error listing premium features")

    @premium.command(name="upgrade", description="Upgrade to a premium tier")
    async def upgrade(self, ctx):
        """Get information on how to upgrade premium tier"""
        embed = discord.Embed(
            title="Upgrade Premium Tier",
            description="To upgrade your premium tier, visit our website or contact support:",
            color=Config.EMBED_COLOR
        )
        
        embed.add_field(
            name="Website",
            value="https://toweroftemptation.com/premium",
            inline=False
        )
        
        embed.add_field(
            name="Contact Support",
            value="Email: support@toweroftemptation.com\nDiscord: https://discord.gg/toweroftemptation",
            inline=False
        )
        
        embed.set_footer(text="Use /premium activate CODE to activate your premium subscription once purchased")
        
        await ctx.send(embed=embed)

async def setup(bot):
    """Add the premium cog to the bot"""
    await bot.add_cog(PremiumCog(bot))
    logger.info("Premium cog loaded")