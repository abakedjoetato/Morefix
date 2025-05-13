"""
Discord.py Compatibility Patches for py-cord 2.6.1

This module provides compatibility fixes between discord.py and py-cord 2.6.1.
It monkey-patches critical components to ensure consistent behavior across versions.
"""

import sys
import logging
import inspect
from types import ModuleType
from typing import Any, Dict, List, Optional, Union, Callable, TypeVar, Type, cast

logger = logging.getLogger(__name__)

# Import discord namespace first
import discord
from discord.ext import commands

# Check if we're using py-cord 2.6.1 or a compatible version
is_pycord_261 = False
try:
    discord_version = getattr(discord, "__version__", "0.0.0")
    version_parts = [int(x) for x in discord_version.split('.')[:3]]
    
    # py-cord 2.6.1+
    if len(version_parts) >= 3 and tuple(version_parts) >= (2, 6, 1):
        is_pycord_261 = True
        logger.info(f"Detected py-cord 2.6.1+ ({discord_version}), applying compatibility patches")
except (AttributeError, ValueError):
    pass

# Define a module to hold app_commands compatibility
class AppCommandsModule(ModuleType):
    """Module for app_commands compatibility layer"""
    
    def __init__(self):
        super().__init__("app_commands")
        self.command = None
        self.describe = None
        self.choices = None
        self.autocomplete = None
        self.Choice = None
        self.Group = None
        self.ContextMenu = None
        
app_commands = AppCommandsModule()

def patch_app_commands():
    """Patch app_commands to provide compatibility"""
    global app_commands
    
    # Try to get real app_commands from discord.py
    real_app_commands = None
    if hasattr(discord, "app_commands"):
        real_app_commands = discord.app_commands
    
    # If not found, try to create our own compatible version
    if real_app_commands is None:
        # Recreate command decorator from py-cord
        def command_decorator(**kwargs):
            def decorator(func):
                if hasattr(commands, "slash_command"):
                    # Use py-cord's slash_command if available
                    return commands.slash_command(**kwargs)(func)
                else:
                    # Fallback to regular command
                    return commands.command(**kwargs)(func)
            return decorator
            
        # Recreate describe decorator from py-cord
        def describe_decorator(**kwargs):
            def decorator(func):
                # In py-cord 2.4.1+, we might have an option decorator
                if hasattr(commands, "option"):
                    # Apply individual options
                    result = func
                    for param_name, desc in kwargs.items():
                        result = commands.option(name=param_name, description=desc)(result)
                    return result
                return func
            return decorator
            
        # Recreate choices decorator from py-cord
        def choices_decorator(**kwargs):
            def decorator(func):
                return func
            return decorator
            
        # Recreate autocomplete decorator
        def autocomplete_decorator(**kwargs):
            def decorator(func):
                return func
            return decorator
            
        # Basic Choice class for compatibility
        class Choice:
            def __init__(self, name, value):
                self.name = name
                self.value = value
                
        # Apply patches
        app_commands.command = command_decorator
        app_commands.describe = describe_decorator
        app_commands.choices = choices_decorator
        app_commands.autocomplete = autocomplete_decorator
        app_commands.Choice = Choice
        
    else:
        # Use the real app_commands
        app_commands.command = real_app_commands.command
        app_commands.describe = real_app_commands.describe
        
        # Apply other attributes if available
        for attr in ["choices", "autocomplete", "Choice", "Group", "ContextMenu"]:
            if hasattr(real_app_commands, attr):
                setattr(app_commands, attr, getattr(real_app_commands, attr))
                
    # Ensure we have the command method
    if app_commands.command is None:
        logger.warning("app_commands.command is still None after patching, falling back to basic implementation")
        
        def basic_command(**kwargs):
            def decorator(func):
                return func
            return decorator
            
        app_commands.command = basic_command
                
    return app_commands

def patch_all():
    """Apply all necessary patches for Discord.py compatibility"""
    logger.info("Applying Discord.py compatibility patches...")
    
    # Patch app_commands
    patch_app_commands()
    
    # Inject app_commands into discord module if needed
    if not hasattr(discord, "app_commands") and app_commands is not None:
        discord.app_commands = app_commands
        sys.modules["discord.app_commands"] = app_commands
        logger.info("Injected app_commands module into discord namespace")
        
    # If we're using py-cord 2.6.1, apply specific fixes
    if is_pycord_261:
        try:
            from discord.interactions import Interaction
            
            # Fix missing attributes or methods if needed
            if not hasattr(Interaction, "followup") or getattr(Interaction, "followup", None) is None:
                logger.warning("Patching missing Interaction.followup attribute")
                
                # Add basic followup class
                class FollowupProxy:
                    def __init__(self, interaction):
                        self.interaction = interaction
                        
                    async def send(self, content=None, **kwargs):
                        # Try to implement followup via webhook
                        try:
                            if hasattr(self.interaction, "webhook"):
                                return await self.interaction.webhook.send(content, **kwargs)
                            else:
                                # Last resort, try to create a response
                                return await self.interaction.response.send_message(content, **kwargs)
                        except Exception as e:
                            logger.error(f"Error in patched followup.send: {e}")
                
                # Monkey patch the Interaction class
                original_init = Interaction.__init__
                
                def patched_init(self, *args, **kwargs):
                    original_init(self, *args, **kwargs)
                    self.followup = FollowupProxy(self)
                    
                Interaction.__init__ = patched_init
        except (ImportError, AttributeError) as e:
            logger.error(f"Error applying py-cord 2.6.1 patches: {e}")
        
    logger.info("Discord.py compatibility patches applied successfully")
    
    return True