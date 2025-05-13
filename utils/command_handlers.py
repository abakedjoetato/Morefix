"""
Command handler utilities for Discord bot

This module provides utility functions for handling Discord commands with database operations.
"""

import logging
import functools
from typing import Any, Callable, Dict, List, Optional, Union, TypeVar, cast, Coroutine

import discord
from discord.ext import commands
from discord import Interaction, InteractionType, Member, User

from utils.safe_mongodb import SafeMongoDBResult
from utils.interaction_handlers import respond_to_interaction

logger = logging.getLogger(__name__)

# Type variable for command functions
F = TypeVar('F', bound=Callable[..., Coroutine])

def guild_only_command(func: F) -> F:
    """
    Decorator to make a command guild-only
    
    Args:
        func: The command function
        
    Returns:
        The decorated function
    """
    @functools.wraps(func)
    async def wrapper(self, ctx, *args, **kwargs):
        # Check if this is a guild command
        guild = None
        if hasattr(ctx, 'guild'):
            guild = ctx.guild
        
        # Handle both context and interaction objects
        if guild is None:
            # No guild, this is a DM
            if hasattr(ctx, 'response') and hasattr(ctx.response, 'send_message'):
                # This is an Interaction
                await respond_to_interaction(
                    ctx,
                    content="This command can only be used in a server, not in DMs.",
                    ephemeral=True
                )
            else:
                # This is a Context
                await ctx.send("This command can only be used in a server, not in DMs.")
            return
            
        # Guild exists, continue with command
        return await func(self, ctx, *args, **kwargs)
        
    return cast(F, wrapper)

def handle_db_result(
    collection_name: Optional[str] = None,
    error_message: str = "Failed to perform database operation",
    success_message: Optional[str] = None,
    include_error_details: bool = True,
    send_error_ephemeral: bool = True
):
    """
    Decorator for handling database operation results in commands
    
    Args:
        collection_name: Name of the collection for error reporting
        error_message: Default error message
        success_message: Optional success message
        include_error_details: Whether to include error details in the message
        send_error_ephemeral: Whether to send error messages as ephemeral
        
    Returns:
        The decorator function
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(self, ctx, *args, **kwargs):
            try:
                result = await func(self, ctx, *args, **kwargs)
                
                # Handle SafeMongoDBResult
                if isinstance(result, SafeMongoDBResult):
                    if result.success:
                        # Success case
                        if success_message:
                            if hasattr(ctx, 'response') and hasattr(ctx.response, 'send_message'):
                                # This is an Interaction
                                await respond_to_interaction(
                                    ctx,
                                    content=success_message
                                )
                            else:
                                # This is a Context
                                await ctx.send(success_message)
                        return result.data
                    else:
                        # Error case
                        error_detail = f": {result.error}" if include_error_details and result.error else ""
                        full_error = f"{error_message}{error_detail}"
                        
                        if hasattr(ctx, 'response') and hasattr(ctx.response, 'send_message'):
                            # This is an Interaction
                            await respond_to_interaction(
                                ctx,
                                content=full_error,
                                ephemeral=send_error_ephemeral
                            )
                        else:
                            # This is a Context
                            await ctx.send(full_error)
                        return None
                else:
                    # Regular result, just return it
                    return result
                    
            except Exception as e:
                logger.error(f"Error in command handler for {func.__name__}: {e}")
                
                # Try to send an error message
                try:
                    error_detail = f": {str(e)}" if include_error_details else ""
                    full_error = f"{error_message}{error_detail}"
                    
                    if hasattr(ctx, 'response') and hasattr(ctx.response, 'send_message'):
                        # This is an Interaction
                        await respond_to_interaction(
                            ctx,
                            content=full_error,
                            ephemeral=send_error_ephemeral
                        )
                    else:
                        # This is a Context
                        await ctx.send(full_error)
                except Exception as e2:
                    logger.error(f"Failed to send error message: {e2}")
                return None
                
        return cast(F, wrapper)
        
    return decorator

def create_collection_handler(collection_name: str):
    """
    Create a handler for a specific collection
    
    Args:
        collection_name: Name of the collection
        
    Returns:
        A specialized handle_db_result decorator
    """
    def collection_handler(
        error_message: str = f"Failed to access {collection_name} data",
        success_message: Optional[str] = None,
        include_error_details: bool = True,
        send_error_ephemeral: bool = True
    ):
        return handle_db_result(
            collection_name=collection_name,
            error_message=error_message,
            success_message=success_message,
            include_error_details=include_error_details,
            send_error_ephemeral=send_error_ephemeral
        )
        
    return collection_handler

def get_user_from_context(ctx: Union[commands.Context, Interaction]) -> Optional[Union[User, Member]]:
    """
    Get the user from a context or interaction
    
    Args:
        ctx: Command context or interaction
        
    Returns:
        The user or member, or None if not found
    """
    # For commands.Context, use author
    if hasattr(ctx, 'author'):
        return ctx.author
        
    # For Interaction, use user
    if hasattr(ctx, 'user'):
        return ctx.user
        
    # For other types, try other attributes
    if hasattr(ctx, 'message') and hasattr(ctx.message, 'author'):
        return ctx.message.author
        
    return None
    
def get_guild_from_context(ctx: Union[commands.Context, Interaction]) -> Optional[discord.Guild]:
    """
    Get the guild from a context or interaction
    
    Args:
        ctx: Command context or interaction
        
    Returns:
        The guild, or None if not found
    """
    # Try direct guild attribute
    if hasattr(ctx, 'guild'):
        return ctx.guild
        
    # For other types, try other attributes
    if hasattr(ctx, 'message') and hasattr(ctx.message, 'guild'):
        return ctx.message.guild
        
    return None