"""
Discord Compatibility Patches for py-cord 2.6.1

This module provides compatibility patches for py-cord 2.6.1 to make it work with
code written for discord.py's app_commands API.

Usage:
    # Replace imports in your cogs:
    # from discord import app_commands
    from utils.discord_patches import app_commands
"""

import sys
import logging
import inspect
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, Union, cast

import discord
from discord.ext import commands

logger = logging.getLogger(__name__)

# Check if we're using py-cord or discord.py
USING_PYCORD = False
try:
    import discord
    if hasattr(discord, "__version__"):
        version = discord.__version__
        if version.startswith("2."):
            USING_PYCORD = True
            logger.info(f"Detected py-cord version: {version}")
        else:
            logger.info(f"Detected discord.py version: {version}")
    else:
        logger.warning("Could not determine discord library version")
except ImportError:
    logger.error("Could not import discord library")

# Create a namespace for app_commands
class AppCommandModule:
    """Compatibility module for discord.py's app_commands"""
    
    @staticmethod
    def command(*, name: Optional[str] = None, description: Optional[str] = None, **kwargs):
        """
        Command decorator compatible with both discord.py and py-cord
        
        Args:
            name: Name of the command
            description: Description of the command
            **kwargs: Additional arguments
            
        Returns:
            Command decorator
        """
        def decorator(func):
            # For py-cord, we use slash_command
            if USING_PYCORD:
                # Handle guild_only parameter which is different in py-cord
                if 'guild_only' in kwargs:
                    kwargs['guild_ids'] = kwargs.pop('guild_only')
                    
                # Create the command
                return commands.slash_command(
                    name=name,
                    description=description,
                    **kwargs
                )(func)
            else:
                # For discord.py, we would use app_commands.command
                # (This branch won't be taken in our case)
                return func
                
        return decorator
    
    class Choice:
        """Choice class for application command options"""
        
        def __init__(self, name: str, value: Union[str, int, float]):
            self.name = name
            self.value = value
            
        def to_dict(self) -> dict:
            return {
                'name': self.name,
                'value': self.value
            }
    
    class Group:
        """
        Command group compatible with both discord.py and py-cord
        
        Args:
            name: Name of the group
            description: Description of the group
            **kwargs: Additional arguments
        """
        
        def __init__(self, *, name: Optional[str] = None, description: Optional[str] = None, **kwargs):
            self.name = name
            self.description = description
            self.kwargs = kwargs
            self.commands = []
            
        def command(self, *, name: Optional[str] = None, description: Optional[str] = None, **kwargs):
            """
            Create a command within this group
            
            Args:
                name: Name of the command
                description: Description of the command
                **kwargs: Additional arguments
                
            Returns:
                Command decorator
            """
            def decorator(func):
                if USING_PYCORD:
                    # For py-cord, we use a slash command in a group
                    # Handle guild_only parameter
                    if 'guild_only' in kwargs:
                        kwargs['guild_ids'] = kwargs.pop('guild_only')
                        
                    # Create the command
                    cmd = commands.slash_command(
                        name=name or self.name,
                        description=description or self.description,
                        **{**self.kwargs, **kwargs}
                    )(func)
                    
                    self.commands.append(cmd)
                    return cmd
                else:
                    # For discord.py (not used in our case)
                    return func
                    
            return decorator

# Create a single instance of the app_commands module
app_commands = AppCommandModule()

# Add describe function for parameters (used in many cogs)
def describe(**kwargs):
    """
    Decorator to describe command parameters
    
    Args:
        **kwargs: Parameter descriptions
        
    Returns:
        Function decorator
    """
    def decorator(func):
        # In py-cord, we don't need this decorator
        # The description is already handled in the slash_command options
        return func
    return decorator

# Add the describe function to the app_commands module
app_commands.describe = describe

# Function to check if a command is already registered
def is_command_registered(bot, command_name):
    """
    Check if a command is already registered
    
    Args:
        bot: Bot instance
        command_name: Name of the command
        
    Returns:
        bool: True if the command is registered, False otherwise
    """
    for command in bot.application_commands:
        if command.name == command_name:
            return True
    return False