"""
Compatibility layer for discord.py and py-cord differences

This module provides functions and classes to abstract away the differences
between discord.py and py-cord command system implementations.
"""

import logging
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union, cast

import discord
from discord.ext import commands

from utils.command_imports import is_compatible_with_pycord_261

logger = logging.getLogger(__name__)

# Type variables for better type hinting
CommandT = TypeVar('CommandT', bound=Callable[..., Any])
FuncT = TypeVar('FuncT', bound=Callable[..., Any])

class AppCommandOptionType(Enum):
    """Compatible enum for app command option types"""
    STRING = 3
    INTEGER = 4
    BOOLEAN = 5
    USER = 6
    CHANNEL = 7
    ROLE = 8
    MENTIONABLE = 9
    NUMBER = 10
    ATTACHMENT = 11

def command(
    name: Optional[str] = None,
    description: Optional[str] = None,
    **kwargs: Any
) -> Callable[[CommandT], CommandT]:
    """
    A compatible decorator for creating slash commands.
    
    This handles the differences between discord.py's app_commands.command and
    py-cord's slash_command.
    
    Args:
        name: The name of the command
        description: The description of the command
        **kwargs: Additional arguments to pass to the command
        
    Returns:
        Command decorator function
    """
    def decorator(func: CommandT) -> CommandT:
        # Handle based on library version
        if is_compatible_with_pycord_261():
            # For py-cord 2.6.1, use the discord.commands.slash_command decorator
            slash_command = commands.slash_command(
                name=name,
                description=description,
                **kwargs
            )
            return slash_command(func)
        else:
            # For discord.py or other versions, use app_commands.command
            from utils.discord_patches import app_commands
            app_command = app_commands.command(
                name=name,
                description=description,
                **kwargs
            )
            return app_command(func)
    
    return decorator

def describe(**kwargs: str) -> Callable[[CommandT], CommandT]:
    """
    A compatible decorator for describing command parameters.
    
    This handles the differences between discord.py's app_commands.describe and
    py-cord's describe.
    
    Args:
        **kwargs: Parameter descriptions
        
    Returns:
        Command decorator function
    """
    def decorator(func: CommandT) -> CommandT:
        # For py-cord 2.6.1, use commands.describe; otherwise use app_commands.describe
        if is_compatible_with_pycord_261():
            return commands.describe(**kwargs)(func)
        else:
            from utils.discord_patches import app_commands
            return app_commands.describe(**kwargs)(func)
    
    return decorator

def choices(**kwargs: List[Union[str, int, float]]) -> Callable[[CommandT], CommandT]:
    """
    A compatible decorator for adding choices to command parameters.
    
    This handles the differences between discord.py's app_commands.choices and
    py-cord's choices.
    
    Args:
        **kwargs: Parameter choices
        
    Returns:
        Command decorator function
    """
    def decorator(func: CommandT) -> CommandT:
        # For py-cord 2.6.1, use commands.choices; otherwise use app_commands.choices
        if is_compatible_with_pycord_261():
            return commands.choices(**kwargs)(func)
        else:
            from utils.discord_patches import app_commands
            return app_commands.choices(**kwargs)(func)
    
    return decorator

def guild_only() -> Callable[[CommandT], CommandT]:
    """
    A compatible decorator for making commands guild-only.
    
    This handles the differences between discord.py and py-cord.
    
    Returns:
        Command decorator function
    """
    def decorator(func: CommandT) -> CommandT:
        # Set attribute that can be checked during command execution
        setattr(func, "__guild_only__", True)
        
        # For py-cord 2.6.1, use commands.guild_only; otherwise use our own implementation
        if is_compatible_with_pycord_261():
            return commands.guild_only()(func)
        else:
            # For discord.py, we'll handle this in the command_handler
            return func
    
    return decorator

def autocomplete(
    **kwargs: Callable[[discord.Interaction, str], Any]
) -> Callable[[CommandT], CommandT]:
    """
    A compatible decorator for adding autocomplete to command parameters.
    
    This handles the differences between discord.py's app_commands.autocomplete and
    py-cord's autocomplete.
    
    Args:
        **kwargs: Parameter autocomplete functions
        
    Returns:
        Command decorator function
    """
    def decorator(func: CommandT) -> CommandT:
        # For py-cord 2.6.1, use commands.autocomplete; otherwise use app_commands.autocomplete
        if is_compatible_with_pycord_261():
            return commands.autocomplete(**kwargs)(func)
        else:
            from utils.discord_patches import app_commands
            return app_commands.autocomplete(**kwargs)(func)
    
    return decorator