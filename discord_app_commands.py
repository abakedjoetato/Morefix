"""
Compatibility module for discord.app_commands

This file provides direct import compatibility for:
    from discord import app_commands
"""

# Import directly from our enhanced app_commands module
from utils.app_commands_patch import app_commands_bridge, Choice

# Make the attributes available directly in this module
command = app_commands_bridge.command
describe = app_commands_bridge.describe
choices = app_commands_bridge.choices
autocomplete = app_commands_bridge.autocomplete

# Export these names for "from discord.app_commands import X" style imports
__all__ = [
    'command', 'describe', 'choices', 'autocomplete', 'Choice'
]