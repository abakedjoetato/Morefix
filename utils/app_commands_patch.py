"""
App Commands Patch for py-cord 2.6.1

This module provides a compatibility layer for app_commands functionality
when using py-cord 2.6.1, which doesn't provide the app_commands module
in the same way as discord.py.
"""

import inspect
import logging
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union, cast

import discord
from discord.ext import commands

logger = logging.getLogger(__name__)

# Type variables for better type hinting
CommandT = TypeVar('CommandT', bound=Callable[..., Any])

class CommandType(Enum):
    """
    Compatible enum for command types
    
    Mirrors discord.py's app_commands.CommandType
    """
    CHAT_INPUT = 1
    USER = 2
    MESSAGE = 3

class AppCommandOptionType(Enum):
    """
    Compatible enum for app command option types
    
    Mirrors discord.py's app_commands.AppCommandOptionType
    """
    SUBCOMMAND = 1
    SUBCOMMAND_GROUP = 2
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
    A compatibility wrapper for app_commands.command
    
    Args:
        name: The name of the command
        description: The description of the command
        **kwargs: Additional arguments for the command
        
    Returns:
        A decorator that converts a function into an application command
    """
    def decorator(func: CommandT) -> CommandT:
        # Extract the name from the function if not provided
        command_name = name or func.__name__
        command_description = description or (func.__doc__ or "No description provided")
        
        # Use slash_command from discord.ext.commands
        slash_command = commands.slash_command(
            name=command_name,
            description=command_description,
            **kwargs
        )
        
        # Apply the decorator
        return slash_command(func)
    
    return decorator

def describe(**kwargs: str) -> Callable[[CommandT], CommandT]:
    """
    A compatibility wrapper for app_commands.describe
    
    Args:
        **kwargs: Parameter name to description mapping
        
    Returns:
        A decorator that adds descriptions to command parameters
    """
    def decorator(func: CommandT) -> CommandT:
        # Use commands.describe from discord.ext
        return commands.describe(**kwargs)(func)
    
    return decorator

def choices(**kwargs: List[Union[str, int, float]]) -> Callable[[CommandT], CommandT]:
    """
    A compatibility wrapper for app_commands.choices
    
    Args:
        **kwargs: Parameter name to choices mapping
        
    Returns:
        A decorator that adds choices to command parameters
    """
    def decorator(func: CommandT) -> CommandT:
        # Use commands.choices from discord.ext
        return commands.choices(**kwargs)(func)
    
    return decorator

def guild_only() -> Callable[[CommandT], CommandT]:
    """
    A compatibility wrapper for app_commands.guild_only
    
    Returns:
        A decorator that restricts commands to guilds
    """
    def decorator(func: CommandT) -> CommandT:
        # Use commands.guild_only from discord.ext
        return commands.guild_only()(func)
    
    return decorator

def autocomplete(
    **kwargs: Callable[[discord.Interaction, str], Any]
) -> Callable[[CommandT], CommandT]:
    """
    A compatibility wrapper for app_commands.autocomplete
    
    Args:
        **kwargs: Parameter name to autocomplete function mapping
        
    Returns:
        A decorator that adds autocomplete to command parameters
    """
    def decorator(func: CommandT) -> CommandT:
        # Use commands.autocomplete from discord.ext
        return commands.autocomplete(**kwargs)(func)
    
    return decorator