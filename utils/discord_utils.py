"""
Utility functions for Discord command handling

This module provides utility functions for Discord commands,
focusing on safe database access patterns, server selection,
and message output handling.
"""

import logging
import discord
from discord import app_commands
from discord.ext import commands
from typing import Any, Dict, List, Optional, Tuple, Union, cast

from utils.safe_mongodb import SafeMongoDBResult, SafeDocument

logger = logging.getLogger(__name__)

async def get_guild_document(guild_id: Optional[Union[int, str]]) -> SafeMongoDBResult[SafeDocument]:
    """
    Safely retrieve a guild document from the database
    
    Args:
        guild_id: The guild ID (can be int or str)
        
    Returns:
        SafeMongoDBResult containing the guild document or error
    """
    try:
        # Handle None guild_id
        if guild_id is None:
            return SafeMongoDBResult.create_error("Guild ID is None")
            
        # Convert to string for MongoDB if needed
        guild_id_str = str(guild_id)
        
        # Import bot instance (done here to avoid circular imports)
        from bot import bot
        if not hasattr(bot, 'db') or bot.db is None:
            return SafeMongoDBResult.create_error("Database not initialized")
            
        # Get the document
        guild_doc = await bot.db.guilds.find_one({"guild_id": guild_id_str})
        
        # Return result - may be None if no document found
        return SafeMongoDBResult.ok(SafeDocument(guild_doc))
        
    except Exception as e:
        logger.error(f"Error in get_guild_document: {e}")
        return SafeMongoDBResult.create_error(e)

async def get_server_selection(ctx_or_interaction, guild_id: str, db=None) -> List[Tuple[str, str]]:
    """
    Get server selection options for a guild with safe MongoDB access.
    
    Args:
        ctx_or_interaction: Context or Interaction
        guild_id: Discord guild ID
        db: Optional database connection
        
    Returns:
        List of (server_id, server_name) tuples
    """
    try:
        # Get guild document
        guild_result = await get_guild_document(guild_id)
        
        # Handle errors
        if not guild_result.success:
            return []
            
        guild_doc = guild_result.result
        if not guild_doc:
            return []
            
        # Get server info
        server_info = guild_doc.get("server_info", {})
        if not server_info:
            return []
            
        # Convert to list of tuples
        servers = []
        for server_id, info in server_info.items():
            name = info.get("name", server_id) if isinstance(info, dict) else server_id
            servers.append((server_id, name))
            
        return servers
        
    except Exception as e:
        logger.error(f"Error getting server selection: {e}")
        return []

async def server_id_autocomplete(interaction: discord.Interaction, current: str):
    """
    Autocomplete for server selection with safe database access
    
    Args:
        interaction: Discord interaction
        current: Current input value
        
    Returns:
        List of app_commands.Choice options
    """
    try:
        # Get guild ID safely
        guild_id = None
        if hasattr(interaction, 'guild_id') and interaction.guild_id is not None:
            guild_id = interaction.guild_id
            
        if guild_id is None:
            return []
            
        # Get server options
        servers = await get_server_selection(interaction, guild_id)
        
        # Filter by current input if needed
        if current:
            servers = [s for s in servers if current.lower() in s[0].lower() or current.lower() in s[1].lower()]
            
        # Convert to choices (limit to 25 per Discord API requirements)
        return [
            app_commands.Choice(name=f"{name} ({server_id})", value=server_id)
            for server_id, name in servers[:25]
        ]
        
    except Exception as e:
        logger.error(f"Error in server_id_autocomplete: {e}")
        return []

async def hybrid_send(
    interaction: Union[discord.Interaction, commands.Context], 
    content: Optional[str] = None, 
    embed: Optional[discord.Embed] = None,
    ephemeral: bool = False,
    **kwargs
) -> Optional[Union[discord.Message, discord.WebhookMessage]]:
    """
    A helper function that handles sending messages in both application commands and text commands.
    
    This unified approach simplifies code by allowing the same function call pattern
    regardless of whether the command is a traditional text command or an application command.
    
    Args:
        interaction: Either a discord.Interaction (app command) or commands.Context (text command)
        content: The text content to send
        embed: A discord.Embed to send
        ephemeral: Whether the message should be ephemeral (only visible to the user who triggered the command)
        **kwargs: Additional arguments to pass to the send function
    
    Returns:
        The message that was sent or None if failed
    """
    try:
        # Handle different types
        if isinstance(interaction, discord.Interaction):
            # Application command
            if hasattr(interaction, 'response') and hasattr(interaction.response, 'is_done'):
                # Check if we've already responded
                if interaction.response.is_done():
                    # Use followup for subsequent messages
                    return await interaction.followup.send(
                        content=content, 
                        embed=embed, 
                        ephemeral=ephemeral,
                        **kwargs
                    )
                else:
                    # First response
                    await interaction.response.send_message(
                        content=content, 
                        embed=embed, 
                        ephemeral=ephemeral,
                        **kwargs
                    )
                    # Can't return the message object from response.send_message
                    return None
            else:
                logger.warning("Interaction missing response attribute in hybrid_send")
                return None
                
        elif isinstance(interaction, commands.Context):
            # Text command (ephemeral not supported)
            return await interaction.send(
                content=content, 
                embed=embed,
                **kwargs
            )
            
        else:
            # Unknown type
            logger.error(f"Unknown interaction type in hybrid_send: {type(interaction)}")
            return None
            
    except Exception as e:
        logger.error(f"Error in hybrid_send: {e}")
        return None