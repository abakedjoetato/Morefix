"""
Command Tree Management

This module provides utilities for managing the command tree in a way that is
compatible with both py-cord 2.6.1 and discord.py.
"""

import logging
import traceback
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union, cast

import discord
from discord.ext import commands

from utils.command_imports import is_compatible_with_pycord_261

logger = logging.getLogger(__name__)

class CommandTree:
    """
    A compatibility wrapper for command tree management
    
    This provides a common interface for managing the command tree whether
    using py-cord 2.6.1 or discord.py.
    """
    
    def __init__(self, bot: commands.Bot):
        """
        Initialize the command tree wrapper
        
        Args:
            bot: The bot to manage the command tree for
        """
        self.bot = bot
        
        # Use app_commands in discord.py, direct methods in py-cord
        if not is_compatible_with_pycord_261():
            # For discord.py, we need to access app_commands
            from discord import app_commands
            self._tree = app_commands.CommandTree(bot) 
            # Replace the bot's tree with our custom tree
            bot.tree = self._tree
        else:
            # For py-cord, we can use the bot's command handling directly
            self._tree = None
            
    async def sync(self, guild_id: Optional[int] = None):
        """
        Sync the command tree to Discord
        
        Args:
            guild_id: Optional guild ID to sync to (None for global sync)
            
        Returns:
            List of synced commands
        """
        try:
            if not is_compatible_with_pycord_261():
                # For discord.py, use the tree sync method
                if guild_id:
                    guild = self.bot.get_guild(guild_id)
                    if guild:
                        return await self._tree.sync(guild=guild)
                    logger.warning(f"Could not find guild with ID {guild_id}")
                    return []
                else:
                    return await self._tree.sync()
            else:
                # For py-cord, use the bot's sync_commands method
                if guild_id:
                    return await self.bot.sync_commands(guild_ids=[guild_id])
                else:
                    return await self.bot.sync_commands(force=True)
        except Exception as e:
            logger.error(f"Error syncing command tree: {e}")
            logger.error(traceback.format_exc())
            return []
            
    async def add_command(self, command: Any, guild_id: Optional[int] = None):
        """
        Add a command to the tree
        
        Args:
            command: The command to add
            guild_id: Optional guild ID to add to (None for global)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not is_compatible_with_pycord_261():
                # For discord.py
                guild = None
                if guild_id:
                    guild = self.bot.get_guild(guild_id)
                self._tree.add_command(command, guild=guild)
                return True
            else:
                # For py-cord, commands are automatically added
                # We just need to sync them
                if guild_id:
                    await self.bot.sync_commands(guild_ids=[guild_id])
                else:
                    await self.bot.sync_commands()
                return True
        except Exception as e:
            logger.error(f"Error adding command to tree: {e}")
            logger.error(traceback.format_exc())
            return False

def create_command_tree(bot: commands.Bot) -> CommandTree:
    """
    Create a command tree wrapper for the bot
    
    Args:
        bot: The bot to create a command tree for
        
    Returns:
        A CommandTree instance
    """
    return CommandTree(bot)

async def sync_commands(bot: commands.Bot, command_tree: Optional[CommandTree] = None, guild_ids: Optional[List[int]] = None) -> List[Any]:
    """
    Sync the bot's commands with Discord
    
    This is a utility function that handles the sync process in a way that
    works for both py-cord 2.6.1 and discord.py.
    
    Args:
        bot: The bot to sync commands for
        command_tree: Optional command tree to use (will be created if None)
        guild_ids: Optional list of guild IDs to sync to (None for global)
        
    Returns:
        List of synced commands
    """
    try:
        logger.info(f"Syncing commands using py-cord 2.6.1 sync_commands")
        
        # Create a command tree if not provided
        tree = command_tree or create_command_tree(bot)
        
        # Sync commands
        synced_commands = []
        
        if guild_ids:
            # Sync to specific guilds
            for guild_id in guild_ids:
                logger.info(f"Syncing commands to guild {guild_id}")
                guild_commands = await tree.sync(guild_id=guild_id)
                if guild_commands:
                    synced_commands.extend(guild_commands)
        else:
            # Global sync
            logger.info("Syncing global commands")
            global_commands = await tree.sync()
            if global_commands:
                synced_commands.extend(global_commands)
                
        return synced_commands
    except Exception as e:
        logger.error(f"Error in sync_commands: {e}")
        logger.error(traceback.format_exc())
        return []