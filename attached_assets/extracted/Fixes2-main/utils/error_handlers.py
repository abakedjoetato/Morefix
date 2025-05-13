"""
Error Handlers for Tower of Temptation PvP Statistics Bot

This module provides specialized error handlers:
1. Discord command error handlers
2. SFTP operation error handlers
3. Database operation error handlers
4. Rate limiting and timeout handlers
5. User-friendly error responses

The handlers integrate with the error telemetry system for tracking and analysis.
"""
import logging
import asyncio
import re
import traceback
from datetime import datetime
from typing import Dict, Any, Optional, Union, Callable, List

import discord
from discord.ext import commands

from utils.error_telemetry import ErrorTelemetry, categorize_error
from utils.sftp_exceptions import SFTPError, format_error_for_user

# Configure module-specific logger
logger = logging.getLogger(__name__)

# Error response templates
ERROR_TEMPLATES = {
    "default": {
        "title": "An error occurred",
        "color": 0xE74C3C,  # Red
        "description": "Sorry, something went wrong while processing your request.",
        "footer": "Error ID: {error_id}"
    },
    "permission": {
        "title": "Permission Error",
        "color": 0xF39C12,  # Orange
        "description": "You don't have permission to use this command.",
        "footer": "Required permission: {permission}"
    },
    "validation": {
        "title": "Invalid Input",
        "color": 0x3498DB,  # Blue
        "description": "The provided input is invalid: {message}",
        "footer": "Please check the command help for correct usage."
    },
    "timeout": {
        "title": "Request Timed Out",
        "color": 0xE74C3C,  # Red
        "description": "The operation took too long to complete and timed out.",
        "footer": "Please try again later."
    },
    "not_found": {
        "title": "Not Found",
        "color": 0x95A5A6,  # Gray
        "description": "The requested {resource} could not be found.",
        "footer": "Please check your input and try again."
    },
    "rate_limit": {
        "title": "Rate Limited",
        "color": 0xF39C12,  # Orange
        "description": "You're doing that too frequently. Please wait {retry_after:.1f} seconds before trying again.",
        "footer": "Rate limits help ensure fair usage for all users."
    },
    "discord_api": {
        "title": "Discord API Error",
        "color": 0xE74C3C,  # Red
        "description": "There was an error communicating with Discord: {message}",
        "footer": "This issue is likely temporary. Please try again later."
    },
    "database": {
        "title": "Database Error",
        "color": 0xE74C3C,  # Red
        "description": "There was a problem with the database operation.",
        "footer": "Error ID: {error_id}"
    },
    "sftp": {
        "title": "SFTP Error",
        "color": 0xE74C3C,  # Red
        "description": "There was a problem with the SFTP operation: {message}",
        "footer": "Error ID: {error_id}"
    }
}

# User-friendly error message patterns
USER_FRIENDLY_PATTERNS = [
    # Discord API errors
    (r"(?i)Unknown interaction", "The command interaction expired. Please try again."),
    (r"(?i)Unknown [Mm]essage", "The message was deleted or is too old to interact with."),
    (r"(?i)Cannot send an empty message", "The response couldn't be generated properly. Please try again."),
    (r"(?i)Missing Permissions", "I don't have the necessary permissions to complete this action."),
    (r"(?i)Interaction has already been responded to", "The command took too long to process. Please try again."),
    
    # Permission errors
    (r"(?i)Missing.*permission", "You don't have the required permissions for this command."),
    (r"(?i)You need (\w+) permission", "You need {1} permission to use this command."),
    
    # SFTP errors
    (r"(?i)Authentication failed", "SFTP authentication failed. Please check your username and password."),
    (r"(?i)Connection refused", "Couldn't connect to the SFTP server. Please check if it's online."),
    (r"(?i)No such file", "The specified file doesn't exist on the server."),
    (r"(?i)Path not found", "The specified path doesn't exist on the server."),
    
    # Database errors
    (r"(?i)duplicate key error", "This record already exists in the database."),
    (r"(?i)connection.*closed", "Database connection error. Please try again."),
    
    # Rate limits
    (r"(?i)rate limited", "You're doing that too frequently. Please wait and try again."),
    
    # Validation errors
    (r"(?i)invalid.*format", "The input format is invalid. Please check and try again."),
    (r"(?i)required parameter", "A required parameter is missing. Please check the command syntax."),
    
    # Timeout errors
    (r"(?i)timed out", "The operation took too long and timed out. Please try again later.")
]

def format_user_friendly_error(error: Exception) -> str:
    """Format an exception as a user-friendly message
    
    Args:
        error: The exception to format
        
    Returns:
        User-friendly error message
    """
    error_str = str(error)
    
    # Check if this is an SFTP error with a user-friendly format
    if isinstance(error, SFTPError):
        return format_error_for_user(error)
    
    # Try to match against known patterns
    for pattern, message in USER_FRIENDLY_PATTERNS:
        match = re.search(pattern, error_str)
        if match:
            # If the message has format groups, fill them in
            if '{' in message and '}' in message and len(match.groups()) > 0:
                try:
                    return message.format(*match.groups())
                except:
                    pass
            return message
    
    # For CheckFailure errors, extract the check name
    if isinstance(error, commands.CheckFailure):
        check_name = type(error).__name__.replace('Check', '').replace('Failure', '')
        if check_name:
            return f"Check failed: {check_name}. You may not have the required permissions."
    
    # For CommandNotFound, give a helpful message
    if isinstance(error, commands.CommandNotFound):
        return "That command doesn't exist. Use `/help` to see available commands."
    
    # For UserInputError, try to give specific guidance
    if isinstance(error, commands.UserInputError):
        if isinstance(error, commands.MissingRequiredArgument):
            return f"Missing required argument: `{error.param.name}`"
        elif isinstance(error, commands.BadArgument):
            return f"Invalid argument: {str(error)}"
        elif isinstance(error, commands.TooManyArguments):
            return "Too many arguments provided."
        elif isinstance(error, commands.BadUnionArgument):
            return f"Could not convert to any of: {', '.join(c.__name__ for c in error.converters)}"
        else:
            return f"Invalid input: {str(error)}"
    
    # Fall back to a generic message for other errors
    return "An error occurred while processing your request."

async def handle_command_error(interaction: discord.Interaction, error: Exception) -> discord.Embed:
    """Handle a Discord command error
    
    Args:
        interaction: Discord interaction
        error: The exception that occurred
        
    Returns:
        Discord embed with error information
    """
    # Track the error
    context = {
        "interaction": interaction,
        "guild_id": str(interaction.guild.id) if interaction.guild else None,
        "channel_id": str(interaction.channel.id) if interaction.channel else None,
        "user_id": str(interaction.user.id) if interaction.user else None,
        "command": interaction.command.name if hasattr(interaction, 'command') and interaction.command else None
    }
    
    # Determine error category
    category = categorize_error(error, context)
    
    # Track the error
    error_id = await ErrorTelemetry.track_error(
        error=error,
        context=context,
        category=category
    )
    
    # Get user-friendly message
    user_message = format_user_friendly_error(error)
    
    # Choose template based on category
    template = ERROR_TEMPLATES.get(category, ERROR_TEMPLATES["default"])
    
    # Create embed
    embed = discord.Embed(
        title=template["title"],
        description=template["description"].format(message=user_message),
        color=template["color"]
    )
    
    # Add error ID to footer if available
    footer_text = template["footer"].format(
        error_id=error_id[:8] if error_id else "Unknown",
        permission=str(error) if isinstance(error, commands.MissingPermissions) else "unknown",
        resource="item" if not hasattr(error, "resource") else error.resource
    )
    embed.set_footer(text=footer_text)
    
    # Log the error
    logger.error(f"Command error in {interaction.command.name if hasattr(interaction, 'command') and interaction.command else 'unknown command'}: {error}")
    
    return embed

async def handle_sftp_error(error: Exception, context: Dict[str, Any] = None) -> dict:
    """Handle an SFTP operation error
    
    Args:
        error: The exception that occurred
        context: Optional context information
        
    Returns:
        Dictionary with error information
    """
    # Default context if none provided
    if context is None:
        context = {}
    
    # Add SFTP-specific context
    sftp_context = {
        "sftp_operation": context.get("operation", "unknown"),
        **context
    }
    
    # Track the error
    error_id = await ErrorTelemetry.track_error(
        error=error,
        context=sftp_context,
        category="sftp"
    )
    
    # Get user-friendly message
    user_message = format_error_for_user(error) if isinstance(error, SFTPError) else format_user_friendly_error(error)
    
    # Log the error
    logger.error(f"SFTP error in {sftp_context.get('operation', 'unknown operation')}: {error}")
    
    # Return error information
    return {
        "success": False,
        "error": str(error),
        "user_message": user_message,
        "error_id": error_id,
        "category": "sftp",
        "timestamp": datetime.utcnow().isoformat()
    }

async def handle_database_error(error: Exception, context: Dict[str, Any] = None) -> dict:
    """Handle a database operation error
    
    Args:
        error: The exception that occurred
        context: Optional context information
        
    Returns:
        Dictionary with error information
    """
    # Default context if none provided
    if context is None:
        context = {}
    
    # Add database-specific context
    db_context = {
        "database_operation": context.get("operation", "unknown"),
        **context
    }
    
    # Track the error
    error_id = await ErrorTelemetry.track_error(
        error=error,
        context=db_context,
        category="database"
    )
    
    # Get user-friendly message
    user_message = format_user_friendly_error(error)
    
    # Log the error
    logger.error(f"Database error in {db_context.get('operation', 'unknown operation')}: {error}")
    
    # Return error information
    return {
        "success": False,
        "error": str(error),
        "user_message": user_message,
        "error_id": error_id,
        "category": "database",
        "timestamp": datetime.utcnow().isoformat()
    }

async def send_error_response(interaction: discord.Interaction, error: Exception, ephemeral: bool = True):
    """Send an error response to a Discord interaction
    
    Args:
        interaction: Discord interaction
        error: The exception that occurred
        ephemeral: Whether the response should be ephemeral
    """
    # Create error embed
    embed = await handle_command_error(interaction, error)
    
    # Check if we've already responded
    try:
        if interaction.response.is_done():
            # If already responded, use followup
            await interaction.followup.send(embed=embed, ephemeral=ephemeral)
        else:
            # Otherwise respond directly
            await interaction.response.send_message(embed=embed, ephemeral=ephemeral)
    except Exception as e:
        # If we can't respond, log it
        logger.error(f"Failed to send error response: {e}")

def error_handler_middleware(func):
    """Decorator for adding error handling to commands
    
    Args:
        func: The command function to wrap
        
    Returns:
        Wrapped function with error handling
    """
    async def wrapper(self, interaction: discord.Interaction, *args, **kwargs):
        try:
            # Run the original function
            return await func(self, interaction, *args, **kwargs)
        except Exception as error:
            # Handle the error
            await send_error_response(interaction, error)
            
            # Re-raise if it's a serious error that should stop command processing
            if isinstance(error, (commands.CommandError, SFTPError)):
                # These are expected errors, no need to re-raise
                pass
            else:
                # Unexpected error, re-raise for global handlers
                raise
    
    return wrapper