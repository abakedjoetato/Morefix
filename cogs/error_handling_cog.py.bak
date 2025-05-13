"""
Error Handling Cog for Tower of Temptation PvP Statistics Bot

This cog provides centralized error handling for all commands:
1. User-friendly error messages with solving suggestions
2. Error tracking and analytics
3. Administrator debug commands
4. Detailed error diagnostics
5. Advanced error pattern detection
"""
import os
import logging
import traceback
import datetime
import re
import json
from typing import Dict, Any, Optional, List, Union

import discord
from discord.ext import commands
from discord import app_commands

from utils.error_telemetry import ErrorTelemetry
from utils.error_handlers import (
    handle_command_error, handle_sftp_error, handle_database_error,
    send_error_response, format_user_friendly_error
)
from utils.user_feedback import (
    create_error_embed, create_error_resolution_guide,
    get_suggestion_for_error
)

# Configure module-specific logger
logger = logging.getLogger(__name__)

# Checks for admin and developer permissions
def is_bot_admin():
    """Check if user is a bot administrator"""
    async def predicate(interaction: discord.Interaction):
        if not interaction.guild:
            return False
            
        # Check if user has administrator permission
        if interaction.user.guild_permissions.administrator:
            return True
            
        # Check if user is in admin list
        bot = interaction.client
        if hasattr(bot, 'config') and hasattr(bot.config, 'BOT_ADMINS'):
            admin_ids = getattr(bot.config, 'BOT_ADMINS', [])
            return str(interaction.user.id) in admin_ids
            
        return False
    return app_commands.check(predicate)

def is_bot_developer():
    """Check if user is a bot developer"""
    async def predicate(interaction: discord.Interaction):
        # Check if user is in developer list
        bot = interaction.client
        if hasattr(bot, 'config') and hasattr(bot.config, 'BOT_DEVELOPERS'):
            dev_ids = getattr(bot.config, 'BOT_DEVELOPERS', [])
            return str(interaction.user.id) in dev_ids
            
        return False
    return app_commands.check(predicate)

class ErrorHandlingCog(commands.Cog):
    """Error handling and diagnostics for the bot"""
    
    def __init__(self, bot):
        """Initialize the error handling cog
        
        Args:
            bot: Bot instance
        """
        self.bot = bot
        
        # Initialize error telemetry
        self.bot.loop.create_task(self._initialize_telemetry())
        
        # Set up global error handlers
        self._setup_error_handlers()
        
        logger.info("Error handling cog initialized")
    
    async def _initialize_telemetry(self):
        """Initialize error telemetry system"""
        from utils.error_telemetry import initialize_error_telemetry
        
        try:
            # Wait until bot is ready to ensure database is available
            await self.bot.wait_until_ready()
            
            # Initialize telemetry
            self.telemetry = await initialize_error_telemetry(self.bot)
            logger.info("Error telemetry system initialized")
        except Exception as e:
            logger.error(f"Failed to initialize error telemetry: {e}")
    
    def _setup_error_handlers(self):
        """Set up global error handlers for the bot"""
        # Set up application command error handler
        self.bot.tree.on_error = self.on_app_command_error
        
        # Set up global command error handler
        self.bot.add_listener(self.on_command_error, "on_command_error")
        
        # Set up interaction error handler
        self.bot.add_listener(self.on_interaction_error, "on_interaction_error")
    
    async def on_app_command_error(self, interaction: discord.Interaction, error: Exception):
        """Handle application command errors
        
        Args:
            interaction: Discord interaction
            error: Exception that occurred
        """
        # Unwrap CommandInvokeError
        if isinstance(error, app_commands.CommandInvokeError):
            error = error.original
        
        # Track the error
        context = {
            "interaction": interaction,
            "guild_id": str(interaction.guild.id) if interaction.guild else None,
            "channel_id": str(interaction.channel.id) if interaction.channel else None,
            "user_id": str(interaction.user.id) if interaction.user else None,
            "command": interaction.command.name if hasattr(interaction, 'command') and interaction.command else None
        }
        
        await ErrorTelemetry.track_error(
            error=error,
            context=context
        )
        
        # Send error response
        await send_error_response(interaction, error)
        
        # Log the error
        command_name = interaction.command.name if hasattr(interaction, 'command') and interaction.command else "unknown"
        logger.error(f"Error in app command '{command_name}': {error}")
        logger.error(traceback.format_exception(type(error), error, error.__traceback__))
    
    async def on_command_error(self, ctx: commands.Context, error: Exception):
        """Handle prefix command errors
        
        Args:
            ctx: Command context
            error: Exception that occurred
        """
        # Unwrap CommandInvokeError
        if isinstance(error, commands.CommandInvokeError):
            error = error.original
        
        # Track the error
        context = {
            "message": ctx.message,
            "guild_id": str(ctx.guild.id) if ctx.guild else None,
            "channel_id": str(ctx.channel.id) if ctx.channel else None,
            "author_id": str(ctx.author.id) if ctx.author else None,
            "command": ctx.command.name if ctx.command else None
        }
        
        await ErrorTelemetry.track_error(
            error=error,
            context=context
        )
        
        # Get user-friendly message
        user_message = format_user_friendly_error(error)
        
        # Determine error color
        if isinstance(error, (commands.UserInputError, commands.CheckFailure)):
            color = discord.Color.orange()
        else:
            color = discord.Color.red()
        
        # Send error message
        try:
            await ctx.send(
                embed=discord.Embed(
                    title="Error",
                    description=user_message,
                    color=color
                )
            )
        except Exception:
            # If sending embed fails, try plain message
            try:
                await ctx.send(f"Error: {user_message}")
            except Exception:
                pass
        
        # Log the error
        command_name = ctx.command.name if ctx.command else "unknown"
        logger.error(f"Error in prefix command '{command_name}': {error}")
        logger.error(traceback.format_exception(type(error), error, error.__traceback__))
    
    async def on_interaction_error(self, interaction: discord.Interaction, error: Exception):
        """Handle general interaction errors
        
        Args:
            interaction: Discord interaction
            error: Exception that occurred
        """
        # Track the error
        context = {
            "interaction": interaction,
            "guild_id": str(interaction.guild.id) if interaction.guild else None,
            "channel_id": str(interaction.channel.id) if interaction.channel else None,
            "user_id": str(interaction.user.id) if interaction.user else None,
            "interaction_type": str(interaction.type) if hasattr(interaction, 'type') else "unknown"
        }
        
        await ErrorTelemetry.track_error(
            error=error,
            context=context
        )
        
        # Try to respond to the interaction
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    f"An error occurred: {format_user_friendly_error(error)}",
                    ephemeral=True
                )
        except Exception:
            pass
        
        # Log the error
        logger.error(f"Error in interaction: {error}")
        logger.error(traceback.format_exception(type(error), error, error.__traceback__))
    
    # Error analysis command
    @app_commands.command(
        name="debug",
        description="Debug a specific error or view recent errors [Admin only]"
    )
    @app_commands.describe(
        error_id="Optional specific error ID to debug",
        show_recent="Show recent errors for this server"
    )
    @is_bot_admin()
    async def debug_command(
        self,
        interaction: discord.Interaction,
        error_id: Optional[str] = None,
        show_recent: Optional[bool] = False
    ):
        """Debug command for administrators
        
        Args:
            interaction: Discord interaction
            error_id: Optional specific error ID to debug
            show_recent: Show recent errors for this server
        """
        await interaction.response.defer(ephemeral=True)
        
        # Get database
        db = self.bot.db()
        
        if error_id:
            # Look up specific error
            error = await db.errors.find_one({"fingerprint": error_id})
            
            if not error:
                # Try looking up by substring
                async for doc in db.errors.find({"fingerprint": {"$regex": error_id}}):
                    error = doc
                    break
            
            if error:
                # Create embed with error details
                embed = discord.Embed(
                    title=f"Error Debug: {error['error_type']}",
                    description=error['error_message'],
                    color=discord.Color.red()
                )
                
                # Add error details
                embed.add_field(
                    name="Category",
                    value=error['category'],
                    inline=True
                )
                
                embed.add_field(
                    name="First Seen",
                    value=error['first_seen'].strftime("%Y-%m-%d %H:%M:%S"),
                    inline=True
                )
                
                embed.add_field(
                    name="Last Seen",
                    value=error['last_seen'].strftime("%Y-%m-%d %H:%M:%S"),
                    inline=True
                )
                
                embed.add_field(
                    name="Occurrences",
                    value=str(error['occurrence_count']),
                    inline=True
                )
                
                # Add context if available
                if 'last_context' in error and error['last_context']:
                    context_str = "\n".join([f"**{k}**: {v}" for k, v in error['last_context'].items()])
                    if len(context_str) > 1024:
                        context_str = context_str[:1021] + "..."
                    
                    embed.add_field(
                        name="Context",
                        value=context_str,
                        inline=False
                    )
                
                # Add traceback excerpt
                if 'last_traceback' in error and error['last_traceback']:
                    traceback_lines = error['last_traceback'].split("\n")
                    # Only include last 10 lines
                    if len(traceback_lines) > 10:
                        traceback_excerpt = "\n".join(traceback_lines[-10:])
                    else:
                        traceback_excerpt = error['last_traceback']
                    
                    if len(traceback_excerpt) > 1024:
                        traceback_excerpt = traceback_excerpt[:1021] + "..."
                    
                    embed.add_field(
                        name="Traceback",
                        value=f"```python\n{traceback_excerpt}\n```",
                        inline=False
                    )
                
                # Add fingerprint
                embed.set_footer(text=f"Fingerprint: {error['fingerprint']}")
                
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await interaction.followup.send(f"Error with ID {error_id} not found", ephemeral=True)
                
        elif show_recent:
            # Show recent errors for this guild
            guild_id = str(interaction.guild.id) if interaction.guild else None
            
            if not guild_id:
                await interaction.followup.send("This command must be used in a server", ephemeral=True)
                return
            
            # Create embed for recent errors
            embed = discord.Embed(
                title="Recent Errors",
                description=f"Recent errors for this server",
                color=discord.Color.orange()
            )
            
            # Get recent errors with guild_id in context
            pipeline = [
                {"$match": {"last_context.guild_id": guild_id}},
                {"$sort": {"last_seen": -1}},
                {"$limit": 10}
            ]
            
            error_count = 0
            async for error in db.errors.aggregate(pipeline):
                error_count += 1
                
                # Add error field
                field_name = f"{error['error_type']} ({error['category']})"
                field_value = (
                    f"**Message:** {error['error_message'][:100]}\n"
                    f"**Count:** {error['occurrence_count']}\n"
                    f"**Last seen:** {error['last_seen'].strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"**ID:** `{error['fingerprint']}`"
                )
                
                embed.add_field(
                    name=field_name,
                    value=field_value,
                    inline=False
                )
            
            if error_count == 0:
                embed.description = "No recent errors found for this server"
            
            embed.set_footer(text=f"Use /debug error_id:<id> to view details for a specific error")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        else:
            # Show error statistics
            try:
                # Get error stats
                stats = await ErrorTelemetry.get_error_stats(days=7)
                
                # Create embed
                embed = discord.Embed(
                    title="Error Statistics",
                    description=f"Error statistics for the past 7 days",
                    color=discord.Color.blue()
                )
                
                # Add total count
                embed.add_field(
                    name="Total Errors",
                    value=str(stats.get("total_errors", 0)),
                    inline=True
                )
                
                # Add category breakdown
                categories = stats.get("categories", [])
                if categories:
                    category_text = "\n".join([f"**{c['category']}**: {c['count']}" for c in categories])
                    embed.add_field(
                        name="Categories",
                        value=category_text,
                        inline=True
                    )
                
                # Add most frequent errors
                frequent_errors = stats.get("most_frequent", [])
                if frequent_errors:
                    error_text = ""
                    for i, error in enumerate(frequent_errors[:5], 1):
                        error_text += f"{i}. **{error['error_type']}**: {error['count']} occurrences\n"
                        error_text += f"   Message: {error['message'][:50]}...\n"
                        error_text += f"   ID: `{error['fingerprint']}`\n"
                    
                    embed.add_field(
                        name="Most Frequent Errors",
                        value=error_text,
                        inline=False
                    )
                
                embed.set_footer(text=f"Use /debug error_id:<id> to view details for a specific error")
                
                await interaction.followup.send(embed=embed, ephemeral=True)
                
            except Exception as e:
                logger.error(f"Error getting error statistics: {e}")
                await interaction.followup.send(f"Error getting statistics: {e}", ephemeral=True)
    
    # Error resolution guide command
    @app_commands.command(
        name="error_guide",
        description="Get a detailed guide for resolving specific errors"
    )
    @app_commands.describe(
        error_type="Type of error to get help with"
    )
    @app_commands.choices(error_type=[
        app_commands.Choice(name="SFTP Connection Issues", value="sftp_connection"),
        app_commands.Choice(name="Command Usage Help", value="command_usage"),
        app_commands.Choice(name="Rate Limit Information", value="rate_limit"),
        app_commands.Choice(name="Permission Problems", value="missing_permission"),
        app_commands.Choice(name="General Troubleshooting", value="general")
    ])
    async def error_guide_command(
        self,
        interaction: discord.Interaction,
        error_type: str
    ):
        """Provide an error resolution guide
        
        Args:
            interaction: Discord interaction
            error_type: Type of error to get help with
        """
        await interaction.response.defer()
        
        # Get command information for context if needed
        context = {}
        if error_type == "command_usage" and interaction.command:
            # Try to get command information
            command_name = interaction.command.name
            
            # Build parameter information if available
            if hasattr(interaction.command, "parameters"):
                parameters = []
                for param in interaction.command.parameters:
                    parameters.append({
                        "name": param.name,
                        "description": getattr(param, "description", ""),
                        "required": getattr(param, "required", False)
                    })
                
                context["parameters"] = parameters
            
            # Set command name in context
            context["command"] = command_name
        
        # Create resolution guide
        embed = await create_error_resolution_guide(error_type, context)
        
        await interaction.followup.send(embed=embed)
    
    # Enable/disable telemetry command
    @app_commands.command(
        name="telemetry",
        description="Enable or disable error telemetry [Developer only]"
    )
    @app_commands.describe(
        enable="Whether to enable or disable telemetry"
    )
    @is_bot_developer()
    async def telemetry_command(
        self,
        interaction: discord.Interaction,
        enable: bool
    ):
        """Enable or disable error telemetry
        
        Args:
            interaction: Discord interaction
            enable: Whether to enable or disable telemetry
        """
        # Enable or disable telemetry
        if enable:
            ErrorTelemetry.enable()
            await interaction.response.send_message("Error telemetry enabled", ephemeral=True)
        else:
            ErrorTelemetry.disable()
            await interaction.response.send_message("Error telemetry disabled", ephemeral=True)

async def setup(bot):
    """Add the error handling cog to the bot"""
    await bot.add_cog(ErrorHandlingCog(bot))