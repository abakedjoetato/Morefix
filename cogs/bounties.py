"""
Bounties Cog

This module implements bounty commands with the new command handler framework
and safe MongoDB operations.
"""

import logging
import datetime
import discord
from discord.ext import commands
from typing import Dict, List, Optional, Union

# Use our discord_patches module for app_commands compatibility
from utils.discord_patches import app_commands
# Import compatibility functions for command decorators
from utils.discord_compat import command, describe, guild_only

# Import utility modules for handling commands and database operations
from utils.command_handlers import command_handler, db_operation, defer_interaction
from utils.safe_mongodb import SafeMongoDBResult, SafeDocument
from utils.interaction_handlers import safely_respond_to_interaction

logger = logging.getLogger(__name__)

class Bounties(commands.Cog):
    """
    Bounty system commands for the Tower of Temptation PvP Statistics Bot.
    
    The bounty system allows players to place bounties on other players,
    which are claimed when the target is killed.
    """
    
    def __init__(self, bot):
        self.bot = bot
        
    @commands.slash_command(
        name="bounty",
        description="Place a bounty on a player"
    )
    @describe(
        player_name="Name of the player to place a bounty on",
        amount="Amount of currency to offer as a bounty",
        server_id="The server ID (optional)"
    )
    @command_handler(guild_only=True)
    async def bounty_command(
        self, 
        interaction: discord.Interaction, 
        player_name: str, 
        amount: int,
        server_id: Optional[str] = None
    ):
        """
        Place a bounty on a player.
        
        Args:
            interaction: Discord interaction
            player_name: Name of the player to place a bounty on
            amount: Amount of currency to offer as a bounty
            server_id: Optional server ID
        """
        # Input validation with error messages
        if amount <= 0:
            await safely_respond_to_interaction(
                interaction,
                "Bounty amount must be greater than 0.",
                ephemeral=True
            )
            return
            
        if player_name.strip() == "":
            await safely_respond_to_interaction(
                interaction,
                "Please provide a valid player name.",
                ephemeral=True
            )
            return
        
        # Get the guild ID safely
        guild_id = None
        if hasattr(interaction, 'guild_id') and interaction.guild_id is not None:
            guild_id = interaction.guild_id
        
        # Get the user ID safely
        user_id = None
        if hasattr(interaction, 'user') and interaction.user is not None:
            user_id = getattr(interaction.user, 'id', None)
        
        # Check if we have the necessary information
        if guild_id is None or user_id is None:
            await safely_respond_to_interaction(
                interaction,
                "Could not process your request. Missing guild or user information.",
                ephemeral=True
            )
            return
        
        # Create bounty using our safe db operation
        bounty_result = await self.create_bounty(
            guild_id=guild_id,
            server_id=server_id,
            placer_id=user_id,
            target_name=player_name,
            amount=amount
        )
        
        # Handle result with proper error checking
        if not bounty_result.success:
            error_msg = bounty_result.error if bounty_result.error else "Unknown error"
            logger.error(f"Error creating bounty: {error_msg}")
            await safely_respond_to_interaction(
                interaction,
                f"Failed to place bounty: {error_msg}",
                ephemeral=True
            )
            return
        
        # Success response
        await safely_respond_to_interaction(
            interaction,
            f"Bounty of {amount} placed on {player_name}!",
            ephemeral=False
        )
    
    @commands.slash_command(
        name="bounties",
        description="List all active bounties"
    )
    @describe(
        server_id="The server ID (optional)"
    )
    @command_handler(guild_only=True)
    async def list_bounties_command(
        self, 
        interaction: discord.Interaction,
        server_id: Optional[str] = None
    ):
        """
        List all active bounties.
        
        Args:
            interaction: Discord interaction
            server_id: Optional server ID
        """
        # Get the guild ID safely
        guild_id = None
        if hasattr(interaction, 'guild_id') and interaction.guild_id is not None:
            guild_id = interaction.guild_id
        
        if guild_id is None:
            await safely_respond_to_interaction(
                interaction,
                "Could not process your request. Missing guild information.",
                ephemeral=True
            )
            return
        
        # Get bounties using our safe db operation
        bounties_result = await self.get_bounties(
            guild_id=guild_id,
            server_id=server_id
        )
        
        # Handle result with proper error checking
        if not bounties_result.success:
            error_msg = bounties_result.error if bounties_result.error else "Unknown error"
            logger.error(f"Error getting bounties: {error_msg}")
            await safely_respond_to_interaction(
                interaction,
                f"Failed to get bounties: {error_msg}",
                ephemeral=True
            )
            return
        
        # Extract bounties from result
        bounties = bounties_result.result
        
        if not bounties or len(bounties) == 0:
            await safely_respond_to_interaction(
                interaction,
                "No active bounties found.",
                ephemeral=True
            )
            return
        
        # Create embed for bounties
        embed = discord.Embed(
            title="Active Bounties",
            description=f"Total Bounties: {len(bounties)}",
            color=discord.Color.gold()
        )
        
        # Add fields for each bounty with defensive programming
        for i, bounty in enumerate(bounties):
            if i >= 25:  # Discord has a limit of 25 fields
                embed.set_footer(text=f"+ {len(bounties) - 25} more bounties")
                break
                
            try:
                # Safely extract values with defaults
                target_name = bounty.get("target_name", "Unknown")
                amount = bounty.get("amount", 0)
                placer_name = bounty.get("placer_name", "Unknown")
                
                embed.add_field(
                    name=f"{target_name} - {amount}",
                    value=f"Placed by: {placer_name}",
                    inline=True
                )
            except Exception as e:
                logger.error(f"Error processing bounty for embed: {e}")
                continue
        
        # Send the embed
        await safely_respond_to_interaction(interaction, "", embed=embed)
        
    @command_handler(collection_name="bounties")
    @db_operation(operation_type="create_bounty")
    async def create_bounty(
        self, 
        guild_id: Union[str, int], 
        placer_id: Union[str, int],
        target_name: str,
        amount: int,
        server_id: Optional[str] = None
    ) -> SafeMongoDBResult:
        """
        Create a bounty with safe database operations.
        
        Args:
            guild_id: The guild ID
            placer_id: The user ID of the bounty placer
            target_name: The name of the target player
            amount: The bounty amount
            server_id: Optional server ID
            
        Returns:
            SafeMongoDBResult containing the inserted bounty or error
        """
        try:
            # Get placer information for displaying name
            try:
                user = await self.bot.fetch_user(placer_id)
                placer_name = user.display_name if user else "Unknown"
            except Exception as e:
                logger.error(f"Error fetching user {placer_id}: {e}")
                placer_name = "Unknown"
            
            # Convert IDs to strings for MongoDB
            guild_id_str = str(guild_id)
            placer_id_str = str(placer_id)
            
            # Create bounty document
            bounty = {
                "guild_id": guild_id_str,
                "server_id": server_id,
                "placer_id": placer_id_str,
                "placer_name": placer_name,
                "target_name": target_name,
                "amount": amount,
                "status": "active",
                "created_at": datetime.datetime.utcnow().isoformat()
            }
            
            # Insert using the bot's database connection
            if not hasattr(self.bot, 'db') or self.bot.db is None:
                return SafeMongoDBResult.error_result("Database connection not available")
                
            result = await self.bot.db.bounties.insert_one(bounty)
            
            # Return success result with inserted document
            bounty["_id"] = result.inserted_id
            return SafeMongoDBResult.success_result(bounty)
            
        except Exception as e:
            logger.error(f"Error creating bounty: {e}")
            return SafeMongoDBResult.error_result(str(e), None, "bounties")
    
    @command_handler(collection_name="bounties")
    @db_operation(operation_type="get_bounties")
    async def get_bounties(
        self,
        guild_id: Union[str, int],
        server_id: Optional[str] = None
    ) -> SafeMongoDBResult:
        """
        Get all active bounties with safe database operations.
        
        Args:
            guild_id: The guild ID
            server_id: Optional server ID
            
        Returns:
            SafeMongoDBResult containing the bounties or error
        """
        try:
            # Convert guild_id to string for MongoDB
            guild_id_str = str(guild_id)
            
            # Create query
            query = {
                "guild_id": guild_id_str,
                "status": "active"
            }
            
            # Add server_id to query if provided
            if server_id is not None and server_id.strip() != "":
                query["server_id"] = server_id
            
            # Check database connection
            if not hasattr(self.bot, 'db') or self.bot.db is None:
                return SafeMongoDBResult.error_result("Database connection not available")
            
            # Get all active bounties for this guild/server
            bounties = []
            async for doc in self.bot.db.bounties.find(query).sort("amount", -1):
                bounties.append(SafeDocument(doc))
            
            return SafeMongoDBResult.success_result(bounties)
            
        except Exception as e:
            logger.error(f"Error getting bounties: {e}")
            return SafeMongoDBResult.error_result(str(e), None, "bounties")

async def setup(bot):
    await bot.add_cog(Bounties(bot))