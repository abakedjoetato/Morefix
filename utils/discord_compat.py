"""
Discord API Compatibility Layer

This module provides compatibility between different versions of discord.py and py-cord.
It includes unified decorators, helper functions, and proper import proxies to ensure
code works across different library versions.
"""

import sys
import logging
import functools
import inspect
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union, cast, overload

try:
    import discord
    from discord.ext import commands
    
    # Check if we're using py-cord by looking for slash_command attribute
    USING_PYCORD = hasattr(commands.Bot, "slash_command")
    
    # Check if we're using py-cord 2.6.1+ with newer imports
    if USING_PYCORD:
        try:
            # Try importing app_commands directly (newer style)
            import discord.app_commands as app_commands
            USING_PYCORD_261_PLUS = True
        except ImportError:
            # Fall back to the old style if needed
            from discord import app_commands
            USING_PYCORD_261_PLUS = False
    else:
        # discord.py style - import from discord.ext
        from discord.ext import commands as app_commands  # type: ignore
        USING_PYCORD_261_PLUS = False
        
except ImportError as e:
    # Provide better error messages for missing dependencies
    logging.error(f"Failed to import Discord libraries: {e}")
    raise ImportError(
        "Failed to import Discord libraries. Please install discord.py or py-cord:\n"
        "For py-cord: pip install py-cord>=2.0.0\n"
        "For discord.py: pip install discord.py>=2.0.0"
    ) from e

# Type variables for return typing
T = TypeVar('T')
CommandT = TypeVar('CommandT')

# Logger for this module
logger = logging.getLogger(__name__)

# Version information for debugging
COMPAT_LAYER_VERSION = "1.0.0"

def get_library_info() -> Dict[str, Any]:
    """Get information about the current Discord library being used.
    
    Returns:
        Dict with library name, version, and compatibility details
    """
    library_info = {
        "using_pycord": USING_PYCORD,
        "using_pycord_261_plus": USING_PYCORD_261_PLUS,
        "compat_layer_version": COMPAT_LAYER_VERSION,
    }
    
    # Add version information if available
    try:
        library_info["discord_version"] = discord.__version__
    except (AttributeError, NameError):
        library_info["discord_version"] = "unknown"
        
    return library_info

# ========== Decorator Compatibility Wrappers ==========

def command(
    name: Optional[str] = None,
    description: Optional[str] = None,
    **kwargs
) -> Callable[[T], T]:
    """Unified command decorator that works across py-cord and discord.py.
    
    Args:
        name: Command name
        description: Command description
        **kwargs: Additional arguments to pass to the decorator
        
    Returns:
        Command decorator function
    """
    def decorator(func: T) -> T:
        """Wraps a command function with the appropriate decorator."""
        if USING_PYCORD:
            if hasattr(commands.Bot, "slash_command"):
                # py-cord style
                slash_decorator = commands.slash_command(
                    name=name,
                    description=description,
                    **kwargs
                )
                return slash_decorator(func)
        
        # discord.py style or fallback
        app_decorator = app_commands.command(
            name=name,
            description=description,
            **kwargs
        )
        return app_decorator(func)
    
    return decorator

def describe(**kwargs) -> Callable[[T], T]:
    """Unified describe decorator for command parameter descriptions.
    
    Args:
        **kwargs: Parameter name to description mapping
        
    Returns:
        Decorator function
    """
    def decorator(func: T) -> T:
        """Wraps a function with the describe decorator."""
        if USING_PYCORD:
            # py-cord style
            if hasattr(app_commands, "describe"):
                describe_decorator = app_commands.describe(**kwargs)
                return describe_decorator(func)
        
        # discord.py style
        describe_decorator = app_commands.describe(**kwargs)
        return describe_decorator(func)
    
    return decorator

def guild_only() -> Callable[[T], T]:
    """Unified guild_only decorator that works across versions.
    
    Returns:
        Decorator function
    """
    def decorator(func: T) -> T:
        """Wraps a function with the guild_only decorator."""
        if USING_PYCORD:
            # py-cord style
            if hasattr(app_commands, "guild_only"):
                guild_only_decorator = app_commands.guild_only()
                return guild_only_decorator(func)
        
        # discord.py style
        guild_only_decorator = app_commands.guild_only()
        return guild_only_decorator(func)
    
    return decorator

def choices(**kwargs) -> Callable[[T], T]:
    """Unified choices decorator for command parameter choices.
    
    Args:
        **kwargs: Parameter name to choices mapping
        
    Returns:
        Decorator function
    """
    def decorator(func: T) -> T:
        """Wraps a function with the choices decorator."""
        if USING_PYCORD:
            # py-cord style
            if hasattr(app_commands, "choices"):
                choices_decorator = app_commands.choices(**kwargs)
                return choices_decorator(func)
        
        # discord.py style
        choices_decorator = app_commands.choices(**kwargs)
        return choices_decorator(func)
    
    return decorator

# ========== Attribute Access Safety ==========

def safe_getattr(obj: Any, attr: str, default: Any = None) -> Any:
    """Safely get an attribute from an object with proper error handling.
    
    Args:
        obj: Object to get attribute from
        attr: Attribute name to get
        default: Default value if attribute doesn't exist
        
    Returns:
        Attribute value or default
    """
    try:
        return getattr(obj, attr, default)
    except Exception as e:
        logger.debug(f"Error getting attribute {attr} from {obj}: {e}")
        return default

# ========== Command Group Compatibility ==========

def group(
    name: Optional[str] = None,
    description: Optional[str] = None,
    **kwargs
) -> Callable[[T], T]:
    """Unified command group decorator that works across versions.
    
    Args:
        name: Group name
        description: Group description
        **kwargs: Additional arguments to pass to the decorator
        
    Returns:
        Command group decorator function
    """
    def decorator(func: T) -> T:
        """Wraps a function with the appropriate group decorator."""
        if USING_PYCORD:
            # py-cord style
            if hasattr(commands.Bot, "slash_command"):
                if USING_PYCORD_261_PLUS and hasattr(commands, "group"):
                    # py-cord 2.6.1+ style
                    group_decorator = commands.group(
                        name=name,
                        description=description,
                        **kwargs
                    )
                    return group_decorator(func)
                else:
                    # Older py-cord style
                    group_decorator = commands.slash_command(
                        name=name,
                        description=description,
                        **kwargs
                    )
                    return group_decorator(func)
                
        # discord.py style
        from discord.ext.commands import group as ext_group
        group_decorator = ext_group(
            name=name,
            description=description,
            **kwargs
        )
        return group_decorator(func)
    
    return decorator

# Add alias for backward compatibility
slash_command = command
slash_group = group