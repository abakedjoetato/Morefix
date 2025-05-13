"""
Command import utilities

This module provides utility functions for importing commands and determining
compatibility with different Discord library versions.
"""

import logging
import sys
import re
import importlib
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar, Union, cast

logger = logging.getLogger(__name__)

def is_compatible_with_pycord_261() -> bool:
    """
    Check if we're running with py-cord 2.6.1
    
    Returns:
        bool: True if running with py-cord 2.6.1, False otherwise
    """
    # Try to import discord
    try:
        import discord
        # Check if version is 2.6.1
        version = getattr(discord, "__version__", "unknown")
        logger.debug(f"Detected Discord library version: {version}")
        return version == "2.6.1"
    except ImportError:
        logger.warning("Could not import discord module")
        return False

def get_discord_version() -> str:
    """
    Get the version of discord library we're using
    
    Returns:
        str: Version of discord library or "unknown" if not found
    """
    try:
        import discord
        return getattr(discord, "__version__", "unknown")
    except ImportError:
        return "unknown"

def import_commands():
    """
    Import the appropriate commands module based on the Discord library version
    
    Returns:
        module: The commands module
    """
    import discord
    
    if is_compatible_with_pycord_261():
        # py-cord has commands as a property of the discord.ext module
        from discord.ext import commands
        logger.debug("Using py-cord 2.6.1 commands")
        return commands
    else:
        # discord.py has commands as a property of the discord.ext module
        from discord.ext import commands
        logger.debug("Using discord.py commands")
        return commands

def import_app_commands():
    """
    Import the appropriate app_commands module based on the Discord library version
    
    Returns:
        module: The app_commands module (or a compatibility layer)
    """
    if is_compatible_with_pycord_261():
        # For py-cord 2.6.1, we use our compatibility layer
        logger.debug("Using py-cord 2.6.1 app_commands compatibility layer")
        from utils.app_commands_patch import AppCommandsBridge
        return AppCommandsBridge()
    else:
        # For discord.py, we can use the built-in app_commands
        from discord import app_commands
        logger.debug("Using discord.py app_commands")
        return app_commands

# Type for command function decorators 
F = TypeVar('F', bound=Callable[..., Any])

def get_command_decorator(guild_only: bool = False) -> Callable[[F], F]:
    """
    Get the appropriate command decorator based on the Discord library version
    
    Args:
        guild_only: Whether the command should be guild-only
        
    Returns:
        Callable: The command decorator function
    """
    commands = import_commands()
    
    if is_compatible_with_pycord_261():
        # py-cord uses the slash_command decorator
        def decorator(func: F) -> F:
            cmd = commands.slash_command(guild_only=guild_only)(func)
            return cast(F, cmd)
        return decorator
    else:
        # For discord.py, we use the command decorator from app_commands
        app_commands = import_app_commands()
        
        def decorator(func: F) -> F:
            @app_commands.command()
            async def wrapper(*args, **kwargs):
                return await func(*args, **kwargs)
                
            # Copy attributes
            for attr_name in dir(func):
                if not attr_name.startswith('__'):
                    setattr(wrapper, attr_name, getattr(func, attr_name))
                    
            return cast(F, wrapper)
            
        return decorator