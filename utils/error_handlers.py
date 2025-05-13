"""
Error handling utilities for Discord command errors.

This module provides a comprehensive error handling system for both
application commands and traditional commands across different Discord library versions.
"""

import logging
import traceback
from typing import Any, Dict, Optional, Union, Tuple, List, Callable

import discord
from discord.ext import commands

from utils.discord_compat import get_command_name, format_command_signature, is_guild_only

logger = logging.getLogger(__name__)

# Error types categorization
PERMISSION_ERRORS = (
    commands.MissingPermissions,
    commands.BotMissingPermissions,
    commands.MissingRole,
    commands.BotMissingRole,
    commands.MissingAnyRole,
    commands.BotMissingAnyRole
)

COOLDOWN_ERRORS = (
    commands.CommandOnCooldown,
)

USER_INPUT_ERRORS = (
    commands.MissingRequiredArgument,
    commands.BadArgument,
    commands.BadUnionArgument,
    commands.BadLiteralArgument,
    commands.ArgumentParsingError,
    commands.UserInputError
)

CHECK_FAILURE_ERRORS = (
    commands.CheckFailure,
    commands.CheckAnyFailure,
    commands.PrivateMessageOnly,
    commands.NoPrivateMessage,
    commands.NotOwner
)

DISCORD_ERRORS = (
    discord.Forbidden,
    discord.NotFound,
    discord.HTTPException
)

# Try to import app command specific errors if available
try:
    from discord import app_commands
    APP_COMMAND_ERRORS = (
        app_commands.CommandInvokeError,
        app_commands.CommandNotFound,
        app_commands.TransformerError
    )
except (ImportError, AttributeError):
    APP_COMMAND_ERRORS = tuple()

def get_error_data(error: Exception) -> Dict[str, Any]:
    """Extract useful data from an error for error handling
    
    Args:
        error: The exception that was raised
        
    Returns:
        Dict with error information
    """
    if error is None:
        return {}
        
    data = {
        "type": type(error).__name__,
        "message": str(error)
    }
    
    # Extract additional data based on error type
    
    # Permission errors
    if isinstance(error, commands.MissingPermissions):
        data["missing_perms"] = getattr(error, "missing_permissions", [])
    
    # Cooldown errors
    elif isinstance(error, commands.CommandOnCooldown):
        data["retry_after"] = getattr(error, "retry_after", 0)
        data["cooldown_type"] = getattr(error, "type", None)
        
    # Add traceback for unexpected errors
    elif not isinstance(error, (
        PERMISSION_ERRORS + COOLDOWN_ERRORS + USER_INPUT_ERRORS + 
        CHECK_FAILURE_ERRORS + DISCORD_ERRORS + APP_COMMAND_ERRORS
    )):
        data["traceback"] = traceback.format_exception(type(error), error, error.__traceback__)
    
    return data

async def handle_command_error(
    ctx_or_interaction: Union[commands.Context, discord.Interaction],
    error: Exception,
    ephemeral: bool = True
) -> bool:
    """Handle command errors for both traditional and application commands
    
    Args:
        ctx_or_interaction: Command context or interaction
        error: The error that occurred
        ephemeral: Whether the error response should be ephemeral (application commands only)
        
    Returns:
        bool: True if the error was handled, False otherwise
    """
    # Unwrap CommandInvokeError if needed
    if hasattr(error, "original"):
        error = error.original
        
    # Log the error
    command_name = "Unknown command"
    guild_name = "Unknown guild"
    channel_name = "Unknown channel"
    user_name = "Unknown user"
    
    # Extract command and context information based on context type
    if isinstance(ctx_or_interaction, commands.Context):
        ctx = ctx_or_interaction
        command_name = ctx.command.qualified_name if ctx.command else "Unknown command"
        guild_name = ctx.guild.name if ctx.guild else "DM"
        channel_name = getattr(ctx.channel, "name", "Unknown")
        user_name = str(ctx.author)
        
        # Handle cooldown errors
        if isinstance(error, commands.CommandOnCooldown):
            seconds = round(error.retry_after)
            message = f"This command is on cooldown. Please try again in {seconds} seconds."
            await ctx.send(message, ephemeral=ephemeral)
            return True
            
        # Handle permission errors
        elif isinstance(error, commands.MissingPermissions):
            perms = ", ".join(f"`{p}`" for p in error.missing_permissions)
            message = f"You need the following permissions to use this command: {perms}"
            await ctx.send(message, ephemeral=ephemeral)
            return True
            
        # Handle bot permission errors
        elif isinstance(error, commands.BotMissingPermissions):
            perms = ", ".join(f"`{p}`" for p in error.missing_permissions)
            message = f"I need the following permissions to execute this command: {perms}"
            await ctx.send(message, ephemeral=ephemeral)
            return True
            
        # Handle missing arguments
        elif isinstance(error, commands.MissingRequiredArgument):
            message = f"Missing required argument: `{error.param.name}`."
            usage = f"Usage: `{ctx.prefix}{format_command_signature(ctx.command)}`"
            await ctx.send(f"{message}\n{usage}", ephemeral=ephemeral)
            return True
            
        # Handle check failures like guild_only
        elif isinstance(error, commands.NoPrivateMessage) or (
            isinstance(error, commands.CheckFailure) and 
            ctx.command and is_guild_only(ctx.command)
        ):
            await ctx.send("This command can only be used in a server, not in DMs.", ephemeral=ephemeral)
            return True
            
        # Handle bad arguments
        elif isinstance(error, commands.BadArgument):
            message = f"Invalid argument: {str(error)}"
            await ctx.send(message, ephemeral=ephemeral)
            return True
        
    # Handle interaction-based errors (application commands)
    elif isinstance(ctx_or_interaction, discord.Interaction):
        interaction = ctx_or_interaction
        command_name = getattr(interaction.command, "name", "Unknown command") if hasattr(interaction, "command") else "Unknown command"
        guild_name = interaction.guild.name if interaction.guild else "DM"
        channel_name = getattr(interaction.channel, "name", "Unknown") if interaction.channel else "Unknown"
        user_name = str(interaction.user)
        
        # Check if the response has already been sent
        try:
            # Special handling for missing permissions in app commands
            if isinstance(error, discord.app_commands.errors.MissingPermissions):
                perms = ", ".join(f"`{p}`" for p in getattr(error, "missing_permissions", ["unknown"]))
                message = f"You need the following permissions to use this command: {perms}"
                await interaction.response.send_message(message, ephemeral=ephemeral)
                return True
                
            # Handle check failures such as guild_only
            elif isinstance(error, discord.app_commands.errors.CheckFailure):
                resource = getattr(error, "resource", None)
                if resource == "guild":
                    await interaction.response.send_message("This command can only be used in a server, not in DMs.", ephemeral=ephemeral)
                    return True
                    
            # Handle cooldowns
            elif hasattr(discord.app_commands, "errors") and hasattr(discord.app_commands.errors, "CommandOnCooldown") and isinstance(error, discord.app_commands.errors.CommandOnCooldown):
                seconds = round(error.retry_after)
                message = f"This command is on cooldown. Please try again in {seconds} seconds."
                await interaction.response.send_message(message, ephemeral=ephemeral)
                return True
        except discord.InteractionResponded:
            # Interaction has already been responded to
            pass
            
    # Log the error with context information
    error_type = type(error).__name__
    error_data = get_error_data(error)
    
    logger.error(f"Command error in {guild_name}/{channel_name} by {user_name} for command '{command_name}': {error_type}: {str(error)}")
    
    # Log traceback for unexpected errors
    if "traceback" in error_data:
        logger.error("".join(error_data["traceback"]))
    
    # Return False for unhandled errors, allowing them to propagate
    return False