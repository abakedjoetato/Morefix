"""
Discord utility functions for cogs
"""

import logging
import asyncio
from typing import Any, Callable, Dict, List, Optional, Union

import discord
from discord.ext import commands

from utils.safe_mongodb import SafeMongoDBResult, SafeDocument

logger = logging.getLogger(__name__)

async def server_id_autocomplete(ctx):
    """Autocomplete for server IDs
    
    Args:
        ctx: The AutocompleteContext
        
    Returns:
        List of guild IDs that the bot is connected to
    """
    try:
        guilds = ctx.bot.guilds
        choices = [
            (f"{guild.name} ({guild.id})", str(guild.id)) 
            for guild in guilds[:25]
        ]
        return choices
    except Exception as e:
        logger.error(f"Error in server_id_autocomplete: {e}")
        return [("Error fetching servers", "0")]

async def command_handler(coro, *args, **kwargs):
    """
    Wrapper for command handling with proper error handling
    
    Args:
        coro: The coroutine to execute
        args: Arguments to pass to the coroutine
        kwargs: Keyword arguments to pass to the coroutine
        
    Returns:
        The result of the coroutine
    """
    try:
        return await coro(*args, **kwargs)
    except Exception as e:
        logger.error(f"Error in command_handler: {e}")
        raise

async def defer_interaction(interaction):
    """
    Safely defer an interaction with error handling
    
    Args:
        interaction: The interaction to defer
        
    Returns:
        True if deferred successfully, False otherwise
    """
    try:
        if not interaction.response.is_done():
            await interaction.response.defer()
            return True
    except Exception as e:
        logger.error(f"Failed to defer interaction: {e}")
    return False

async def safely_respond_to_interaction(
    interaction, 
    message: str, 
    ephemeral: bool = False, 
    embed: Optional[discord.Embed] = None
):
    """
    Safely respond to an interaction with error handling
    
    Args:
        interaction: The interaction to respond to
        message: The message to send
        ephemeral: Whether the response should be ephemeral
        embed: Optional embed to send
        
    Returns:
        True if responded successfully, False otherwise
    """
    try:
        if not interaction.response.is_done():
            if embed:
                await interaction.response.send_message(message, ephemeral=ephemeral, embed=embed)
            else:
                await interaction.response.send_message(message, ephemeral=ephemeral)
            return True
        else:
            if embed:
                await interaction.followup.send(message, ephemeral=ephemeral, embed=embed)
            else:
                await interaction.followup.send(message, ephemeral=ephemeral)
            return True
    except Exception as e:
        logger.error(f"Failed to respond to interaction: {e}")
        return False

async def db_operation(db_func, *args, **kwargs):
    """
    Wrapper for database operations with proper error handling
    
    Args:
        db_func: The database function to execute
        args: Arguments to pass to the function
        kwargs: Keyword arguments to pass to the function
        
    Returns:
        The result of the database function
    """
    try:
        return await db_func(*args, **kwargs)
    except Exception as e:
        logger.error(f"Error in db_operation: {e}")
        return SafeMongoDBResult.error_result(f"Database error: {e}")