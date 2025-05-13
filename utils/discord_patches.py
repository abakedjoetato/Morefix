"""
Discord Patches for py-cord 2.6.1

This module provides patches and compatibility shims for using py-cord 2.6.1
with code that expects discord.py's module structure.
"""

import logging
import sys
from typing import Any, Dict, List, Optional, Union, Callable

from utils.command_imports import import_app_commands

logger = logging.getLogger(__name__)

# Import the appropriate app_commands module based on the current library
app_commands = import_app_commands()

# Add the app_commands module to discord for import compatibility
try:
    import discord
    if not hasattr(discord, 'app_commands'):
        setattr(discord, 'app_commands', app_commands)
        logger.info("Successfully patched discord.app_commands")
except ImportError as e:
    logger.error(f"Failed to patch discord.app_commands: {e}")

class Interaction:
    """
    Placeholder for direct imports of discord.Interaction
    
    This helps with type annotations and imports that expect
    discord.Interaction directly.
    """
    pass

def patch_modules():
    """
    Apply patches to make py-cord 2.6.1 more compatible with discord.py code
    
    This function:
    1. Patches sys.modules to make 'discord.app_commands' importable
    2. Sets up any other necessary patches for compatibility
    
    Returns:
        bool: True if patches were applied, False otherwise
    """
    try:
        # Add app_commands to sys.modules for direct imports
        if 'discord.app_commands' not in sys.modules:
            sys.modules['discord.app_commands'] = app_commands
            logger.info("Added discord.app_commands to sys.modules")
        
        # Patch discord.Interaction if needed
        if hasattr(discord, 'Interaction'):
            # Use the actual Interaction class
            globals()['Interaction'] = discord.Interaction
            logger.info("Using discord.Interaction directly")
        
        return True
    except Exception as e:
        logger.error(f"Failed to apply Discord patches: {e}")
        return False

# Apply patches when the module is imported
patch_success = patch_modules()
logger.info(f"Discord patches applied: {patch_success}")