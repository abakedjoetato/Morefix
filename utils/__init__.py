"""
Utils package for Discord bot
"""

# Re-export app_commands at package level for easier imports
from utils.app_commands import (
    command, describe, choices, autocomplete, Choice
)

# For backward compatibility, provide app_commands object
from utils.discord_patches import app_commands