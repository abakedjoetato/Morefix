"""
Compatibility layer for Discord commands
"""

import logging
import functools
from typing import Any, Callable, Dict, List, Optional, Union, cast

import discord
from discord.ext import commands

logger = logging.getLogger(__name__)

# Import directly from utils.app_commands to ensure we have our patched version
from utils.app_commands import command as app_command
from utils.app_commands import describe as app_describe
from utils.app_commands import choices as app_choices
from utils.app_commands import Choice as AppChoice

def command(name: Optional[str] = None, **kwargs):
    """
    Create a slash command compatible with py-cord 2.6.1
    
    Args:
        name: Command name
        **kwargs: Additional arguments
        
    Returns:
        Command decorator
    """
    logger.debug(f"Creating command with name: {name}")
    return app_command(name=name, **kwargs)

def describe(**kwargs):
    """
    Add parameter descriptions to a slash command
    
    Args:
        **kwargs: Parameter descriptions
        
    Returns:
        Command decorator
    """
    return app_describe(**kwargs)

def choices(**kwargs):
    """
    Add parameter choices to a slash command
    
    Args:
        **kwargs: Parameter choices
        
    Returns:
        Command decorator
    """
    return app_choices(**kwargs)

def guild_only():
    """
    Make a slash command guild-only, compatible with py-cord 2.6.1
    
    Returns:
        Command decorator
    """
    def decorator(func):
        # Try different approaches to support both discord.py and py-cord
        try:
            # py-cord 2.6.1 approach
            func.__guild_only__ = True
        except:
            # For other libraries, try to set it as a parameter
            try:
                setattr(func, "guild_only", True)
            except:
                logger.debug("Failed to set guild_only")
                
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)
        return wrapper
    return decorator

# For compatibility, also provide direct access to the Choice class
Choice = AppChoice