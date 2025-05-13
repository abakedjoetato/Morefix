"""
Discord API Compatibility Layer

This module provides compatibility functions and import objects
to support both discord.py and py-cord 2.6.1 APIs.
"""

import sys
import logging
import discord
from typing import Any, Dict, List, Optional, Tuple, Type, Union, cast

logger = logging.getLogger(__name__)

# Detect library version
PY_CORD = False
try:
    import discord
    version = getattr(discord, "__version__", "0.0.0")
    logger.info(f"Detected discord library version: {version}")
    
    # Check for py-cord by looking for slash_command
    if hasattr(discord.ext.commands, 'slash_command'):
        PY_CORD = True
        logger.info(f"Using py-cord version: {version}")
    else:
        logger.info("Using discord.py")
except ImportError as e:
    logger.error(f"Error importing discord: {e}")
    PY_CORD = False

# Provide app_commands compatibility
if PY_CORD:
    # For py-cord, we'll create an app_commands module that mimics discord.py's structure
    class AppCommandsModule:
        """Compatibility module for app_commands"""
        
        @staticmethod
        def command(*args, **kwargs):
            """Wrapper for slash_command"""
            # Use the underlying slash_command from py-cord
            return discord.ext.commands.slash_command(*args, **kwargs)
        
        # Add other needed app_commands functionality
        class Group:
            def __init__(self, *args, **kwargs):
                pass
        
        class Choice:
            def __init__(self, name, value):
                self.name = name
                self.value = value
    
    # Create the module
    app_commands = AppCommandsModule()
else:
    # For discord.py, just import the real app_commands
    try:
        from discord import app_commands
    except ImportError:
        logger.error("Failed to import app_commands from discord")
        
        # Create a fallback
        class FallbackAppCommands:
            @staticmethod
            def command(*args, **kwargs):
                return lambda x: x
                
            class Group:
                def __init__(self, *args, **kwargs):
                    pass
            
            class Choice:
                def __init__(self, name, value):
                    self.name = name
                    self.value = value
        
        app_commands = FallbackAppCommands()

# Add a slash_command decorator function that works with both libraries
def slash_command(*args, **kwargs):
    """
    Universal slash command decorator that works with both discord.py and py-cord
    
    Args:
        *args: Positional arguments to pass to the underlying decorator
        **kwargs: Keyword arguments to pass to the underlying decorator
        
    Returns:
        The appropriate slash command decorator
    """
    if PY_CORD:
        return discord.ext.commands.slash_command(*args, **kwargs)
    else:
        return app_commands.command(*args, **kwargs)

# Utility function to check which library we're using
def is_using_pycord():
    """
    Check if we're using py-cord
    
    Returns:
        bool: True if using py-cord, False if using discord.py
    """
    return PY_CORD