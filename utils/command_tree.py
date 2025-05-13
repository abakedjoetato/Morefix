"""
Command Tree Module for py-cord 2.6.1 Compatibility

This module provides a unified interface for command registration and synchronization,
handling the differences between py-cord 2.6.1 and other Discord library versions.
"""

import logging
import traceback
from typing import Any, Dict, List, Optional, Union, Callable, cast

import discord
from discord.ext import commands

from utils.command_imports import (
    is_compatible_with_pycord_261,
    PYCORD_261,
    HAS_APP_COMMANDS
)

logger = logging.getLogger(__name__)

class CompatibilityCommandTree:
    """
    Unified command tree interface for py-cord 2.6.1 compatibility
    
    This class provides a consistent interface for registering and syncing
    commands across different Discord library versions.
    """
    
    def __init__(self, bot: commands.Bot):
        """
        Initialize the compatibility command tree
        
        Args:
            bot: The bot instance
        """
        self.bot = bot
        self._commands = []
        
        # Store reference to native command tree based on library
        if is_compatible_with_pycord_261():
            # py-cord 2.6.1 has tree attribute
            self._native_tree = getattr(bot, "tree", None)
        elif HAS_APP_COMMANDS:
            # discord.py has app_commands.CommandTree
            self._native_tree = getattr(bot, "tree", None)
        else:
            # Fallback for older versions
            self._native_tree = None
            
        logger.info(f"Initialized command tree with py-cord 2.6.1 compatibility mode: {is_compatible_with_pycord_261()}")
    
    def add_command(
        self, 
        command: Callable,
        name: Optional[str] = None,
        description: Optional[str] = None,
        guild_ids: Optional[List[int]] = None,
        **kwargs
    ) -> Any:
        """
        Add a command to the command tree
        
        Args:
            command: The command function/coroutine
            name: Optional name for the command
            description: Optional description for the command
            guild_ids: Optional list of guild IDs to register with
            **kwargs: Additional parameters for the command
            
        Returns:
            The registered command
        """
        # Default command name is function name
        command_name = name or getattr(command, "__name__", "unknown_command")
        
        try:
            if is_compatible_with_pycord_261():
                # py-cord 2.6.1 approach
                if self._native_tree:
                    logger.debug(f"Registering command {command_name} with py-cord 2.6.1 tree")
                    
                    # Check if we need to register to specific guilds
                    if guild_ids:
                        # Register to each guild
                        for guild_id in guild_ids:
                            try:
                                guild = discord.Object(id=guild_id)
                                registered = self._native_tree.command(
                                    name=command_name,
                                    description=description or getattr(command, "__doc__", "No description"),
                                    guild=guild,
                                    **kwargs
                                )(command)
                                self._commands.append(registered)
                            except Exception as e:
                                logger.error(f"Error registering guild command {command_name} for guild {guild_id}: {e}")
                    else:
                        # Register globally
                        registered = self._native_tree.command(
                            name=command_name,
                            description=description or getattr(command, "__doc__", "No description"),
                            **kwargs
                        )(command)
                        self._commands.append(registered)
                    
                    return registered
                else:
                    logger.warning("No native command tree found for py-cord 2.6.1")
            elif HAS_APP_COMMANDS:
                # discord.py approach
                if self._native_tree:
                    logger.debug(f"Registering command {command_name} with discord.py tree")
                    
                    # Similar approach to py-cord but with discord.py specifics
                    if guild_ids:
                        for guild_id in guild_ids:
                            registered = self._native_tree.command(
                                name=command_name,
                                description=description or getattr(command, "__doc__", "No description"),
                                guild=discord.Object(id=guild_id),
                                **kwargs
                            )(command)
                            self._commands.append(registered)
                    else:
                        registered = self._native_tree.command(
                            name=command_name,
                            description=description or getattr(command, "__doc__", "No description"),
                            **kwargs
                        )(command)
                        self._commands.append(registered)
                    
                    return registered
                else:
                    logger.warning("No native command tree found for discord.py")
            else:
                # Fallback approach for older libraries
                logger.debug(f"Registering command {command_name} using fallback approach")
                
                # Use basic command decorator
                registered = commands.command(
                    name=command_name,
                    description=description or getattr(command, "__doc__", "No description"),
                    **kwargs
                )(command)
                
                # Add to bot's commands
                self.bot.add_command(registered)
                self._commands.append(registered)
                
                return registered
        except Exception as e:
            logger.error(f"Error registering command {command_name}: {e}")
            logger.error(traceback.format_exc())
            return command
    
    async def sync(self, guild: Optional[discord.Guild] = None) -> bool:
        """
        Sync commands to Discord
        
        Args:
            guild: Optional guild to sync to, if None syncs globally
            
        Returns:
            bool: True if sync was successful, False otherwise
        """
        try:
            if self._native_tree is None:
                logger.warning("No native command tree to sync")
                return False
                
            if is_compatible_with_pycord_261():
                # py-cord 2.6.1 approach
                logger.info(f"Syncing commands with py-cord 2.6.1 {'to guild' if guild else 'globally'}")
                
                # Use the native tree's sync method
                await self._native_tree.sync(guild=guild)
                return True
            elif HAS_APP_COMMANDS:
                # discord.py approach
                logger.info(f"Syncing commands with discord.py {'to guild' if guild else 'globally'}")
                
                if guild:
                    await self._native_tree.sync(guild=guild)
                else:
                    await self._native_tree.sync()
                return True
            else:
                # No sync needed for older command systems
                logger.info("No command sync required for this library version")
                return True
        except Exception as e:
            logger.error(f"Error syncing commands: {e}")
            logger.error(traceback.format_exc())
            return False


def create_command_tree(bot: commands.Bot) -> CompatibilityCommandTree:
    """
    Create a command tree instance for the bot
    
    Args:
        bot: The bot instance
        
    Returns:
        CompatibilityCommandTree: The command tree instance
    """
    return CompatibilityCommandTree(bot)


async def sync_command_tree(
    bot: commands.Bot,
    command_tree: CompatibilityCommandTree,
    guild_ids: Optional[List[int]] = None,
    sync_global: bool = True
) -> bool:
    """
    Sync commands to Discord using the compatibility command tree
    
    Args:
        bot: The bot instance
        command_tree: The command tree instance
        guild_ids: Optional list of guild IDs to sync to
        sync_global: Whether to sync global commands
        
    Returns:
        bool: True if sync was successful, False otherwise
    """
    try:
        # Track success for each sync operation
        sync_results = []
        
        # Sync to specific guilds if provided
        if guild_ids:
            for guild_id in guild_ids:
                try:
                    # Get the guild object
                    guild = bot.get_guild(guild_id)
                    
                    if guild is not None:
                        # Sync commands to this guild
                        result = await command_tree.sync(guild=guild)
                        sync_results.append(result)
                        
                        # Get guild name safely
                        guild_name = getattr(guild, "name", str(guild_id))
                        logger.info(f"Synced commands to guild {guild_name} ({guild_id})")
                    else:
                        logger.warning(f"Could not find guild with ID {guild_id}")
                        sync_results.append(False)
                except Exception as e:
                    logger.error(f"Error syncing commands to guild {guild_id}: {e}")
                    logger.error(traceback.format_exc())
                    sync_results.append(False)
        
        # Sync globally if requested
        if sync_global:
            try:
                result = await command_tree.sync()
                sync_results.append(result)
                logger.info("Application commands synced globally")
            except Exception as e:
                logger.error(f"Error syncing commands globally: {e}")
                logger.error(traceback.format_exc())
                sync_results.append(False)
                
        # Overall success if at least one sync operation succeeded
        return any(sync_results) if sync_results else False
    except Exception as e:
        logger.error(f"Error in sync_command_tree: {e}")
        logger.error(traceback.format_exc())
        return False