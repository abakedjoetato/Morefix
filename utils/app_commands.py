"""
app_commands compatibility module for py-cord 2.6.1

This module provides app_commands functionality that can be imported directly as:
    from utils.app_commands import command, describe, choices, etc.

This is a bridge to the app_commands_patch.py functionality.
"""

import logging
import sys
from utils.app_commands_patch import app_commands_bridge, Choice

logger = logging.getLogger(__name__)

# Export all the app_commands functionality
command = app_commands_bridge.command
describe = app_commands_bridge.describe
choices = app_commands_bridge.choices
autocomplete = app_commands_bridge.autocomplete

# Export the Choice class
Choice = Choice

# Make this module available for direct import via `from discord import app_commands`
# This is needed because the cogs are looking for app_commands objects
class AppCommandsModule:
    """Compatibility module for app_commands"""
    def __init__(self):
        self.command = command
        self.describe = describe
        self.choices = choices
        self.autocomplete = autocomplete
        self.Choice = Choice
        
# Create an app_commands object that can be imported
app_commands = AppCommandsModule()

# Try to register this module at the discord namespace level
try:
    import discord
    if not hasattr(discord, 'app_commands'):
        setattr(discord, 'app_commands', app_commands)
    if 'discord.app_commands' not in sys.modules:
        sys.modules['discord.app_commands'] = app_commands
except Exception as e:
    logger.error(f"Failed to register app_commands module: {e}")

logger.debug("app_commands compatibility module loaded")