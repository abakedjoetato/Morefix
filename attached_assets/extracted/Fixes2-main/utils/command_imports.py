"""
Command Imports for py-cord 2.6.1 Compatibility

This module provides compatibility layers for importing command-related classes and functions
across different versions of py-cord and discord.py.
"""

import logging
import sys
import importlib
from typing import Any, Dict, List, Optional, Union, Type, Tuple, cast

logger = logging.getLogger(__name__)

# Constants for library detection
IS_PYCORD = False
PYCORD_VERSION = None
PYCORD_261 = False
HAS_APP_COMMANDS = False

# Command-related classes that will be imported dynamically
SlashCommand = None
Option = None

def _setup_imports():
    """
    Setup imports and constants for library detection.
    This function is called at module load time to initialize the constants.
    """
    global IS_PYCORD, PYCORD_VERSION, PYCORD_261, HAS_APP_COMMANDS
    global SlashCommand, Option
    
    try:
        import discord
        
        # Get the version and determine if it's py-cord
        version = getattr(discord, "__version__", "0.0.0")
        logger.info(f"Detected discord library version: {version}")
        
        # Check if it's py-cord by looking for specific attributes/modules
        try:
            # py-cord has a 'discord.ui' module with Modal class
            from discord.ui import Modal
            IS_PYCORD = True
            PYCORD_VERSION = version
            logger.info(f"Detected py-cord version: {PYCORD_VERSION}")
        except ImportError:
            IS_PYCORD = False
            logger.info("Not using py-cord")
        
        # Check for py-cord 2.6.1 which misreports itself as 2.5.2
        if IS_PYCORD and version == "2.5.2":
            # Additional check for py-cord 2.6.1
            try:
                # In py-cord 2.6.1, Modal has specific attributes
                from discord.ui import Modal
                if hasattr(Modal, "__discord_ui_view__"):
                    PYCORD_261 = True
                    logger.info("Detected py-cord 2.6.1 compatibility mode")
            except (ImportError, AttributeError):
                PYCORD_261 = False
        
        # Check for app_commands module (discord.py style)
        try:
            import discord.app_commands
            HAS_APP_COMMANDS = True
            logger.info("Detected app_commands module")
        except ImportError:
            HAS_APP_COMMANDS = False
            logger.info("No app_commands module found")
        
        # Import appropriate command classes based on detected library
        if IS_PYCORD:
            if PYCORD_261:
                # py-cord 2.6.1
                from discord.commands import SlashCommand as PyCordSlashCommand
                from discord.commands import Option as PyCordOption
                
                SlashCommand = PyCordSlashCommand
                Option = PyCordOption
                logger.info("Imported SlashCommand and Option from py-cord 2.6.1")
            else:
                # Regular py-cord
                from discord.ext.commands import SlashCommand as PyCordSlashCommand
                from discord.commands import Option as PyCordOption
                
                SlashCommand = PyCordSlashCommand
                Option = PyCordOption
                logger.info("Imported SlashCommand and Option from regular py-cord")
        elif HAS_APP_COMMANDS:
            # discord.py style
            from discord.ext.commands import Command as DiscordPyCommand
            
            # discord.py doesn't have SlashCommand, so use Command as a placeholder
            SlashCommand = DiscordPyCommand
            
            # discord.py uses app_commands.Command, create a placeholder Option
            class DiscordPyOption:
                pass
                
            Option = DiscordPyOption
            logger.info("Using compatibility classes for discord.py")
        else:
            # Fallback for older versions
            from discord.ext.commands import Command
            
            # Use base Command class as placeholders
            SlashCommand = Command
            Option = object
            logger.info("Using fallback Command class for older discord.py")
            
    except ImportError as e:
        logger.error(f"Error during import setup: {e}")
        
        # Set fallback values
        IS_PYCORD = False
        PYCORD_VERSION = None
        PYCORD_261 = False
        HAS_APP_COMMANDS = False
        SlashCommand = None
        Option = None

def is_compatible_with_pycord_261() -> bool:
    """
    Check if we're running with py-cord 2.6.1 compatibility
    
    Returns:
        bool: True if we're using py-cord 2.6.1, False otherwise
    """
    return PYCORD_261

def has_app_commands() -> bool:
    """
    Check if we're running with discord.py app_commands
    
    Returns:
        bool: True if we have app_commands, False otherwise
    """
    return HAS_APP_COMMANDS

def is_pycord() -> bool:
    """
    Check if we're running with py-cord
    
    Returns:
        bool: True if we're using py-cord, False otherwise
    """
    return IS_PYCORD

def get_slash_command_class() -> Optional[Type]:
    """
    Get the appropriate SlashCommand class for the current library
    
    Returns:
        Type or None: The SlashCommand class or None if not available
    """
    return SlashCommand

def get_option_class() -> Optional[Type]:
    """
    Get the appropriate Option class for the current library
    
    Returns:
        Type or None: The Option class or None if not available
    """
    return Option

# Initialize the module when imported
_setup_imports()