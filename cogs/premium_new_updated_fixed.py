"""
Premium features and management commands for the Discord bot.
This module handles premium tier subscription management, feature access, and status commands.
Fixed for pycord 2.6.1 compatibility.
"""
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Union, List

import discord
from discord.ext import commands

from utils.premium_mongodb_models import PremiumSubscription, ActivationCode
from utils.command_handlers import command_handler, handle_command_error, enhanced_slash_command
from utils.interaction_handlers import safely_respond_to_interaction
from utils.error_handlers import create_error_embed

logger = logging.getLogger(__name__)

class PremiumCog(commands.Cog):
    """Premium features and management commands"""
    
    def __init__(self, bot):
        self.bot = bot
        self._premium_cache = {}
        self._cache_ttl = 300  # 5 minutes
        
    @commands.group(name="premium", invoke_without_command=True)
    async def premium(self, ctx):
        """Premium command group"""
        await ctx.send("Please use a subcommand: status, info, activate, features, upgrade")
        
    @premium.command(name="status")
    async def status(self, ctx):
        """Check guild's premium tier status"""
        if not ctx.guild:
            await ctx.send("This command can only be used in a server.")
            return
            
        try:
            # Get subscription from database
            subscription = await PremiumSubscription.get_by_guild_id(str(ctx.guild.id))
            
            if not subscription or not subscription.is_active:
                embed = discord.Embed(
                    title="Premium Status",
                    description="This server does not have an active premium subscription.",
                    color=discord.Color.blue()
                )
                embed.add_field(name="Upgrade", value="Use `/premium upgrade` to see available plans.")
                await ctx.send(embed=embed)
                return
                
            # Show active subscription details
            embed = discord.Embed(
                title="Premium Status",
                description=f"This server has an active **Tier {subscription.tier}** premium subscription.",
                color=discord.Color.gold()
            )
            
            # Add expiration date
            expires_at = subscription.expires_at
            embed.add_field(
                name="Expires",
                value=f"<t:{int(expires_at.timestamp())}:R>" if expires_at else "Never",
                inline=False
            )
            
            # Add features
            features = self._get_features_for_tier(subscription.tier)
            feature_text = "\n".join([f"✅ {feature}" for feature in features])
            embed.add_field(name="Features", value=feature_text, inline=False)
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await handle_command_error(ctx, e, "Failed to retrieve premium status.")
            
    @premium.command(name="info")
    async def info(self, ctx):
        """View premium tier information"""
        embed = discord.Embed(
            title="Premium Tiers Information",
            description="Tower of Temptation offers several premium tiers with enhanced features.",
            color=discord.Color.gold()
        )
        
        # Tier 1
        tier1_features = self._get_features_for_tier(1)
        embed.add_field(
            name="🥉 Tier 1",
            value="\n".join([f"• {feature}" for feature in tier1_features]),
            inline=False
        )
        
        # Tier 2  
        tier2_features = self._get_features_for_tier(2)
        embed.add_field(
            name="🥈 Tier 2",
            value="\n".join([f"• {feature}" for feature in tier2_features]),
            inline=False
        )
        
        # Tier 3
        tier3_features = self._get_features_for_tier(3)
        embed.add_field(
            name="🥇 Tier 3",
            value="\n".join([f"• {feature}" for feature in tier3_features]),
            inline=False
        )
        
        embed.add_field(
            name="How to Upgrade",
            value="Use `/premium upgrade` to get information on how to upgrade.",
            inline=False
        )
        
        await ctx.send(embed=embed)
        
    @premium.command(name="activate")
    async def activate(self, ctx, code: str = None):
        """Activate premium features using an activation code"""
        if not ctx.guild:
            await ctx.send("This command can only be used in a server.")
            return
            
        if not code:
            await ctx.send("Please provide an activation code. Usage: `/premium activate [code]`")
            return
            
        try:
            # Find activation code in database
            activation_code = await ActivationCode.get_by_code(code)
            
            if not activation_code:
                embed = create_error_embed(
                    "Invalid Code",
                    "The activation code you provided is invalid."
                )
                await ctx.send(embed=embed)
                return
                
            if activation_code.used:
                embed = create_error_embed(
                    "Code Already Used",
                    "This activation code has already been used."
                )
                await ctx.send(embed=embed)
                return
                
            # Check if guild already has a subscription
            existing_sub = await PremiumSubscription.get_by_guild_id(str(ctx.guild.id))
            
            if existing_sub and existing_sub.is_active:
                if existing_sub.tier >= activation_code.tier:
                    embed = create_error_embed(
                        "Subscription Already Active",
                        f"This server already has an active Tier {existing_sub.tier} subscription, " +
                        f"which is higher than or equal to the Tier {activation_code.tier} code you're trying to use."
                    )
                    await ctx.send(embed=embed)
                    return
                    
                # Upgrade existing subscription
                await existing_sub.upgrade(activation_code.tier, activation_code.duration_days)
                await activation_code.mark_as_used(ctx.guild.id)
                
                embed = discord.Embed(
                    title="Subscription Upgraded",
                    description=f"This server has been upgraded to Tier {activation_code.tier} premium for {activation_code.duration_days} days!",
                    color=discord.Color.green()
                )
                
            else:
                # Create new subscription
                new_sub = PremiumSubscription(
                    guild_id=str(ctx.guild.id),
                    tier=activation_code.tier,
                    activated_at=datetime.utcnow(),
                    expires_at=datetime.utcnow() + timedelta(days=activation_code.duration_days),
                    activated_by=str(ctx.author.id)
                )
                
                await new_sub.save()
                await activation_code.mark_as_used(ctx.guild.id)
                
                embed = discord.Embed(
                    title="Premium Activated",
                    description=f"This server now has Tier {activation_code.tier} premium for {activation_code.duration_days} days!",
                    color=discord.Color.green()
                )
                
            # Clear cache
            self._clear_guild_cache(ctx.guild.id)
            
            # List features
            features = self._get_features_for_tier(activation_code.tier)
            feature_text = "\n".join([f"✅ {feature}" for feature in features])
            embed.add_field(name="Features", value=feature_text, inline=False)
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await handle_command_error(ctx, e, "Failed to activate premium subscription.")
            
    @premium.command(name="features")
    async def features(self, ctx):
        """List available premium features based on tier"""
        if not ctx.guild:
            await ctx.send("This command can only be used in a server.")
            return
            
        try:
            # Get current subscription
            subscription = await PremiumSubscription.get_by_guild_id(str(ctx.guild.id))
            
            if not subscription or not subscription.is_active:
                embed = discord.Embed(
                    title="Premium Features",
                    description="This server does not have an active premium subscription.",
                    color=discord.Color.blue()
                )
                embed.add_field(
                    name="Free Features",
                    value="\n".join([f"• {feature}" for feature in self._get_features_for_tier(0)]),
                    inline=False
                )
                embed.add_field(
                    name="Upgrade",
                    value="Use `/premium upgrade` to see available premium features.",
                    inline=False
                )
            else:
                embed = discord.Embed(
                    title="Premium Features",
                    description=f"This server has an active **Tier {subscription.tier}** premium subscription.",
                    color=discord.Color.gold()
                )
                
                features = self._get_features_for_tier(subscription.tier)
                feature_text = "\n".join([f"✅ {feature}" for feature in features])
                embed.add_field(name="Available Features", value=feature_text, inline=False)
                
                # Show next tier if not at max
                if subscription.tier < 3:
                    next_tier = subscription.tier + 1
                    next_features = [f for f in self._get_features_for_tier(next_tier) 
                                    if f not in features]
                    if next_features:
                        upgrade_text = "\n".join([f"• {feature}" for feature in next_features])
                        embed.add_field(
                            name=f"Tier {next_tier} Features",
                            value=upgrade_text + "\n\nUse `/premium upgrade` for more info.",
                            inline=False
                        )
                
            await ctx.send(embed=embed)
            
        except Exception as e:
            await handle_command_error(ctx, e, "Failed to retrieve premium features.")
            
    @premium.command(name="upgrade")
    async def upgrade(self, ctx):
        """Get information on how to upgrade premium tier"""
        embed = discord.Embed(
            title="Upgrade Premium Tier",
            description="Upgrade your server to unlock enhanced features!",
            color=discord.Color.gold()
        )
        
        embed.add_field(
            name="How to Upgrade",
            value=(
                "1. Visit our website: https://toweroftemptation.gg/premium\n"
                "2. Select your desired tier\n"
                "3. Complete the payment process\n"
                "4. Receive your activation code\n"
                "5. Use `/premium activate [code]` in your server"
            ),
            inline=False
        )
        
        embed.add_field(
            name="Current Pricing",
            value=(
                "🥉 **Tier 1**: $5/month\n"
                "🥈 **Tier 2**: $10/month\n"
                "🥇 **Tier 3**: $20/month\n"
                "\nDiscounts available for quarterly and yearly subscriptions!"
            ),
            inline=False
        )
        
        embed.add_field(
            name="Need Help?",
            value="Join our support server: https://discord.gg/towertemptation",
            inline=False
        )
        
        await ctx.send(embed=embed)
        
    def _get_features_for_tier(self, tier: int) -> List[str]:
        """Get list of features available for a specific tier
        
        Args:
            tier: Premium tier level
            
        Returns:
            List of feature descriptions
        """
        # Free features
        features = [
            "Basic statistics tracking",
            "Server leaderboard (top 10)",
            "Basic canvas features"
        ]
        
        # Tier 1 features
        if tier >= 1:
            features.extend([
                "Extended leaderboard (top 25)",
                "Advanced statistics views",
                "Custom canvas colors (16)",
                "Stats refresh rate: 30 minutes"
            ])
            
        # Tier 2 features
        if tier >= 2:
            features.extend([
                "Expanded leaderboard (top 50)",
                "Player stat history graphs",
                "Canvas size: 32x32",
                "Custom canvas colors (32)",
                "Stats refresh rate: 15 minutes",
                "Server event notifications"
            ])
            
        # Tier 3 features
        if tier >= 3:
            features.extend([
                "Complete leaderboard (all players)",
                "Real-time statistics updates",
                "Canvas size: 64x64",
                "Custom canvas colors (unlimited)",
                "Stats refresh rate: 5 minutes",
                "Advanced analytics dashboard",
                "Priority support"
            ])
            
        return features
        
    def _clear_guild_cache(self, guild_id: int):
        """Clear premium status cache for a guild
        
        Args:
            guild_id: Discord guild ID
        """
        cache_key = f"premium:{guild_id}"
        if cache_key in self._premium_cache:
            del self._premium_cache[cache_key]
            
    async def check_premium(self, guild_id: Union[str, int], min_tier: int = 1) -> bool:
        """Check if a guild has premium status at or above the specified tier
        
        Args:
            guild_id: Discord guild ID
            min_tier: Minimum premium tier required
            
        Returns:
            bool: Whether guild has required premium tier
        """
        # Normalize guild ID to string
        guild_id_str = str(guild_id)
        
        # Check cache first
        cache_key = f"premium:{guild_id}"
        if cache_key in self._premium_cache:
            cached_result, timestamp = self._premium_cache[cache_key]
            # Check if cache is still valid
            if (datetime.utcnow() - timestamp).total_seconds() < self._cache_ttl:
                return cached_result.get('tier', 0) >= min_tier
                
        try:
            # Query database
            subscription = await PremiumSubscription.get_by_guild_id(guild_id_str)
            
            result = {
                'has_premium': bool(subscription and subscription.is_active),
                'tier': subscription.tier if subscription and subscription.is_active else 0
            }
            
            # Update cache
            self._premium_cache[cache_key] = (result, datetime.utcnow())
            
            return result['tier'] >= min_tier
            
        except Exception as e:
            logger.error(f"Error checking premium status: {e}")
            return False

async def setup(bot):
    """Add the premium cog to the bot"""
    await bot.add_cog(PremiumCog(bot))