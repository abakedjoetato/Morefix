"""
Discord Compatibility Layer for py-cord 2.6.1

This module centralizes all the compatibility layers used to ensure
the bot works with py-cord 2.6.1 while maintaining compatibility
with both discord.py codebase and older py-cord versions.
"""

import logging
import sys
from typing import Dict, Any, Optional, Tuple, List, Union, Callable

logger = logging.getLogger(__name__)

# Import discord namespace first
import discord

# Detect py-cord version
PYCORD_VERSION = "unknown"
try:
    PYCORD_VERSION = getattr(discord, "__version__", "0.0.0")
    _version_parts = [int(x) for x in PYCORD_VERSION.split('.')[:3]]
    
    # Check if py-cord 2.6.1+
    IS_PYCORD_261 = len(_version_parts) >= 3 and tuple(_version_parts) >= (2, 6, 1)
    
    logger.info(f"Detected Discord library version: {PYCORD_VERSION}")
    if IS_PYCORD_261:
        logger.info("Using py-cord 2.6.1+ compatibility patches")
except (AttributeError, ValueError, TypeError):
    IS_PYCORD_261 = False
    logger.warning("Could not detect Discord library version, assuming older version")

# Import our patch modules
from utils.discord_patches import patch_all as patch_discord_modules

def is_pycord_261_or_later():
    """Check if the current discord library is py-cord 2.6.1 or later
    
    Returns:
        bool: True if py-cord 2.6.1+, False otherwise
    """
    return IS_PYCORD_261

def patch_all() -> bool:
    """Apply all compatibility patches
    
    Returns:
        bool: True if all patches were applied successfully
    """
    success = True
    
    # Apply discord module patches first
    try:
        patch_result = patch_discord_modules()
        if not patch_result:
            logger.warning("Discord module patches did not complete successfully")
            success = False
    except Exception as e:
        logger.error(f"Error applying Discord module patches: {e}")
        success = False
    
    # Ensure all imports are patched for module importing by other modules
    if success:
        # These are the modules that might be imported by other modules
        # For each one, ensure it appears in the right namespace
        try:
            # Re-export app_commands from our patches
            if hasattr(discord, "app_commands"):
                sys.modules['discord.app_commands'] = discord.app_commands
                
            # Ensure ext.commands namespace is available
            if hasattr(discord, "ext") and hasattr(discord.ext, "commands"):
                sys.modules['discord.ext.commands'] = discord.ext.commands
        except Exception as e:
            logger.error(f"Error setting up module imports: {e}")
            success = False
    
    return success

# Imported functions for command handling
def get_command_name(command: Any) -> str:
    """Get the name of a command across different Discord library versions
    
    Args:
        command: Command object from any Discord library
        
    Returns:
        str: Name of the command
    """
    if is_pycord_261_or_later():
        # For py-cord 2.6.1+
        if hasattr(command, "name"):
            return command.name
        elif hasattr(command, "qualified_name"):
            return command.qualified_name
    
    # Fallback for all versions
    try:
        return str(command)
    except:
        return "unknown_command"

# Improved error handling
def format_command_signature(command: Any) -> str:
    """Format a command's signature for error messages
    
    Args:
        command: Command object
        
    Returns:
        str: Formatted command signature
    """
    if hasattr(command, "qualified_name"):
        name = command.qualified_name
    else:
        name = get_command_name(command)
        
    if hasattr(command, "signature"):
        signature = command.signature
    else:
        signature = ""
        
    if signature:
        return f"{name} {signature}"
    else:
        return name

# Functions to handle guild_only properly across versions
def is_guild_only(command: Any) -> bool:
    """Check if a command is guild-only across versions
    
    Args:
        command: Command object
        
    Returns:
        bool: True if guild-only, False otherwise
    """
    if not command:
        return False
        
    # Check attributes in order of likelihood
    if hasattr(command, "guild_only"):
        return bool(command.guild_only)
    
    if hasattr(command, "checks"):
        for check in getattr(command, "checks", []):
            # Try to find guild_only check function
            check_name = getattr(check, "__name__", "")
            if "guild_only" in check_name:
                return True
                
    return False