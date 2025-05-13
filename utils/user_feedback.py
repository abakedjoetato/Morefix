"""
User Feedback for Tower of Temptation PvP Statistics Bot

This module provides user-friendly feedback mechanisms:
1. Error message generation with actionable suggestions
2. Status messages for long-running operations
3. Success indicators with helpful next steps
4. Interactive help and troubleshooting guides

The feedback is designed to help users resolve issues on their own.
"""
import logging
import re
import random
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime

import discord
from discord import Embed, Color

from utils.error_telemetry import ErrorTelemetry

# Configure module-specific logger
logger = logging.getLogger(__name__)

# Standard colors
COLORS = {
    "primary": discord.Color.from_rgb(59, 136, 195),   # Blue
    "success": discord.Color.from_rgb(46, 204, 113),   # Green
    "warning": discord.Color.from_rgb(241, 196, 15),   # Yellow
    "error": discord.Color.from_rgb(231, 76, 60),      # Red
    "info": discord.Color.from_rgb(52, 152, 219),      # Light Blue
    "neutral": discord.Color.from_rgb(149, 165, 166)   # Gray
}

# Standard icons (Discord emoji or unicode)
ICONS = {
    "success": "✅",
    "error": "❌",
    "warning": "⚠️",
    "info": "ℹ️",
    "waiting": "⏳",
    "premium": "⭐",
    "settings": "⚙️",
    "help": "❓",
    "server": "🖥️",
    "database": "🗄️",
    "sftp": "📁",
    "logs": "📊",
    "time": "⏱️",
    "user": "👤",
    "guild": "🏠"
}

# Error suggestion templates
ERROR_SUGGESTIONS = {
    # SFTP errors
    "sftp_connection": [
        "Check that the server address and port are correct",
        "Verify that the server is online and accepting connections",
        "Ensure your firewall isn't blocking the connection",
        "Try connecting with a different SFTP client to verify the server is working"
    ],
    "sftp_authentication": [
        "Verify your username and password are correct",
        "Check if the account has SFTP access permissions",
        "Try regenerating your SFTP credentials on the server"
    ],
    "sftp_file_access": [
        "Check that the file path is correct",
        "Verify that you have permission to access this file",
        "Ensure the file hasn't been moved or deleted"
    ],
    "sftp_timeout": [
        "The server might be under heavy load, try again later",
        "Try smaller operations if you're working with large files",
        "Check your network connection stability"
    ],
    
    # Discord API errors
    "discord_rate_limit": [
        "You're making requests too quickly, please wait and try again",
        "Try using fewer commands in a short period",
        "Consider using bulk operations instead of many individual commands"
    ],
    "discord_permission": [
        "The bot needs additional permissions to perform this action",
        "Check the bot's role and channel permissions",
        "Try re-inviting the bot with the correct permissions"
    ],
    "discord_interaction": [
        "The interaction has expired, please try the command again",
        "Discord interactions have a short timeout, try a faster operation",
        "If this happens frequently, report it as a bug"
    ],
    
    # Database errors
    "database_connection": [
        "There might be an issue with our database, please try again later",
        "If the problem persists, report it to the bot administrators"
    ],
    "database_query": [
        "The data you're trying to access might not exist",
        "Check your search parameters and try again",
        "If you're sure the data should exist, it might be a bug"
    ],
    
    # User input errors
    "invalid_input": [
        "Please check the command syntax and try again",
        "Review the help documentation for correct usage",
        "Make sure all required parameters are provided"
    ],
    "invalid_format": [
        "The format of your input is incorrect",
        "Make sure you're using the correct format (e.g., dates, IDs, etc.)",
        "Check the examples in the command help"
    ],
    
    # Permission errors
    "missing_permission": [
        "You don't have permission to use this command",
        "Ask a server administrator to grant you the necessary role",
        "Some commands are restricted to specific roles or users"
    ],
    
    # Premium errors
    "premium_required": [
        "This feature requires a premium subscription",
        "Upgrade to premium to unlock this feature",
        "See `/premium info` for subscription details"
    ],
    
    # General errors
    "general": [
        "If this problem persists, please report it to the bot administrators",
        "Try using a related command that might accomplish what you need",
        "Check for announcements about known issues"
    ]
}

def create_error_embed(
    title: str,
    description: str,
    error_type: str = "general",
    error_id: Optional[str] = None,
    fields: Optional[List[Dict[str, str]]] = None,
    include_timestamp: bool = True
) -> discord.Embed:
    """Create an error embed with suggestions
    
    Args:
        title: Error title
        description: Error description
        error_type: Type of error for suggestions
        error_id: Optional error tracking ID
        fields: Optional additional fields
        include_timestamp: Whether to include a timestamp
        
    Returns:
        Discord embed with error information and suggestions
    """
    # Create embed with error styling
    embed = discord.Embed(
        title=f"{ICONS['error']} {title}",
        description=description,
        color=COLORS["error"]
    )
    
    # Add timestamp if requested
    if include_timestamp:
        embed.timestamp = datetime.utcnow()
    
    # Add error ID if provided
    if error_id:
        embed.set_footer(text=f"Error ID: {error_id[:8]}")
    
    # Add any additional fields
    if fields:
        for field in fields:
            embed.add_field(
                name=field["name"],
                value=field["value"],
                inline=field.get("inline", False)
            )
    
    # Add suggestions for fixing the error
    suggestions = ERROR_SUGGESTIONS.get(error_type, ERROR_SUGGESTIONS["general"])
    if suggestions:
        # Choose up to 3 random suggestions
        if len(suggestions) > 3:
            chosen_suggestions = random.sample(suggestions, 3)
        else:
            chosen_suggestions = suggestions
        
        # Format suggestions
        suggestion_text = "\n".join([f"• {s}" for s in chosen_suggestions])
        embed.add_field(
            name="Suggestions",
            value=suggestion_text,
            inline=False
        )
    
    return embed

def create_success_embed(
    title: str,
    description: str,
    fields: Optional[List[Dict[str, str]]] = None,
    include_timestamp: bool = True
) -> discord.Embed:
    """Create a success embed
    
    Args:
        title: Success title
        description: Success description
        fields: Optional additional fields
        include_timestamp: Whether to include a timestamp
        
    Returns:
        Discord embed with success information
    """
    # Create embed with success styling
    embed = discord.Embed(
        title=f"{ICONS['success']} {title}",
        description=description,
        color=COLORS["success"]
    )
    
    # Add timestamp if requested
    if include_timestamp:
        embed.timestamp = datetime.utcnow()
    
    # Add any additional fields
    if fields:
        for field in fields:
            embed.add_field(
                name=field["name"],
                value=field["value"],
                inline=field.get("inline", False)
            )
    
    return embed

def create_info_embed(
    title: str,
    description: str,
    fields: Optional[List[Dict[str, str]]] = None,
    include_timestamp: bool = True
) -> discord.Embed:
    """Create an information embed
    
    Args:
        title: Info title
        description: Info description
        fields: Optional additional fields
        include_timestamp: Whether to include a timestamp
        
    Returns:
        Discord embed with information
    """
    # Create embed with info styling
    embed = discord.Embed(
        title=f"{ICONS['info']} {title}",
        description=description,
        color=COLORS["info"]
    )
    
    # Add timestamp if requested
    if include_timestamp:
        embed.timestamp = datetime.utcnow()
    
    # Add any additional fields
    if fields:
        for field in fields:
            embed.add_field(
                name=field["name"],
                value=field["value"],
                inline=field.get("inline", False)
            )
    
    return embed

def create_warning_embed(
    title: str,
    description: str,
    fields: Optional[List[Dict[str, str]]] = None,
    include_timestamp: bool = True
) -> discord.Embed:
    """Create a warning embed
    
    Args:
        title: Warning title
        description: Warning description
        fields: Optional additional fields
        include_timestamp: Whether to include a timestamp
        
    Returns:
        Discord embed with warning information
    """
    # Create embed with warning styling
    embed = discord.Embed(
        title=f"{ICONS['warning']} {title}",
        description=description,
        color=COLORS["warning"]
    )
    
    # Add timestamp if requested
    if include_timestamp:
        embed.timestamp = datetime.utcnow()
    
    # Add any additional fields
    if fields:
        for field in fields:
            embed.add_field(
                name=field["name"],
                value=field["value"],
                inline=field.get("inline", False)
            )
    
    return embed

def create_loading_embed(
    title: str,
    description: str,
    fields: Optional[List[Dict[str, str]]] = None
) -> discord.Embed:
    """Create a loading/progress embed
    
    Args:
        title: Loading title
        description: Loading description
        fields: Optional additional fields
        
    Returns:
        Discord embed with loading information
    """
    # Create embed with neutral styling
    embed = discord.Embed(
        title=f"{ICONS['waiting']} {title}",
        description=description,
        color=COLORS["neutral"]
    )
    
    embed.timestamp = datetime.utcnow()
    
    # Add any additional fields
    if fields:
        for field in fields:
            embed.add_field(
                name=field["name"],
                value=field["value"],
                inline=field.get("inline", False)
            )
    
    return embed

def create_premium_embed(
    title: str,
    description: str,
    fields: Optional[List[Dict[str, str]]] = None,
    include_timestamp: bool = True
) -> discord.Embed:
    """Create a premium feature embed
    
    Args:
        title: Premium title
        description: Premium description
        fields: Optional additional fields
        include_timestamp: Whether to include a timestamp
        
    Returns:
        Discord embed with premium information
    """
    # Create embed with premium styling (using primary color)
    embed = discord.Embed(
        title=f"{ICONS['premium']} {title}",
        description=description,
        color=COLORS["primary"]
    )
    
    # Add timestamp if requested
    if include_timestamp:
        embed.timestamp = datetime.utcnow()
    
    # Add premium fields
    embed.add_field(
        name="Premium Feature",
        value="This is a premium feature. Upgrade to unlock!",
        inline=False
    )
    
    # Add any additional fields
    if fields:
        for field in fields:
            embed.add_field(
                name=field["name"],
                value=field["value"],
                inline=field.get("inline", False)
            )
    
    # Add premium command footer
    embed.set_footer(text="Use /premium info to learn more")
    
    return embed

async def create_error_resolution_guide(error_type: str, context: Dict[str, Any] = None) -> discord.Embed:
    """Create a detailed error resolution guide
    
    Args:
        error_type: Type of error for guide generation
        context: Optional context information
        
    Returns:
        Discord embed with detailed error resolution steps
    """
    # Default context if none provided
    if context is None:
        context = {}
    
    # Generate appropriate title and description
    if error_type == "sftp_connection":
        title = "SFTP Connection Troubleshooting Guide"
        description = (
            "Follow these steps to resolve SFTP connection issues:\n\n"
            "SFTP connection problems are usually related to network, authentication, or server configuration issues."
        )
        
        # Create embed
        embed = discord.Embed(
            title=f"{ICONS['sftp']} {title}",
            description=description,
            color=COLORS["info"]
        )
        
        # Add steps
        embed.add_field(
            name="1. Verify Server Status",
            value=(
                "• Check if the server is online and running\n"
                "• Verify the hostname and port are correct\n"
                "• Try pinging the server to check connectivity"
            ),
            inline=False
        )
        
        embed.add_field(
            name="2. Check Authentication",
            value=(
                "• Verify your username and password are correct\n"
                "• Check if the account has SFTP access permissions\n"
                "• Try regenerating your SFTP credentials"
            ),
            inline=False
        )
        
        embed.add_field(
            name="3. Network Configuration",
            value=(
                "• Check if your firewall is blocking SFTP connections\n"
                "• Verify that the server's firewall allows your connection\n"
                "• Check if your ISP blocks port 22 (common for SFTP)"
            ),
            inline=False
        )
        
        embed.add_field(
            name="4. Test with Another Client",
            value=(
                "• Try connecting with FileZilla or another SFTP client\n"
                "• If it works, the issue is with the bot's connection\n"
                "• If it fails, the problem is with the server or credentials"
            ),
            inline=False
        )
        
    elif error_type == "command_usage":
        command_name = context.get("command", "unknown")
        title = f"Command Usage Guide: /{command_name}"
        description = f"Learn how to properly use the `/{command_name}` command."
        
        # Create embed
        embed = discord.Embed(
            title=f"{ICONS['help']} {title}",
            description=description,
            color=COLORS["info"]
        )
        
        # Add usage information
        embed.add_field(
            name="Syntax",
            value=f"`/{command_name} [parameters]`",
            inline=False
        )
        
        # Add parameters if available
        if "parameters" in context:
            params_text = ""
            for param in context["parameters"]:
                required = param.get("required", False)
                params_text += f"• `{param['name']}`: {param['description']}"
                params_text += " (Required)" if required else " (Optional)"
                params_text += "\n"
                
            embed.add_field(
                name="Parameters",
                value=params_text,
                inline=False
            )
        
        # Add examples if available
        if "examples" in context:
            examples_text = ""
            for example in context["examples"]:
                examples_text += f"• `/{command_name} {example}`\n"
                
            embed.add_field(
                name="Examples",
                value=examples_text,
                inline=False
            )
        
    elif error_type == "rate_limit":
        title = "Rate Limit Information"
        description = (
            "You've hit a rate limit, which means you're making requests too quickly.\n\n"
            "Rate limits are in place to ensure fair usage of the bot and to prevent abuse."
        )
        
        # Create embed
        embed = discord.Embed(
            title=f"{ICONS['time']} {title}",
            description=description,
            color=COLORS["warning"]
        )
        
        # Add explanation
        embed.add_field(
            name="Why Rate Limits Exist",
            value=(
                "• Protect the bot from abuse\n"
                "• Ensure fair resource distribution\n"
                "• Prevent Discord API rate limits\n"
                "• Maintain stable performance"
            ),
            inline=False
        )
        
        # Add resolution steps
        embed.add_field(
            name="How to Resolve",
            value=(
                "• Wait before trying again\n"
                "• Use bulk operations instead of many individual commands\n"
                "• Spread your commands out over time\n"
                "• Consider upgrading to premium for higher limits"
            ),
            inline=False
        )
        
        # Add rate limit info
        standard_limit = context.get("standard_limit", "5 operations per minute")
        premium_limit = context.get("premium_limit", "20 operations per minute")
        
        embed.add_field(
            name="Rate Limits",
            value=(
                f"• Standard users: {standard_limit}\n"
                f"• Premium users: {premium_limit}"
            ),
            inline=False
        )
        
    else:
        # Default generic guide
        title = "Troubleshooting Guide"
        description = "Follow these steps to resolve your issue:"
        
        # Create embed
        embed = discord.Embed(
            title=f"{ICONS['help']} {title}",
            description=description,
            color=COLORS["info"]
        )
        
        # Add generic steps
        embed.add_field(
            name="1. Check Command Syntax",
            value=(
                "• Make sure you're using the correct command syntax\n"
                "• Verify all required parameters are provided\n"
                "• Check the command help for examples"
            ),
            inline=False
        )
        
        embed.add_field(
            name="2. Check Permissions",
            value=(
                "• Ensure you have the necessary permissions\n"
                "• Verify the bot has the required permissions\n"
                "• Some commands require server administrator rights"
            ),
            inline=False
        )
        
        embed.add_field(
            name="3. Check for Known Issues",
            value=(
                "• Check for announcements about known issues\n"
                "• Try again later if it's a temporary problem\n"
                "• Report the issue if it persists"
            ),
            inline=False
        )
    
    # Add timestamp
    embed.timestamp = datetime.utcnow()
    
    # Add footer
    embed.set_footer(text="Contact support if you need further assistance")
    
    return embed

def get_suggestion_for_error(error: Exception, context: Dict[str, Any] = None) -> str:
    """Get a helpful suggestion for resolving an error
    
    Args:
        error: The exception that occurred
        context: Optional context information
        
    Returns:
        Suggestion string
    """
    error_str = str(error)
    
    # Determine error type for relevant suggestions
    if re.search(r"(?i)connection refused|connect|timed out|host|network", error_str):
        error_type = "sftp_connection"
    elif re.search(r"(?i)auth|login|password|permission denied", error_str):
        error_type = "sftp_authentication"
    elif re.search(r"(?i)no such file|file not found|directory|path", error_str):
        error_type = "sftp_file_access"
    elif re.search(r"(?i)timed out|timeout", error_str):
        error_type = "sftp_timeout"
    elif re.search(r"(?i)rate limit|too many requests", error_str):
        error_type = "discord_rate_limit"
    elif re.search(r"(?i)permission|not allowed|forbidden", error_str):
        error_type = "missing_permission"
    elif re.search(r"(?i)premium|subscribe|upgrade", error_str):
        error_type = "premium_required"
    elif re.search(r"(?i)invalid|format|wrong|incorrect", error_str):
        error_type = "invalid_format"
    elif re.search(r"(?i)database|query|mongodb", error_str):
        error_type = "database_query"
    else:
        error_type = "general"
    
    # Get suggestions for this error type
    suggestions = ERROR_SUGGESTIONS.get(error_type, ERROR_SUGGESTIONS["general"])
    
    # Return a random suggestion
    return random.choice(suggestions)