"""
app_commands compatibility module for py-cord 2.6.1

This module provides compatibility between discord.py's app_commands and py-cord's command system.
Import this instead of 'discord.app_commands' to ensure compatibility.
"""

import discord
import logging
from typing import Any, Callable, List, Optional, TypeVar, Union, get_type_hints

logger = logging.getLogger(__name__)

# Detect library version and availability of app_commands
HAS_APP_COMMANDS = False
try:
    from discord import app_commands
    HAS_APP_COMMANDS = True
    logger.info("Using native discord.py app_commands")
except ImportError:
    logger.info("discord.app_commands not available, using compatibility layer")
    HAS_APP_COMMANDS = False

# Type var for return type preservation
T = TypeVar('T')

# Command decorator that works with both libraries
def command(*, name: Optional[str] = None, description: Optional[str] = None, **kwargs):
    """
    Command decorator compatible with both discord.py and py-cord
    """
    if HAS_APP_COMMANDS:
        # Use native app_commands if available
        return app_commands.command(name=name, description=description, **kwargs)
    else:
        # Use py-cord's slash_command
        return discord.ext.commands.slash_command(name=name, description=description, **kwargs)

# Choice class that works with both libraries
class Choice:
    """
    Choice class compatible with both discord.py and py-cord
    """
    def __init__(self, name: str, value: Union[str, int, float]):
        self.name = name
        self.value = value
        
    def to_dict(self):
        return {'name': self.name, 'value': self.value}

# Group command
class Group:
    """
    Command group compatible with both discord.py and py-cord
    """
    def __init__(self, *, name: Optional[str] = None, description: Optional[str] = None, **kwargs):
        self.name = name
        self.description = description
        self.kwargs = kwargs
    
    def command(self, *, name: Optional[str] = None, description: Optional[str] = None, **kwargs):
        """
        Create a command within this group
        """
        if HAS_APP_COMMANDS:
            # Use native app_commands if available
            return app_commands.command(name=name, description=description, **kwargs)
        else:
            # Use py-cord's slash_command
            return discord.ext.commands.slash_command(name=name, description=description, **kwargs)

# Export all required components
__all__ = ['command', 'Choice', 'Group', 'HAS_APP_COMMANDS']