"""
Command Handlers for py-cord 2.6.1 Compatibility

This module provides enhanced command decorators and handlers that work
across different versions of py-cord and discord.py.
"""

import functools
import logging
import traceback
import inspect
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union, Type, cast, overload

import discord
from discord.ext import commands

from utils.command_imports import is_compatible_with_pycord_261
from utils.interaction_handlers import get_interaction_user, safely_respond_to_interaction
from utils.safe_mongodb import SafeMongoDBResult, safe_mongo_operation

logger = logging.getLogger(__name__)

# Type variables for better type hinting
FuncT = TypeVar('FuncT', bound=Callable[..., Any])
CommandT = TypeVar('CommandT', bound=Callable[..., Any])

async def defer_interaction(interaction_or_ctx: Union[discord.Interaction, commands.Context], ephemeral: bool = False) -> bool:
    """
    Defer an interaction with py-cord 2.6.1 compatibility
    
    Args:
        interaction_or_ctx: The interaction or context to defer
        ephemeral: Whether the response should be ephemeral
        
    Returns:
        bool: True if the interaction was deferred, False otherwise
    """
    try:
        # Handle interactions
        if isinstance(interaction_or_ctx, discord.Interaction):
            if hasattr(interaction_or_ctx, 'response') and interaction_or_ctx.response:
                if hasattr(interaction_or_ctx.response, 'is_done'):
                    # Check if already responded to
                    if interaction_or_ctx.response.is_done():
                        return False
                
                # Defer the interaction
                await interaction_or_ctx.response.defer(ephemeral=ephemeral)
                return True
        
        # Handle context objects
        elif isinstance(interaction_or_ctx, commands.Context):
            # Context objects don't need deferring in the same way
            return True
            
        return False
    except Exception as e:
        logger.error(f"Error deferring interaction: {e}")
        return False

def command_handler(
    collection_name: Optional[str] = None,
    guild_only: bool = False
) -> Callable[[FuncT], FuncT]:
    """
    Decorator for command handlers with enhanced error handling and MongoDB support
    
    Args:
        collection_name: MongoDB collection name to use (None for commands not using DB)
        guild_only: Whether the command should only be usable in guilds
        
    Returns:
        Decorator function
    """
    def decorator(func: FuncT) -> FuncT:
        @functools.wraps(func)
        async def wrapper(self, ctx_or_interaction, *args, **kwargs):
            # Validate guild_only requirement
            if guild_only:
                guild = None
                if isinstance(ctx_or_interaction, discord.Interaction):
                    guild = ctx_or_interaction.guild
                elif isinstance(ctx_or_interaction, commands.Context):
                    guild = ctx_or_interaction.guild
                
                if not guild:
                    await safely_respond_to_interaction(
                        ctx_or_interaction,
                        content="This command can only be used in a server.",
                        ephemeral=True
                    )
                    return
            
            try:
                # If the function is a command handler, attach the collection name
                if collection_name and hasattr(self, 'bot') and hasattr(self.bot, 'db'):
                    # Add collection as a keyword argument if not already provided
                    if 'collection' not in kwargs:
                        db = self.bot.db()
                        if db:
                            kwargs['collection'] = db[collection_name]
                
                # Call the original function
                return await func(self, ctx_or_interaction, *args, **kwargs)
            except Exception as e:
                # Log the error
                error_msg = f"Error in command handler {func.__name__}: {str(e)}"
                logger.error(error_msg)
                logger.error(traceback.format_exc())
                
                # Respond to the user with the error
                try:
                    await safely_respond_to_interaction(
                        ctx_or_interaction,
                        content=f"An error occurred: {str(e)}",
                        ephemeral=True
                    )
                except Exception as resp_error:
                    logger.error(f"Failed to respond with error message: {resp_error}")
                
                return None
                
        return cast(FuncT, wrapper)
    
    return decorator

def db_operation(operation_type: str) -> Callable[[FuncT], FuncT]:
    """
    Decorator for database operations with enhanced error handling
    
    Args:
        operation_type: Type of database operation (for error logging)
        
    Returns:
        Decorator function
    """
    def decorator(func: FuncT) -> FuncT:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                # Get the actual operation coroutine
                coro = func(*args, **kwargs)
                
                # Execute the operation safely
                result = await safe_mongo_operation(coro, operation_type)
                
                # Return the SafeMongoDBResult
                return result
            except Exception as e:
                logger.error(f"Error in DB operation {func.__name__}: {str(e)}")
                logger.error(traceback.format_exc())
                
                # Return error result
                return SafeMongoDBResult.error_result(str(e), operation_type)
                
        return cast(FuncT, wrapper)
    
    return decorator