"""
Cog Helpers for py-cord 2.6.1 Compatibility

This module provides utility functions for registering commands in cogs
with compatibility across different versions of py-cord and discord.py.
"""

import logging
import inspect
from typing import Optional, List, Any, Dict, Type, Callable, Union, TypeVar, cast

import discord
from discord.ext import commands

from utils.command_imports import (
    is_compatible_with_pycord_261, 
    HAS_APP_COMMANDS,
    PYCORD_261,
    IS_PYCORD
)
from utils.command_handlers import (
    enhanced_slash_command,
    option,
    command_handler
)
from utils.interaction_handlers import safely_respond_to_interaction

logger = logging.getLogger(__name__)

# Types for better type checking
CommandT = TypeVar('CommandT', bound=Callable)
CogT = TypeVar('CogT', bound=commands.Cog)

def register_command_in_cog(
    cog: commands.Cog,
    bot: commands.Bot,
    function: Callable,
    name: Optional[str] = None,
    description: Optional[str] = None,
    guild_ids: Optional[List[int]] = None,
    **kwargs
) -> Any:
    """
    Register a command within a cog, handling py-cord 2.6.1 compatibility
    
    Args:
        cog: The cog to register the command in
        bot: The bot instance
        function: The command function
        name: Optional name for the command
        description: Optional description for the command
        guild_ids: Optional list of guild IDs to register with
        **kwargs: Additional parameters for the command
        
    Returns:
        The registered command
    """
    try:
        # Determine command name if not provided
        if not name:
            name = getattr(function, "name", function.__name__)
            
        # Add description if not provided
        if not description:
            description = getattr(function, "__doc__", "No description provided")
            if description:
                # Format the docstring
                description = description.strip().split("\n")[0]
        
        # Check if we're using py-cord 2.6.1
        if is_compatible_with_pycord_261():
            logger.info(f"Registering command {name} in cog {cog.__class__.__name__} using py-cord 2.6.1 compatibility")
            
            # Use our enhanced decorator
            command = enhanced_slash_command(
                name=name,
                description=description,
                guild_ids=guild_ids,
                **kwargs
            )(function)
            
            # Store command reference in the cog's commands list if it exists
            if hasattr(cog, "commands") and isinstance(cog.commands, list):
                cog.commands.append(command)
                
            return command
        elif HAS_APP_COMMANDS:
            # Discord.py style
            logger.info(f"Registering command {name} in cog {cog.__class__.__name__} using discord.py app_commands")
            
            # Use discord.py's app_commands
            command_tree = getattr(bot, "tree", None)
            if command_tree:
                if guild_ids:
                    # Register as guild command for each guild
                    for guild_id in guild_ids:
                        command_tree.command(
                            name=name,
                            description=description,
                            guild=discord.Object(id=guild_id),
                            **kwargs
                        )(function)
                else:
                    # Register as global command
                    command_tree.command(
                        name=name,
                        description=description,
                        **kwargs
                    )(function)
                
                return function
            else:
                logger.warning(f"Could not find command tree in bot when registering {name}")
                return function
        else:
            # Legacy approach
            logger.info(f"Registering command {name} in cog {cog.__class__.__name__} using legacy method")
            
            # Use standard command decorator
            return commands.command(
                name=name,
                description=description,
                **kwargs
            )(function)
    except Exception as e:
        logger.error(f"Error registering command {name} in cog {cog.__class__.__name__}: {e}")
        return function

def cog_slash_command(
    name: Optional[str] = None,
    description: Optional[str] = None,
    guild_ids: Optional[List[int]] = None,
    **kwargs
) -> Callable[[CommandT], CommandT]:
    """
    Decorator for registering slash commands in cogs with py-cord 2.6.1 compatibility
    
    This decorator uses our compatibility layers to ensure commands work
    across different versions of py-cord and discord.py.
    
    Args:
        name: The name of the command
        description: The description of the command
        guild_ids: List of guild IDs to register with
        **kwargs: Additional parameters for the command
        
    Returns:
        Command decorator function
    """
    def decorator(func: CommandT) -> CommandT:
        # Store command metadata on the function for later registration
        func.__command_name__ = name or func.__name__
        func.__command_description__ = description or (func.__doc__ or "").strip().split("\n")[0]
        func.__command_guild_ids__ = guild_ids
        func.__command_kwargs__ = kwargs
        func.__is_slash_command__ = True
        
        return func
    
    return decorator

class CogWithSlashCommands(commands.Cog):
    """
    Base class for cogs that use slash commands with py-cord 2.6.1 compatibility
    
    This class handles registration of slash commands in the cog's __init__ method,
    using our compatibility layers to ensure commands work across different versions.
    """
    
    def __init__(self, bot: commands.Bot):
        """
        Initialize the cog and register all slash commands
        
        Args:
            bot: The bot instance
        """
        self.bot = bot
        self.registered_commands = []
        
        # Register all methods decorated with @cog_slash_command
        for method_name in dir(self):
            if method_name.startswith('_'):
                continue
                
            method = getattr(self, method_name)
            
            # Check if this method is a slash command
            if callable(method) and hasattr(method, '__is_slash_command__'):
                try:
                    # Register the command
                    registered_command = register_command_in_cog(
                        cog=self,
                        bot=self.bot,
                        function=method,
                        name=getattr(method, '__command_name__', method.__name__),
                        description=getattr(method, '__command_description__', None),
                        guild_ids=getattr(method, '__command_guild_ids__', None),
                        **getattr(method, '__command_kwargs__', {})
                    )
                    
                    # Store reference to the registered command
                    self.registered_commands.append(registered_command)
                except Exception as e:
                    logger.error(f"Error registering slash command {method_name}: {e}")