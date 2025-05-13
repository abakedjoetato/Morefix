"""
Command Imports Compatibility Detection

This module provides utilities for detecting the Discord library version
and adjusting import behavior accordingly.
"""

import importlib
import sys
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Discord library version detection
_DISCORD_VERSION: Optional[str] = None
_IS_COMPATIBLE_WITH_PYCORD_261: Optional[bool] = None

def get_discord_version() -> str:
    """
    Get the installed Discord library version
    
    Returns:
        The version string of the installed Discord library
    """
    global _DISCORD_VERSION
    
    if _DISCORD_VERSION is None:
        try:
            discord_module = importlib.import_module("discord")
            _DISCORD_VERSION = getattr(discord_module, "__version__", "unknown")
        except (ImportError, AttributeError) as e:
            logger.warning(f"Failed to get Discord library version: {e}")
            _DISCORD_VERSION = "unknown"
    
    return _DISCORD_VERSION

def is_compatible_with_pycord_261() -> bool:
    """
    Check if the installed Discord library is compatible with py-cord 2.6.1
    
    Returns:
        True if the library is compatible with py-cord 2.6.1, False otherwise
    """
    global _IS_COMPATIBLE_WITH_PYCORD_261
    
    if _IS_COMPATIBLE_WITH_PYCORD_261 is None:
        version = get_discord_version()
        
        # Check for py-cord 2.6.1 specifically
        is_pycord_261 = version == "2.6.1"
        
        # Check for module structure specific to py-cord
        has_slash_command = False
        try:
            from discord.ext.commands import slash_command
            has_slash_command = True
        except ImportError:
            pass
        
        # Set the compatibility flag based on version and structure
        _IS_COMPATIBLE_WITH_PYCORD_261 = is_pycord_261 or has_slash_command
        
        # Log the detected version and compatibility
        logger.info(f"Detected Discord library version: {version}")
        logger.info(f"Compatible with py-cord 2.6.1: {_IS_COMPATIBLE_WITH_PYCORD_261}")
    
    return _IS_COMPATIBLE_WITH_PYCORD_261

def import_app_commands() -> Any:
    """
    Import the appropriate app_commands module based on the installed Discord library
    
    This function handles the differences between discord.py and py-cord,
    allowing code to use app_commands consistently.
    
    Returns:
        The appropriate app_commands module
    """
    if is_compatible_with_pycord_261():
        # For py-cord 2.6.1, we need to use our patches
        try:
            from utils import app_commands_patch
            return app_commands_patch
        except ImportError:
            logger.warning("Failed to import app_commands_patch, falling back to discord.py style")
    
    # For discord.py or fallback, use the standard app_commands
    try:
        from discord import app_commands
        return app_commands
    except ImportError:
        logger.error("Failed to import discord.app_commands. This may cause issues.")
        # Return a placeholder module as a last resort
        class PlaceholderAppCommands:
            pass
        return PlaceholderAppCommands()