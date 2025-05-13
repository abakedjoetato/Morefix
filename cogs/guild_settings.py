"""
Guild Settings Cog

This module implements guild settings management with the new command handler framework
and safe MongoDB operations.
"""

import logging
import datetime
import discord
from utils.discord_patches import app_commands
from discord.ext import commands
from typing import Dict, List, Optional, Union, Literal, Any

from utils.command_handlers import command_handler, db_operation
from utils.safe_mongodb import SafeMongoDBResult, SafeDocument
from utils.discord_utils import get_guild_document, server_id_autocomplete
from utils.interaction_handlers import safely_respond_to_interaction, defer_interaction

logger = logging.getLogger(__name__)

class GuildSettings(commands.Cog):
    """
    Guild settings management for the Tower of Temptation PvP Statistics Bot.
    
    Provides commands for configuring guild-specific settings for the bot,
    including log channels, auto-role assignments, and server IDs.
    """
    
    def __init__(self, bot):
        self.bot = bot
        
    @commands.slash_command(
        name="setup",
        description="Set up the bot for this server"
    )
    @command_handler(admin_only=True)
    async def setup_command(
        self, 
        interaction: discord.Interaction
    ):
        """
        Setup the bot for this server (Admin only).
        
        Args:
            interaction: Discord interaction
        """
        # Get the guild ID safely
        guild_id = None
        if hasattr(interaction, 'guild_id') and interaction.guild_id is not None:
            guild_id = interaction.guild_id
        
        if guild_id is None:
            await interaction.response.send_message(
                "This command must be used in a server.",
                ephemeral=True
            )
            return
            
        # Provide user feedback while setup runs
        await interaction.response.defer(thinking=True)
        
        # Perform initial setup
        setup_result = await self.initialize_guild(guild_id)
        
        # Handle database errors
        if not setup_result.success:
            error = setup_result.error()
            error_msg = str(error) if error else "Unknown error"
            logger.error(f"Error initializing guild: {error_msg}")
            await interaction.followup.send(
                f"Failed to set up server: {error_msg}",
                ephemeral=True
            )
            return
        
        # Success message
        await interaction.followup.send(
            "Server setup complete! You can now use the bot's commands."
        )
    
    @commands.slash_command(
        name="settings",
        description="View or modify server settings"
    )
    @app_commands.describe(
        setting="Setting to modify",
        value="New value for the setting"
    )
    @app_commands.choices(setting=[
        utils.discord_patches.app_commands.Choice(name="log_channel", value="log_channel"),
        utils.discord_patches.app_commands.Choice(name="killfeed_channel", value="killfeed_channel"),
        utils.discord_patches.app_commands.Choice(name="announcements_channel", value="announcements_channel"),
        utils.discord_patches.app_commands.Choice(name="prefix", value="prefix"),
        utils.discord_patches.app_commands.Choice(name="default_server", value="default_server")
    ])
    @command_handler(admin_only=True)
    async def settings_command(
        self, 
        interaction: discord.Interaction,
        setting: Optional[str] = None,
        value: Optional[str] = None
    ):
        """
        View or modify server settings (Admin only).
        
        Args:
            interaction: Discord interaction
            setting: Setting to modify (optional)
            value: New value for the setting (optional)
        """
        # Get the guild ID safely
        guild_id = None
        if hasattr(interaction, 'guild_id') and interaction.guild_id is not None:
            guild_id = interaction.guild_id
        
        if guild_id is None:
            await interaction.response.send_message(
                "This command must be used in a server.",
                ephemeral=True
            )
            return
        
        # Get current settings
        settings_result = await self.get_guild_settings(guild_id)
        
        # Handle database errors
        if not settings_result.success:
            error = settings_result.error()
            error_msg = str(error) if error else "Unknown error"
            logger.error(f"Error getting guild settings: {error_msg}")
            await interaction.response.send_message(
                f"Failed to get server settings: {error_msg}",
                ephemeral=True
            )
            return
        
        settings = settings_result.result
        
        # If no setting specified, show all settings
        if setting is None:
            # Create embed with settings information
            embed = discord.Embed(
                title="Server Settings",
                description="Current bot configuration for this server",
                color=discord.Color.blue()
            )
            
            # Add settings fields
            log_channel_id = settings.get("log_channel")
            log_channel_name = f"<#{log_channel_id}>" if log_channel_id else "Not set"
            embed.add_field(
                name="Log Channel",
                value=log_channel_name,
                inline=True
            )
            
            killfeed_channel_id = settings.get("killfeed_channel")
            killfeed_channel_name = f"<#{killfeed_channel_id}>" if killfeed_channel_id else "Not set"
            embed.add_field(
                name="Killfeed Channel",
                value=killfeed_channel_name,
                inline=True
            )
            
            announcements_channel_id = settings.get("announcements_channel")
            announcements_channel_name = f"<#{announcements_channel_id}>" if announcements_channel_id else "Not set"
            embed.add_field(
                name="Announcements Channel",
                value=announcements_channel_name,
                inline=True
            )
            
            prefix = settings.get("prefix", "!")
            embed.add_field(
                name="Command Prefix",
                value=prefix,
                inline=True
            )
            
            default_server = settings.get("default_server", "None")
            embed.add_field(
                name="Default Server",
                value=default_server,
                inline=True
            )
            
            servers = settings.get("servers", [])
            servers_text = "\n".join([f"• {server}" for server in servers]) if servers else "No servers configured"
            embed.add_field(
                name="Configured Servers",
                value=servers_text,
                inline=False
            )
            
            embed.set_footer(text="Use /settings [setting] [value] to modify a setting")
            
            # Send the embed
            await interaction.response.send_message(embed=embed)
            return
        
        # If setting is specified but no value, show current value
        if value is None:
            current_value = settings.get(setting, "Not set")
            
            # Special handling for channel IDs
            if setting.endswith("_channel") and current_value and str(current_value).isdigit():
                current_value = f"<#{current_value}> (ID: {current_value})"
                
            await interaction.response.send_message(
                f"Current value of `{setting}`: {current_value}\n\nUse `/settings {setting} [new value]` to change it."
            )
            return
        
        # If setting and value are specified, update the setting
        update_result = await self.update_guild_setting(guild_id, setting, value)
        
        # Handle database errors
        if not update_result.success:
            error = update_result.error()
            error_msg = str(error) if error else "Unknown error"
            logger.error(f"Error updating guild setting: {error_msg}")
            await interaction.response.send_message(
                f"Failed to update server setting: {error_msg}",
                ephemeral=True
            )
            return
        
        # Success message
        await interaction.response.send_message(
            f"Setting `{setting}` updated to `{value}`."
        )
    
    @commands.slash_command(
        name="add_server",
        description="Add a game server to track (Admin only)"
    )
    @app_commands.describe(
        server_id="ID of the game server to add",
        server_name="Name of the game server"
    )
    @command_handler(admin_only=True)
    async def add_server_command(
        self, 
        interaction: discord.Interaction,
        server_id: str,
        server_name: str
    ):
        """
        Add a game server to track (Admin only).
        
        Args:
            interaction: Discord interaction
            server_id: ID of the game server to add
            server_name: Name of the game server
        """
        # Get the guild ID safely
        guild_id = None
        if hasattr(interaction, 'guild_id') and interaction.guild_id is not None:
            guild_id = interaction.guild_id
        
        if guild_id is None:
            await interaction.response.send_message(
                "This command must be used in a server.",
                ephemeral=True
            )
            return
        
        # Add the server
        add_result = await self.add_game_server(guild_id, server_id, server_name)
        
        # Handle database errors
        if not add_result.success:
            error = add_result.error()
            error_msg = str(error) if error else "Unknown error"
            logger.error(f"Error adding game server: {error_msg}")
            await interaction.response.send_message(
                f"Failed to add game server: {error_msg}",
                ephemeral=True
            )
            return
        
        # Set as default if no default exists
        settings_result = await self.get_guild_settings(guild_id)
        if settings_result.success:
            settings = settings_result.result
            if not settings.get("default_server"):
                await self.update_guild_setting(guild_id, "default_server", server_id)
        
        # Success message
        await interaction.response.send_message(
            f"Game server `{server_name}` (ID: {server_id}) added successfully."
        )
    
    @commands.slash_command(
        name="remove_server",
        description="Remove a game server (Admin only)"
    )
    @app_commands.describe(
        server_id="ID of the game server to remove"
    )
    @app_commands.autocomplete(server_id=server_id_autocomplete)
    @command_handler(admin_only=True)
    async def remove_server_command(
        self, 
        interaction: discord.Interaction,
        server_id: str
    ):
        """
        Remove a game server (Admin only).
        
        Args:
            interaction: Discord interaction
            server_id: ID of the game server to remove
        """
        # Get the guild ID safely
        guild_id = None
        if hasattr(interaction, 'guild_id') and interaction.guild_id is not None:
            guild_id = interaction.guild_id
        
        if guild_id is None:
            await interaction.response.send_message(
                "This command must be used in a server.",
                ephemeral=True
            )
            return
        
        # Remove the server
        remove_result = await self.remove_game_server(guild_id, server_id)
        
        # Handle database errors
        if not remove_result.success:
            error = remove_result.error()
            error_msg = str(error) if error else "Unknown error"
            logger.error(f"Error removing game server: {error_msg}")
            await interaction.response.send_message(
                f"Failed to remove game server: {error_msg}",
                ephemeral=True
            )
            return
        
        # Check if this was the default server
        settings_result = await self.get_guild_settings(guild_id)
        if settings_result.success:
            settings = settings_result.result
            if settings.get("default_server") == server_id:
                # Clear default server
                await self.update_guild_setting(guild_id, "default_server", None)
                
                # Set a new default if other servers exist
                servers = settings.get("server_info", {})
                if servers:
                    new_default = next(iter(servers.keys()), None)
                    if new_default:
                        await self.update_guild_setting(guild_id, "default_server", new_default)
        
        # Success message
        await interaction.response.send_message(
            f"Game server with ID `{server_id}` removed successfully."
        )
    
    @db_operation(collection_name="guilds", operation="update")
    async def initialize_guild(
        self,
        guild_id: Union[str, int]
    ) -> SafeMongoDBResult[Dict]:
        """
        Initialize a guild in the database with safe operations.
        
        Args:
            guild_id: The guild ID
            
        Returns:
            SafeMongoDBResult containing the update result or error
        """
        try:
            # Convert guild_id to string for MongoDB
            guild_id_str = str(guild_id)
            
            # Get the database connection
            if not hasattr(self.bot, 'db') or self.bot.db is None:
                return SafeMongoDBResult.create_error("Database connection not available")
            
            # Create initial guild document
            init_data = {
                "$set": {
                    "guild_id": guild_id_str,
                    "premium_tier": 0,
                    "prefix": "!",
                    "features_enabled": [],
                    "servers": [],
                    "server_info": {},
                    "updated_at": datetime.datetime.utcnow().isoformat(),
                    "created_at": datetime.datetime.utcnow().isoformat()
                },
                "$setOnInsert": {
                    "stats_start_date": datetime.datetime.utcnow().isoformat()
                }
            }
            
            # Use upsert to create the document if it doesn't exist
            result = await self.bot.db.guilds.update_one(
                {"guild_id": guild_id_str},
                init_data,
                upsert=True
            )
            
            # Return success
            return SafeMongoDBResult.ok({
                "acknowledged": result.acknowledged,
                "modified_count": result.modified_count,
                "upserted_id": result.upserted_id
            })
            
        except Exception as e:
            logger.error(f"Error initializing guild: {e}")
            return SafeMongoDBResult.create_error(e)
    
    @db_operation(collection_name="guilds", operation="query")
    async def get_guild_settings(
        self,
        guild_id: Union[str, int]
    ) -> SafeMongoDBResult[SafeDocument]:
        """
        Get guild settings with safe database operations.
        
        Args:
            guild_id: The guild ID
            
        Returns:
            SafeMongoDBResult containing the guild document or error
        """
        try:
            # Convert guild_id to string for MongoDB
            guild_id_str = str(guild_id)
            
            # Get the database connection
            if not hasattr(self.bot, 'db') or self.bot.db is None:
                return SafeMongoDBResult.create_error("Database connection not available")
            
            # Get guild document
            guild_doc = await self.bot.db.guilds.find_one({"guild_id": guild_id_str})
            
            # If no document found, initialize the guild
            if guild_doc is None:
                init_result = await self.initialize_guild(guild_id)
                if not init_result.success:
                    return SafeMongoDBResult.create_error("Failed to initialize guild settings")
                
                # Fetch again after initialization
                guild_doc = await self.bot.db.guilds.find_one({"guild_id": guild_id_str})
                if guild_doc is None:
                    return SafeMongoDBResult.create_error("Guild settings not found after initialization")
            
            # Return document
            return SafeMongoDBResult.ok(SafeDocument(guild_doc))
            
        except Exception as e:
            logger.error(f"Error getting guild settings: {e}")
            return SafeMongoDBResult.create_error(e)
    
    @db_operation(collection_name="guilds", operation="update")
    async def update_guild_setting(
        self,
        guild_id: Union[str, int],
        setting: str,
        value: Optional[Any]
    ) -> SafeMongoDBResult[Dict]:
        """
        Update a guild setting with safe database operations.
        
        Args:
            guild_id: The guild ID
            setting: The setting name
            value: The new value (None to remove the setting)
            
        Returns:
            SafeMongoDBResult containing the update result or error
        """
        try:
            # Convert guild_id to string for MongoDB
            guild_id_str = str(guild_id)
            
            # Get the database connection
            if not hasattr(self.bot, 'db') or self.bot.db is None:
                return SafeMongoDBResult.create_error("Database connection not available")
            
            # Prepare update operation
            if value is None:
                # Unset the field
                update_data = {
                    "$unset": {setting: ""},
                    "$set": {"updated_at": datetime.datetime.utcnow().isoformat()}
                }
            else:
                # Set the field
                update_data = {
                    "$set": {
                        setting: value,
                        "updated_at": datetime.datetime.utcnow().isoformat()
                    }
                }
            
            # Update guild document
            result = await self.bot.db.guilds.update_one(
                {"guild_id": guild_id_str},
                update_data,
                upsert=True
            )
            
            # Return success
            return SafeMongoDBResult.ok({
                "acknowledged": result.acknowledged,
                "modified_count": result.modified_count,
                "upserted_id": result.upserted_id
            })
            
        except Exception as e:
            logger.error(f"Error updating guild setting: {e}")
            return SafeMongoDBResult.create_error(e)
    
    @db_operation(collection_name="guilds", operation="update")
    async def add_game_server(
        self,
        guild_id: Union[str, int],
        server_id: str,
        server_name: str
    ) -> SafeMongoDBResult[Dict]:
        """
        Add a game server to a guild with safe database operations.
        
        Args:
            guild_id: The guild ID
            server_id: The game server ID
            server_name: The game server name
            
        Returns:
            SafeMongoDBResult containing the update result or error
        """
        try:
            # Convert guild_id to string for MongoDB
            guild_id_str = str(guild_id)
            
            # Get the database connection
            if not hasattr(self.bot, 'db') or self.bot.db is None:
                return SafeMongoDBResult.create_error("Database connection not available")
            
            # Update guild document
            update_data = {
                "$addToSet": {"servers": server_id},
                "$set": {
                    f"server_info.{server_id}": {
                        "name": server_name,
                        "added_at": datetime.datetime.utcnow().isoformat()
                    },
                    "updated_at": datetime.datetime.utcnow().isoformat()
                }
            }
            
            # Use upsert to create the document if it doesn't exist
            result = await self.bot.db.guilds.update_one(
                {"guild_id": guild_id_str},
                update_data,
                upsert=True
            )
            
            # Return success
            return SafeMongoDBResult.ok({
                "acknowledged": result.acknowledged,
                "modified_count": result.modified_count,
                "upserted_id": result.upserted_id
            })
            
        except Exception as e:
            logger.error(f"Error adding game server: {e}")
            return SafeMongoDBResult.create_error(e)
    
    @db_operation(collection_name="guilds", operation="update")
    async def remove_game_server(
        self,
        guild_id: Union[str, int],
        server_id: str
    ) -> SafeMongoDBResult[Dict]:
        """
        Remove a game server from a guild with safe database operations.
        
        Args:
            guild_id: The guild ID
            server_id: The game server ID
            
        Returns:
            SafeMongoDBResult containing the update result or error
        """
        try:
            # Convert guild_id to string for MongoDB
            guild_id_str = str(guild_id)
            
            # Get the database connection
            if not hasattr(self.bot, 'db') or self.bot.db is None:
                return SafeMongoDBResult.create_error("Database connection not available")
            
            # Update guild document
            update_data = {
                "$pull": {"servers": server_id},
                "$unset": {f"server_info.{server_id}": ""},
                "$set": {"updated_at": datetime.datetime.utcnow().isoformat()}
            }
            
            # Use upsert to create the document if it doesn't exist
            result = await self.bot.db.guilds.update_one(
                {"guild_id": guild_id_str},
                update_data
            )
            
            # Return success
            return SafeMongoDBResult.ok({
                "acknowledged": result.acknowledged,
                "modified_count": result.modified_count
            })
            
        except Exception as e:
            logger.error(f"Error removing game server: {e}")
            return SafeMongoDBResult.create_error(e)

async def setup(bot):
    await bot.add_cog(GuildSettings(bot))