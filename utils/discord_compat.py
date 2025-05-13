"""
Discord Compatibility Module

This module provides compatibility between different Discord library versions,
specifically focused on discord.py and py-cord 2.6.1.
"""

import logging
import sys
import types
import inspect
from typing import Any, Callable, Dict, List, Optional, Tuple, Union, TypeVar, cast, Generic

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Attempt to import discord
try:
    import discord
    from discord.ext import commands
    HAS_DISCORD = True
except ImportError:
    HAS_DISCORD = False
    logger.error("Failed to import discord. Discord functionality will not be available.")
    # Create mock modules if discord is not available
    discord = types.ModuleType('discord')
    commands = types.ModuleType('commands')
    setattr(sys.modules, 'discord', discord)
    setattr(sys.modules, 'discord.ext.commands', commands)

# Attempt to import app_commands
try:
    from discord import app_commands
    HAS_APP_COMMANDS = True
except ImportError:
    try:
        # Try alternate import for older versions
        from discord.ext.commands import app_commands
        HAS_APP_COMMANDS = True
    except ImportError:
        HAS_APP_COMMANDS = False
        logger.warning("Failed to import app_commands. Slash commands may not be available.")
        # Create mock module if app_commands is not available
        app_commands = types.ModuleType('app_commands')
        setattr(sys.modules, 'discord.app_commands', app_commands)
        
        # Create essential mock classes
        class MockCommand:
            def __init__(self, **kwargs):
                for key, value in kwargs.items():
                    setattr(self, key, value)
                    
            def __call__(self, func):
                return func
                
        # Add mock classes to app_commands
        app_commands.Command = MockCommand
        app_commands.Group = MockCommand
        app_commands.describe = lambda **kwargs: lambda f: f
        app_commands.guild_only = lambda: lambda f: f
        app_commands.choices = lambda **kwargs: lambda f: f

# Type variables for generic function decorators
T = TypeVar('T')
CommandT = TypeVar('CommandT', bound='commands.Command')

# Decorator functions for backward compatibility
def decorator(func: T) -> T:
    """Generic decorator function for compatibility."""
    return func

def command(name: Optional[str] = None, **attrs) -> Callable[[T], T]:
    """
    Decorator for creating a command with compatibility across versions.
    
    Args:
        name: Name of the command
        **attrs: Additional attributes for the command
        
    Returns:
        Command decorator
    """
    def decorator(func: T) -> T:
        if HAS_DISCORD:
            cmd = commands.command(name=name, **attrs)(func)
            return cast(T, cmd)
        return func
    return decorator

def describe(**kwargs) -> Callable[[T], T]:
    """
    Decorator for describing command parameters with compatibility across versions.
    
    Args:
        **kwargs: Parameter descriptions
        
    Returns:
        Describe decorator
    """
    def decorator(func: T) -> T:
        if HAS_DISCORD and hasattr(commands, 'describe'):
            return cast(T, commands.describe(**kwargs)(func))
        elif HAS_APP_COMMANDS:
            return cast(T, app_commands.describe(**kwargs)(func))
        return func
    return decorator

def guild_only() -> Callable[[T], T]:
    """
    Decorator for restricting commands to guilds with compatibility across versions.
    
    Returns:
        Guild-only decorator
    """
    def decorator(func: T) -> T:
        if HAS_DISCORD and hasattr(commands, 'guild_only'):
            return cast(T, commands.guild_only()(func))
        elif HAS_APP_COMMANDS:
            return cast(T, app_commands.guild_only()(func))
        return func
    return decorator

def choices(**kwargs) -> Callable[[T], T]:
    """
    Decorator for adding choices to command parameters with compatibility across versions.
    
    Args:
        **kwargs: Parameter choices
        
    Returns:
        Choices decorator
    """
    def decorator(func: T) -> T:
        if HAS_DISCORD and hasattr(commands, 'choices'):
            return cast(T, commands.choices(**kwargs)(func))
        elif HAS_APP_COMMANDS:
            return cast(T, app_commands.choices(**kwargs)(func))
        return func
    return decorator

def group(name: Optional[str] = None, **attrs) -> Callable[[T], T]:
    """
    Decorator for creating a command group with compatibility across versions.
    
    Args:
        name: Name of the group
        **attrs: Additional attributes for the group
        
    Returns:
        Group decorator
    """
    def decorator(func: T) -> T:
        if HAS_DISCORD:
            if not name and hasattr(func, '__name__'):
                group_name = func.__name__
            else:
                group_name = name or ""
                
            cmd = commands.group(name=group_name, **attrs)(func)
            return cast(T, cmd)
        return func
    return decorator

def slash_command(name: Optional[str] = None, **attrs) -> Callable[[T], T]:
    """
    Decorator for creating a slash command with compatibility across versions.
    
    Args:
        name: Name of the command
        **attrs: Additional attributes for the command
        
    Returns:
        Slash command decorator
    """
    def decorator(func: T) -> T:
        if HAS_APP_COMMANDS:
            if not name and hasattr(func, '__name__'):
                cmd_name = func.__name__
            else:
                cmd_name = name or ""
                
            cmd = app_commands.command(name=cmd_name, **attrs)(func)
            return cast(T, cmd)
        return func
    return decorator

def slash_group(name: Optional[str] = None, **attrs) -> Callable[[T], T]:
    """
    Decorator for creating a slash command group with compatibility across versions.
    
    Args:
        name: Name of the group
        **attrs: Additional attributes for the group
        
    Returns:
        Slash group decorator
    """
    def decorator(func: T) -> T:
        if HAS_APP_COMMANDS:
            if not name and hasattr(func, '__name__'):
                group_name = func.__name__
            else:
                group_name = name or ""
                
            cmd = app_commands.Group(name=group_name, **attrs)(func)
            return cast(T, cmd)
        return func
    return decorator

def hybrid_command(name: Optional[str] = None, **attrs) -> Callable[[T], T]:
    """
    Decorator for creating a hybrid command with compatibility across versions.
    
    Args:
        name: Name of the command
        **attrs: Additional attributes for the command
        
    Returns:
        Hybrid command decorator
    """
    def decorator(func: T) -> T:
        if HAS_DISCORD and hasattr(commands, 'hybrid_command'):
            if not name and hasattr(func, '__name__'):
                cmd_name = func.__name__
            else:
                cmd_name = name or ""
                
            cmd = commands.hybrid_command(name=cmd_name, **attrs)(func)
            return cast(T, cmd)
        elif HAS_DISCORD:
            # Fallback to regular command if hybrid not available
            return command(name=name, **attrs)(func)
        return func
    return decorator

def hybrid_group(name: Optional[str] = None, **attrs) -> Callable[[T], T]:
    """
    Decorator for creating a hybrid command group with compatibility across versions.
    
    Args:
        name: Name of the group
        **attrs: Additional attributes for the group
        
    Returns:
        Hybrid group decorator
    """
    def decorator(func: T) -> T:
        if HAS_DISCORD and hasattr(commands, 'hybrid_group'):
            if not name and hasattr(func, '__name__'):
                group_name = func.__name__
            else:
                group_name = name or ""
                
            cmd = commands.hybrid_group(name=group_name, **attrs)(func)
            return cast(T, cmd)
        elif HAS_DISCORD:
            # Fallback to regular group if hybrid not available
            return group(name=name, **attrs)(func)
        return func
    return decorator

# Additional helper functions for compatibility
def get_command_name(command: Any) -> str:
    """
    Get the name of a command with compatibility across versions.
    
    Args:
        command: Command object
        
    Returns:
        Command name
    """
    if hasattr(command, 'name'):
        return command.name
    if hasattr(command, '__name__'):
        return command.__name__
    return str(command)

def get_command_signature(command: Any) -> str:
    """
    Get the signature of a command with compatibility across versions.
    
    Args:
        command: Command object
        
    Returns:
        Command signature
    """
    if hasattr(command, 'signature'):
        return command.signature
    if hasattr(command, '__name__'):
        try:
            return str(inspect.signature(command))
        except (ValueError, TypeError):
            pass
    return ""

def get_command_description(command: Any) -> str:
    """
    Get the description of a command with compatibility across versions.
    
    Args:
        command: Command object
        
    Returns:
        Command description
    """
    if hasattr(command, 'description') and command.description:
        return command.description
    if hasattr(command, 'help') and command.help:
        return command.help
    if hasattr(command, '__doc__') and command.__doc__:
        return inspect.cleandoc(command.__doc__)
    return ""

# Ensure all necessary attributes exist on mock modules
if not HAS_DISCORD:
    # Add essential classes to mock discord module
    class MockClient:
        def __init__(self, **kwargs):
            self.user = None
            self.guilds = []
            self.intents = None
            for key, value in kwargs.items():
                setattr(self, key, value)
                
        async def start(self, token, **kwargs):
            pass
            
        async def close(self):
            pass
            
    class MockIntents:
        @classmethod
        def default(cls):
            return cls()
            
        @classmethod
        def all(cls):
            return cls()
            
        @classmethod
        def none(cls):
            return cls()
            
    # Add mock classes to discord module
    discord.Client = MockClient
    discord.Intents = MockIntents
    
    # Add essential classes to mock commands module
    class MockBot(MockClient):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.commands = []
            self.cogs = {}
            
        def add_cog(self, cog):
            self.cogs[cog.__class__.__name__] = cog
            
        def command(self, **kwargs):
            def decorator(func):
                return func
            return decorator
            
        def group(self, **kwargs):
            def decorator(func):
                return func
            return decorator
            
    # Add mock classes to commands module
    commands.Bot = MockBot
    commands.command = lambda **kwargs: lambda f: f
    commands.group = lambda **kwargs: lambda f: f
    commands.Cog = type('Cog', (), {})

# Export for easy importing
__all__ = [
    'discord', 'commands', 'app_commands',
    'command', 'group', 'slash_command', 'slash_group',
    'hybrid_command', 'hybrid_group',
    'describe', 'guild_only', 'choices',
    'get_command_name', 'get_command_signature', 'get_command_description'
]