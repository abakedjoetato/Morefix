"""
Command Handlers for py-cord 2.6.1 Compatibility

This module provides enhanced command decorators and handlers that work
across different versions of py-cord and discord.py.
"""

import logging
import traceback
import functools
import inspect
from typing import Any, Dict, List, Optional, Union, Callable, TypeVar, Type, cast

import discord
from discord.ext import commands

from utils.discord_patches import app_commands
from utils.interaction_handlers import safely_respond_to_interaction, get_interaction_user

logger = logging.getLogger(__name__)

# Type variables for decorator typing
CommandT = TypeVar('CommandT', bound=Callable)
FuncT = TypeVar('FuncT', bound=Callable)
T = TypeVar('T')
P = TypeVar('P')

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
        # Handle different types of interactions/contexts
        if isinstance(interaction_or_ctx, discord.Interaction):
            # Handle Interaction objects
            if hasattr(interaction_or_ctx, 'response') and hasattr(interaction_or_ctx.response, 'defer'):
                # Check if the interaction is already responded to
                if hasattr(interaction_or_ctx.response, 'is_done') and callable(interaction_or_ctx.response.is_done):
                    if not interaction_or_ctx.response.is_done():
                        await interaction_or_ctx.response.defer(ephemeral=ephemeral)
                        return True
                    else:
                        logger.debug("Interaction already responded to, skipping defer")
                        return False
                else:
                    # No is_done method, try deferring anyway
                    try:
                        await interaction_or_ctx.response.defer(ephemeral=ephemeral)
                        return True
                    except Exception as e:
                        logger.debug(f"Error deferring interaction: {e}")
                        return False
            else:
                logger.warning("Cannot find response.defer on interaction")
                return False
                
        elif isinstance(interaction_or_ctx, commands.Context):
            # For Context objects, respond with "Processing..." if defer not available
            try:
                await interaction_or_ctx.send("Processing...", delete_after=5.0)
                return True
            except Exception as e:
                logger.debug(f"Error sending processing message to Context: {e}")
                return False
                
        else:
            logger.warning(f"Unknown interaction/context type: {type(interaction_or_ctx)}")
            return False
            
    except Exception as e:
        logger.error(f"Error in defer_interaction: {e}")
        return False

def enhanced_slash_command(**kwargs):
    """
    Enhanced slash command decorator with compatibility across py-cord versions
    
    Args:
        **kwargs: Keyword arguments to pass to the slash command constructor
        
    Returns:
        Callable: Slash command decorator
    """
    def decorator(func: CommandT) -> CommandT:
        """Inner decorator for slash command"""
        
        # Try app_commands.command first (preferred)
        if hasattr(app_commands, 'command'):
            cmd = app_commands.command(**kwargs)(func)
            return cmd
            
        # Try commands.slash_command next (py-cord 2.0+)
        elif hasattr(commands, 'slash_command'):
            cmd = commands.slash_command(**kwargs)(func)
            return cmd
            
        # Fallback to discord.app_commands.command (discord.py 2.0+)
        elif hasattr(discord, 'app_commands') and hasattr(discord.app_commands, 'command'):
            cmd = discord.app_commands.command(**kwargs)(func)
            return cmd
            
        # Final fallback to standard command as last resort
        else:
            logger.warning("No slash command decorators found! Falling back to standard command")
            return commands.command(**kwargs)(func)
            
    return decorator

def option(**kwargs):
    """
    Enhanced option decorator for slash command parameters with cross-version compatibility
    
    Args:
        **kwargs: Option parameters like name, description, etc.
        
    Returns:
        Callable: Option decorator
    """
    def decorator(func: FuncT) -> FuncT:
        # Try app_commands.describe first (preferred)
        if hasattr(app_commands, 'describe'):
            return app_commands.describe(**kwargs)(func)
            
        # Try to get from discord directly
        elif hasattr(discord, 'app_commands') and hasattr(discord.app_commands, 'describe'):
            return discord.app_commands.describe(**kwargs)(func)
            
        # In case of failure, return unmodified function
        return func
        
    return decorator

def command_handler(
    name: str = None,
    description: str = None,
    guild_only: bool = False,
    defer: bool = True,
    ephemeral: bool = False,
    error_handling: bool = True
):
    """
    Unified command handler decorator with comprehensive error handling
    
    Args:
        name: Command name override
        description: Command description
        guild_only: Whether the command is guild-only
        defer: Whether to defer the interaction response
        ephemeral: Whether responses should be ephemeral
        error_handling: Whether to enable error handling
        
    Returns:
        Callable: Command handler decorator
    """
    def decorator(func: CommandT) -> CommandT:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Try to get interaction/context
            interaction_or_ctx = None
            for arg in args:
                if isinstance(arg, (discord.Interaction, commands.Context)):
                    interaction_or_ctx = arg
                    break
                    
            if interaction_or_ctx is None:
                # No interaction or context found, just call original function
                return await func(*args, **kwargs)
                
            # Check guild_only restriction
            if guild_only and not getattr(interaction_or_ctx, 'guild', None):
                # Guild check failed
                if isinstance(interaction_or_ctx, discord.Interaction):
                    await safely_respond_to_interaction(
                        interaction_or_ctx,
                        "This command can only be used in servers!",
                        ephemeral=True
                    )
                else:
                    await interaction_or_ctx.send("This command can only be used in servers!")
                return
                
            try:
                # Defer response if needed
                if defer:
                    await defer_interaction(interaction_or_ctx, ephemeral=ephemeral)
                    
                # Call original function
                return await func(*args, **kwargs)
                
            except Exception as e:
                # Handle any errors
                if error_handling:
                    await handle_command_error(interaction_or_ctx, e)
                else:
                    # Re-raise if error handling is disabled
                    raise
                    
        # Apply command decorators
        kwargs = {}
        if name:
            kwargs['name'] = name
        if description:
            kwargs['description'] = description
            
        # Apply the enhanced slash command decorator
        return enhanced_slash_command(**kwargs)(wrapper)
        
    return decorator

async def handle_command_error(ctx_or_interaction, error, custom_message=None):
    """
    Handle command errors with detailed error information
    
    Args:
        ctx_or_interaction: Context or interaction where the error occurred
        error: The exception that was raised
        custom_message: Optional custom error message to display
        
    Returns:
        None
    """
    # Log the error
    logger.error(f"Command error: {error}", exc_info=True)
    
    # Create error message
    error_message = custom_message or f"An error occurred: {str(error)}"
    
    try:
        # Determine if this is an interaction or context
        if isinstance(ctx_or_interaction, discord.Interaction):
            # Handle Interaction
            embed = discord.Embed(
                title="Error",
                description=error_message,
                color=discord.Color.red()
            )
            
            # Add traceback if debug mode
            if logger.level <= logging.DEBUG:
                tb = ''.join(traceback.format_exception(type(error), error, error.__traceback__))
                if len(tb) > 1000:
                    tb = tb[:997] + "..."
                embed.add_field(name="Debug Info", value=f"```py\n{tb}\n```", inline=False)
                
            await safely_respond_to_interaction(ctx_or_interaction, embed)
            
        else:
            # Handle Context
            embed = discord.Embed(
                title="Error",
                description=error_message,
                color=discord.Color.red()
            )
            
            await ctx_or_interaction.send(embed=embed)
            
    except Exception as e:
        # If error handling fails, just log it
        logger.error(f"Error while handling command error: {e}", exc_info=True)