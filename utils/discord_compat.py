"""
Discord Compatibility Module for py-cord 2.6.1

Provides compatibility functions and decorators to work with py-cord 2.6.1
"""

import logging
import functools
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union, cast

import discord
from utils.command_imports import is_compatible_with_pycord_261

# Import the app_commands module from our patches
from utils.discord_patches import app_commands

logger = logging.getLogger(__name__)

# Type variables for better type hinting
CommandT = TypeVar('CommandT', bound=Callable[..., Any])

def command(
    name: Optional[str] = None,
    description: Optional[str] = None,
    **kwargs: Any
) -> Callable[[CommandT], CommandT]:
    """
    Compatibility wrapper for slash command decorators
    
    Args:
        name: The name of the command
        description: The description of the command
        **kwargs: Additional arguments for the command
        
    Returns:
        A decorator that converts a function into a slash command
    """
    # For py-cord 2.6.1, use our app_commands patch
    if is_compatible_with_pycord_261():
        return app_commands.command(name=name, description=description, **kwargs)
    
    # For discord.py, use the native app_commands
    try:
        from discord import app_commands as native_app_commands
        return native_app_commands.command(name=name, description=description, **kwargs)
    except ImportError:
        logger.error("Failed to import discord.app_commands. Falling back to commands.command.")
        # Fallback to commands.command as a last resort
        from discord.ext import commands
        return commands.command(name=name, description=description, **kwargs)

def describe(**kwargs: str) -> Callable[[CommandT], CommandT]:
    """
    Compatibility wrapper for describe decorator
    
    Args:
        **kwargs: Parameter name to description mapping
        
    Returns:
        A decorator that adds descriptions to command parameters
    """
    # For py-cord 2.6.1, use our app_commands patch
    if is_compatible_with_pycord_261():
        return app_commands.describe(**kwargs)
    
    # For discord.py, use the native app_commands
    try:
        from discord import app_commands as native_app_commands
        return native_app_commands.describe(**kwargs)
    except ImportError:
        logger.error("Failed to import discord.app_commands.describe. Using no-op decorator.")
        # Return a no-op decorator as fallback
        def noop_decorator(func: CommandT) -> CommandT:
            return func
        return noop_decorator

def guild_only() -> Callable[[CommandT], CommandT]:
    """
    Compatibility wrapper for guild_only decorator
    
    Returns:
        A decorator that restricts commands to guilds
    """
    # For py-cord 2.6.1, use our app_commands patch
    if is_compatible_with_pycord_261():
        return app_commands.guild_only()
    
    # For discord.py, use the native app_commands
    try:
        from discord import app_commands as native_app_commands
        return native_app_commands.guild_only()
    except ImportError:
        logger.error("Failed to import discord.app_commands.guild_only. Using no-op decorator.")
        # Return a no-op decorator as fallback
        def noop_decorator(func: CommandT) -> CommandT:
            return func
        return noop_decorator

def choices(**kwargs: List[Union[str, int, float]]) -> Callable[[CommandT], CommandT]:
    """
    Compatibility wrapper for choices decorator
    
    Args:
        **kwargs: Parameter name to choices mapping
        
    Returns:
        A decorator that adds choices to command parameters
    """
    # For py-cord 2.6.1, use our app_commands patch
    if is_compatible_with_pycord_261():
        return app_commands.choices(**kwargs)
    
    # For discord.py, use the native app_commands
    try:
        from discord import app_commands as native_app_commands
        return native_app_commands.choices(**kwargs)
    except ImportError:
        logger.error("Failed to import discord.app_commands.choices. Using no-op decorator.")
        # Return a no-op decorator as fallback
        def noop_decorator(func: CommandT) -> CommandT:
            return func
        return noop_decorator