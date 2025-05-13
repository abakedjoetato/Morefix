"""
Premium Features Cog

This module implements premium feature management with the new command handler framework
and safe MongoDB operations.
"""

import logging
import datetime
import discord
from utils.discord_patches import app_commands
from discord.ext import commands
from typing import Dict, List, Optional, Union, Literal

from utils.command_handlers import command_handler, db_operation
from utils.safe_mongodb import SafeMongoDBResult, SafeDocument
from utils.premium_feature_access import check_premium_feature_access

logger = logging.getLogger(__name__)

PREMIUM_TIERS = {
    0: "Free",
    1: "Basic",
    2: "Standard",
    3: "Pro",
    4: "Enterprise",
    5: "Ultimate"
}

PREMIUM_FEATURES = {
    "dashboard": {"tier": 1, "description": "Web dashboard access"},
    "custom_embeds": {"tier": 1, "description": "Custom embed formatting"},
    "advanced_stats": {"tier": 2, "description": "Advanced player statistics"},
    "bounties": {"tier": 2, "description": "Bounty system"},
    "rivalries": {"tier": 3, "description": "Player rivalry tracking"},
    "leaderboards": {"tier": 3, "description": "Custom leaderboards"},
    "auto_roles": {"tier": 4, "description": "Automatic role assignments based on stats"},
    "advanced_logs": {"tier": 4, "description": "Advanced log parsing and analysis"},
    "api_access": {"tier": 5, "description": "API access for external integrations"}
}

class Premium(commands.Cog):
    """
    Premium feature management for the Tower of Temptation PvP Statistics Bot.
    
    Controls access to premium features and provides commands for viewing 
    and managing subscription status.
    """
    
    def __init__(self, bot):
        self.bot = bot
        
    @commands.slash_command(
        name="premium",
        description="Show premium status and available features"
    )
    @command_handler()
    async def premium_command(
        self, 
        interaction: discord.Interaction
    ):
        """
        Show premium status and available features.
        
        Args:
            interaction: Discord interaction
        """
        # Get the guild ID safely
        guild_id = None
        if hasattr(interaction, 'guild_id') and interaction.guild_id is not None:
            guild_id = interaction.guild_id
        
        if guild_id is None:
            await interaction.response.send_message(
                "This command must be used in a guild.",
                ephemeral=True
            )
            return
        
        # Get premium status
        premium_result = await self.get_premium_status(guild_id)
        
        # Handle database errors
        if not premium_result.success:
            error = premium_result.error()
            error_msg = str(error) if error else "Unknown error"
            logger.error(f"Error getting premium status: {error_msg}")
            await interaction.response.send_message(
                f"Failed to get premium status: {error_msg}",
                ephemeral=True
            )
            return
        
        premium_info = premium_result.result
        premium_tier = 0  # Default to free tier
        
        # Extract premium tier from result
        if premium_info and hasattr(premium_info, 'premium_tier'):
            premium_tier = premium_info.premium_tier
        
        # Get enabled features
        enabled_features = []
        for feature, info in PREMIUM_FEATURES.items():
            if info["tier"] <= premium_tier:
                enabled_features.append(feature)
        
        # Create embed with premium information
        embed = discord.Embed(
            title="Premium Status",
            description=f"Current tier: **{PREMIUM_TIERS.get(premium_tier, 'Free')}**",
            color=discord.Color.gold() if premium_tier > 0 else discord.Color.light_grey()
        )
        
        # Add fields for features
        if enabled_features:
            features_text = ""
            for feature in enabled_features:
                feature_info = PREMIUM_FEATURES.get(feature, {})
                features_text += f"• **{feature}**: {feature_info.get('description', '')}\n"
                
            embed.add_field(
                name="Enabled Features",
                value=features_text,
                inline=False
            )
        else:
            embed.add_field(
                name="Enabled Features",
                value="No premium features enabled",
                inline=False
            )
        
        # Add field for upgrade info
        if premium_tier < 5:
            next_tier = premium_tier + 1
            next_features = []
            for feature, info in PREMIUM_FEATURES.items():
                if info["tier"] == next_tier:
                    next_features.append(f"• **{feature}**: {info['description']}")
            
            if next_features:
                embed.add_field(
                    name=f"Upgrade to {PREMIUM_TIERS.get(next_tier)}",
                    value="\n".join(next_features),
                    inline=False
                )
        
        # Send the embed
        await interaction.response.send_message(embed=embed)
    
    @commands.slash_command(
        name="set_premium",
        description="Set premium tier for this guild (Admin only)"
    )
    @app_commands.describe(
        tier="Premium tier (0-5)"
    )
    @command_handler(admin_only=True)
    async def set_premium_command(
        self, 
        interaction: discord.Interaction,
        tier: int
    ):
        """
        Set premium tier for this guild (Admin only).
        
        Args:
            interaction: Discord interaction
            tier: Premium tier (0-5)
        """
        # Validate tier
        if tier < 0 or tier > 5:
            await interaction.response.send_message(
                "Premium tier must be between 0 and 5.",
                ephemeral=True
            )
            return
        
        # Get the guild ID safely
        guild_id = None
        if hasattr(interaction, 'guild_id') and interaction.guild_id is not None:
            guild_id = interaction.guild_id
        
        if guild_id is None:
            await interaction.response.send_message(
                "This command must be used in a guild.",
                ephemeral=True
            )
            return
        
        # Update premium tier
        update_result = await self.set_premium_tier(guild_id, tier)
        
        # Handle database errors
        if not update_result.success:
            error = update_result.error()
            error_msg = str(error) if error else "Unknown error"
            logger.error(f"Error setting premium tier: {error_msg}")
            await interaction.response.send_message(
                f"Failed to set premium tier: {error_msg}",
                ephemeral=True
            )
            return
        
        # Success message
        await interaction.response.send_message(
            f"Premium tier set to **{PREMIUM_TIERS.get(tier, 'Unknown')}**.",
            ephemeral=False
        )
    
    @commands.slash_command(
        name="enable_feature",
        description="Enable a specific premium feature for this guild (Admin only)"
    )
    @app_commands.describe(
        feature="The feature to enable",
        server_id="Optional server ID for multi-server setups"
    )
    @app_commands.choices(feature=[
        utils.discord_patches.app_commands.Choice(name=f"{feature} ({info['description']})", value=feature)
        for feature, info in PREMIUM_FEATURES.items()
    ])
    @command_handler(admin_only=True)
    async def enable_feature_command(
        self, 
        interaction: discord.Interaction,
        feature: str,
        server_id: Optional[str] = None
    ):
        """
        Enable a specific premium feature for this guild (Admin only).
        
        Args:
            interaction: Discord interaction
            feature: The feature to enable
            server_id: Optional server ID for multi-server setups
        """
        # Check if feature exists
        if feature not in PREMIUM_FEATURES:
            await interaction.response.send_message(
                f"Unknown feature: {feature}",
                ephemeral=True
            )
            return
        
        # Get the guild ID safely
        guild_id = None
        if hasattr(interaction, 'guild_id') and interaction.guild_id is not None:
            guild_id = interaction.guild_id
        
        if guild_id is None:
            await interaction.response.send_message(
                "This command must be used in a guild.",
                ephemeral=True
            )
            return
            
        # First check premium tier
        premium_result = await self.get_premium_status(guild_id)
        
        # Handle database errors
        if not premium_result.success:
            error = premium_result.error()
            error_msg = str(error) if error else "Unknown error"
            logger.error(f"Error getting premium status: {error_msg}")
            await interaction.response.send_message(
                f"Failed to get premium status: {error_msg}",
                ephemeral=True
            )
            return
        
        premium_info = premium_result.result
        premium_tier = 0  # Default to free tier
        
        # Extract premium tier from result
        if premium_info and hasattr(premium_info, 'premium_tier'):
            premium_tier = premium_info.premium_tier
        
        # Check if tier allows this feature
        feature_tier = PREMIUM_FEATURES.get(feature, {}).get("tier", 999)
        if premium_tier < feature_tier:
            await interaction.response.send_message(
                f"This feature requires **{PREMIUM_TIERS.get(feature_tier)}** tier or higher. " +
                f"Current tier: **{PREMIUM_TIERS.get(premium_tier, 'Free')}**",
                ephemeral=True
            )
            return
        
        # Enable the feature
        update_result = await self.enable_feature(guild_id, feature, server_id)
        
        # Handle database errors
        if not update_result.success:
            error = update_result.error()
            error_msg = str(error) if error else "Unknown error"
            logger.error(f"Error enabling feature: {error_msg}")
            await interaction.response.send_message(
                f"Failed to enable feature: {error_msg}",
                ephemeral=True
            )
            return
        
        # Success message
        await interaction.response.send_message(
            f"Feature **{feature}** enabled{' for server ' + server_id if server_id else ''}.",
            ephemeral=False
        )
    
    @db_operation(collection_name="guilds", operation="query")
    async def get_premium_status(
        self,
        guild_id: Union[str, int]
    ) -> SafeMongoDBResult[SafeDocument]:
        """
        Get premium status for a guild with safe database operations.
        
        Args:
            guild_id: The guild ID
            
        Returns:
            SafeMongoDBResult containing the guild document or error
        """
        try:
            # Convert guild_id to string for MongoDB
            guild_id_str = str(guild_id)
            
            # Get the database connection
            if not hasattr(self.bot, 'db') or self.bot.db is None:
                return SafeMongoDBResult.create_error("Database connection not available")
            
            # Get guild document
            guild_doc = await self.bot.db.guilds.find_one({"guild_id": guild_id_str})
            
            # Return document or empty document if not found
            return SafeMongoDBResult.ok(SafeDocument(guild_doc))
            
        except Exception as e:
            logger.error(f"Error getting premium status: {e}")
            return SafeMongoDBResult.create_error(e)
    
    @db_operation(collection_name="guilds", operation="update")
    async def set_premium_tier(
        self,
        guild_id: Union[str, int],
        tier: int
    ) -> SafeMongoDBResult[Dict]:
        """
        Set premium tier for a guild with safe database operations.
        
        Args:
            guild_id: The guild ID
            tier: Premium tier level (0-5)
            
        Returns:
            SafeMongoDBResult containing the update result or error
        """
        try:
            # Validate tier
            if tier < 0 or tier > 5:
                return SafeMongoDBResult.create_error("Premium tier must be between 0 and 5")
            
            # Convert guild_id to string for MongoDB
            guild_id_str = str(guild_id)
            
            # Get the database connection
            if not hasattr(self.bot, 'db') or self.bot.db is None:
                return SafeMongoDBResult.create_error("Database connection not available")
            
            # Update guild document
            update_data = {
                "$set": {
                    "premium_tier": tier,
                    "updated_at": datetime.datetime.utcnow().isoformat()
                }
            }
            
            # Use upsert to create the document if it doesn't exist
            result = await self.bot.db.guilds.update_one(
                {"guild_id": guild_id_str},
                update_data,
                upsert=True
            )
            
            # Return success
            return SafeMongoDBResult.ok({
                "acknowledged": result.acknowledged,
                "modified_count": result.modified_count,
                "upserted_id": result.upserted_id
            })
            
        except Exception as e:
            logger.error(f"Error setting premium tier: {e}")
            return SafeMongoDBResult.create_error(e)
    
    @db_operation(collection_name="guilds", operation="update")
    async def enable_feature(
        self,
        guild_id: Union[str, int],
        feature: str,
        server_id: Optional[str] = None
    ) -> SafeMongoDBResult[Dict]:
        """
        Enable a specific feature for a guild with safe database operations.
        
        Args:
            guild_id: The guild ID
            feature: Feature name
            server_id: Optional server ID for multi-server setups
            
        Returns:
            SafeMongoDBResult containing the update result or error
        """
        try:
            # Check if feature exists
            if feature not in PREMIUM_FEATURES:
                return SafeMongoDBResult.create_error(f"Unknown feature: {feature}")
            
            # Convert guild_id to string for MongoDB
            guild_id_str = str(guild_id)
            
            # Get the database connection
            if not hasattr(self.bot, 'db') or self.bot.db is None:
                return SafeMongoDBResult.create_error("Database connection not available")
            
            # Prepare the update field
            feature_field = "features_enabled"
            if server_id:
                feature_field = f"server_features.{server_id}"
            
            # Update guild document
            update_data = {
                "$addToSet": {
                    feature_field: feature
                },
                "$set": {
                    "updated_at": datetime.datetime.utcnow().isoformat()
                }
            }
            
            # Use upsert to create the document if it doesn't exist
            result = await self.bot.db.guilds.update_one(
                {"guild_id": guild_id_str},
                update_data,
                upsert=True
            )
            
            # Return success
            return SafeMongoDBResult.ok({
                "acknowledged": result.acknowledged,
                "modified_count": result.modified_count,
                "upserted_id": result.upserted_id
            })
            
        except Exception as e:
            logger.error(f"Error enabling feature: {e}")
            return SafeMongoDBResult.create_error(e)

async def setup(bot):
    await bot.add_cog(Premium(bot))