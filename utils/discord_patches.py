"""
Discord patches for py-cord 2.6.1

This module provides patches and monkey patches to make py-cord 2.6.1 compatible with
code expecting discord.py behavior.
"""

import sys
import logging
import importlib
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Pre-define the app_commands at module level so it can be imported
from utils.app_commands_patch import app_commands_bridge, Choice

# Create a module-like object for app_commands that can be imported directly from this module
class AppCommandsModule:
    def __init__(self):
        self.command = app_commands_bridge.command
        self.describe = app_commands_bridge.describe
        self.choices = app_commands_bridge.choices
        self.autocomplete = app_commands_bridge.autocomplete
        self.Choice = Choice
        
    def __repr__(self):
        return "<py-cord compatibility layer for app_commands>"

# Make app_commands available at module level for direct imports
app_commands = AppCommandsModule()

def patch_modules() -> bool:
    """
    Apply all necessary patches to make py-cord 2.6.1 behave more like discord.py
    
    Returns:
        bool: True if patches were applied, False otherwise
    """
    from utils.command_imports import is_compatible_with_pycord_261
    
    if not is_compatible_with_pycord_261():
        logger.info("Not using py-cord 2.6.1, no need to apply patches")
        return False
    
    # Apply patches for app_commands
    patch_app_commands()
    
    # Apply patches for interaction handling
    patch_interaction_handlers()
    
    # Apply patches for hybrid commands
    patch_hybrid_commands()
    
    # Apply patches for command groups
    patch_command_groups()
    
    # Apply patches for choices in commands
    patch_choices()
    
    return True
    
def patch_app_commands():
    """
    Create a synthetic app_commands module in discord namespace
    """
    import discord
    
    # We already created the app_commands object at module level
    # Just add it to the sys.modules and discord namespaces
    
    # Add the synthetic module to discord
    sys.modules['discord.app_commands'] = app_commands
    
    # Add it to the discord namespace for direct imports
    if not hasattr(discord, 'app_commands'):
        setattr(discord, 'app_commands', app_commands)
    
    logger.info("Patched app_commands into discord namespace")
    
def patch_interaction_handlers():
    """
    Patch interaction handling to be more compatible across versions
    """
    try:
        from utils.interaction_handlers import patch_interaction_respond
        patch_interaction_respond()
        logger.info("Patched interaction response handlers")
    except Exception as e:
        logger.error(f"Failed to patch interaction handlers: {e}")
    
def patch_hybrid_commands():
    """
    Patch hybrid commands to be compatible across versions
    """
    try:
        import discord
        from discord.ext import commands
        
        # Add hybrid_command and hybrid_group to commands if not present
        if not hasattr(commands, 'hybrid_command'):
            setattr(commands, 'hybrid_command', commands.slash_command)
            logger.info("Added hybrid_command compatibility")
            
        if not hasattr(commands, 'hybrid_group'):
            setattr(commands, 'hybrid_group', commands.slash_command)
            logger.info("Added hybrid_group compatibility")
    except Exception as e:
        logger.error(f"Failed to patch hybrid commands: {e}")
        
def patch_command_groups():
    """
    Patch command groups to be compatible across versions
    """
    try:
        import discord
        from discord.ext import commands
        
        # Enhance Group class if needed
        if hasattr(commands, 'Group'):
            original_init = commands.Group.__init__
            
            def enhanced_init(self, *args, **kwargs):
                original_init(self, *args, **kwargs)
                # Add any missing attributes
                if not hasattr(self, 'command'):
                    self.command = self.sub_command
                    
            commands.Group.__init__ = enhanced_init
            logger.info("Enhanced Group class with compatibility attributes")
    except Exception as e:
        logger.error(f"Failed to patch command groups: {e}")
        
def patch_choices():
    """
    Patch choice handling to be compatible across versions
    """
    try:
        from utils.app_commands_patch import Choice
        
        # Replace in relevant modules
        import discord
        if hasattr(discord, 'app_commands') and not hasattr(discord.app_commands, 'Choice'):
            setattr(discord.app_commands, 'Choice', Choice)
            
        logger.info("Patched Choice class across modules")
    except Exception as e:
        logger.error(f"Failed to patch choices: {e}")
        
def create_compatibility_modules():
    """
    Create additional compatibility modules if needed
    """
    # This is a placeholder for adding more compatibility modules as needed
    pass