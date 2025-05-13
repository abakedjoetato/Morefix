"""
SFTP Commands for Tower of Temptation PvP Statistics Bot

This module provides Discord slash commands for SFTP-related operations:
1. Testing SFTP connections
2. Listing available files and directories
3. Downloading and viewing files
4. Managing server SFTP configuration
5. Diagnostics and troubleshooting

All commands use the new connection pool system for enhanced reliability.
"""
import os
import io
import re
import logging
import asyncio
import traceback
from typing import Dict, List, Optional, Any, Union, Tuple
from datetime import datetime, timedelta

import discord
from discord.ext import commands
from discord import app_commands
from discord.app_commands import Choice

from utils.sftp_connection_pool import SFTPContextManager, initialize_sftp_pool
from utils.sftp_helpers import (
    test_sftp_connection, list_directory, find_files, read_file,
    get_latest_csv_files, search_for_csv_files
)
from utils.sftp_exceptions import SFTPError, format_error_for_user

# Configure module-specific logger
logger = logging.getLogger(__name__)

# Define check functions
def is_guild_admin():
    """Check if command user is an admin in the guild"""
    async def predicate(interaction: discord.Interaction):
        if interaction.guild is None:
            return False
        return interaction.user.guild_permissions.administrator
    return app_commands.check(predicate)

def is_premium_guild():
    """Check if guild has a premium subscription"""
    async def predicate(interaction: discord.Interaction):
        if interaction.guild is None:
            return False
        
        # Get bot instance
        bot = interaction.client
        
        # Check premium status
        try:
            if hasattr(bot, 'db') and callable(bot.db):
                db = bot.db()
                # Look up premium status in guilds collection
                guild = await db.guilds.find_one({'guild_id': str(interaction.guild.id)})
                if guild and 'premium' in guild and guild['premium']:
                    return True
                    
                # Alternative check in premium collection
                premium = await db.premium.find_one({'guild_id': str(interaction.guild.id)})
                if premium and 'active' in premium and premium['active']:
                    return True
                    
        except Exception as e:
            logger.error(f"Error checking premium status: {e}")
            
        # Default is not premium
        return False
    return app_commands.check(predicate)

class SFTPCommands(commands.Cog):
    """Commands for managing and using SFTP connections"""
    
    def __init__(self, bot):
        """Initialize SFTP commands cog
        
        Args:
            bot: Bot instance
        """
        self.bot = bot
        self.default_search_paths = [
            '/',
            '/logs',
            '/Logs',
            '/minecraft/logs',
            '/server/logs',
            '/minecraft',
            '/server'
        ]
        
        # Register commands
        # self._register_commands()
        
        # Start tasks
        self.bot.loop.create_task(self._initialize_sftp_pool())
        
    async def _initialize_sftp_pool(self):
        """Initialize the SFTP connection pool"""
        try:
            await initialize_sftp_pool()
        except Exception as e:
            logger.error(f"Failed to initialize SFTP pool: {e}")
    
    async def get_server_config(self, guild_id: str, server_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get SFTP configurations for a guild
        
        Args:
            guild_id: Discord guild ID
            server_id: Optional specific server ID to get
            
        Returns:
            List of server configurations with SFTP details
        """
        db = self.bot.db()
        server_configs = []
        
        try:
            # Query main servers collection
            query = {'guild_id': str(guild_id)}
            if server_id:
                query['server_id'] = server_id
                
            async for server in db.servers.find(query):
                # Check if SFTP is configured
                if ('hostname' in server or 'sftp_host' in server) and ('username' in server or 'sftp_username' in server):
                    # Add to configs
                    server_configs.append(server)
            
            # Check for additional configurations in game_servers collection
            if hasattr(db, 'game_servers'):
                query = {'guild_id': str(guild_id)}
                if server_id:
                    query['server_id'] = server_id
                    
                async for server in db.game_servers.find(query):
                    # Check if SFTP is configured
                    if ('hostname' in server or 'sftp_host' in server) and ('username' in server or 'sftp_username' in server):
                        # Add to configs
                        server_configs.append(server)
                        
            # Finally check guild settings for embedded SFTP configurations
            guild_doc = await db.guilds.find_one({'guild_id': str(guild_id)})
            if guild_doc and 'servers' in guild_doc:
                for server_id, server in guild_doc['servers'].items():
                    # Check if SFTP is configured
                    if ('hostname' in server or 'sftp_host' in server) and ('username' in server or 'sftp_username' in server):
                        # Add server_id to the config
                        server['server_id'] = server_id
                        server['guild_id'] = str(guild_id)
                        server_configs.append(server)
                        
            return server_configs
            
        except Exception as e:
            logger.error(f"Error getting server configs: {e}")
            return []
    
    async def get_server_choices(self, interaction: discord.Interaction) -> List[Choice[str]]:
        """Get choices for server selection in commands
        
        Args:
            interaction: Discord interaction
            
        Returns:
            List of server choices for autocomplete
        """
        try:
            # Get SFTP server configurations for this guild
            guild_id = str(interaction.guild.id) if interaction.guild else None
            if not guild_id:
                return []
                
            server_configs = await self.get_server_config(guild_id)
            
            # Convert to choices
            choices = []
            for config in server_configs:
                server_id = config.get('server_id', '')
                name = config.get('name', server_id)
                
                # Limit name length to 100 chars for autocomplete
                if len(name) > 90:
                    name = name[:90] + '...'
                
                choices.append(Choice(name=name, value=server_id))
                
            return choices
            
        except Exception as e:
            logger.error(f"Error getting server choices: {e}")
            return []
    
    @app_commands.command(
        name="test_sftp",
        description="Test SFTP connection to a configured server"
    )
    @app_commands.describe(
        server="Server to test connection to"
    )
    @app_commands.autocomplete(server=get_server_choices)
    @is_guild_admin()
    async def test_sftp(self, interaction: discord.Interaction, server: str):
        """Test SFTP connection to a server
        
        Args:
            interaction: Discord interaction
            server: Server ID to test
        """
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Get server configuration
            guild_id = str(interaction.guild.id)
            server_configs = await self.get_server_config(guild_id, server)
            
            if not server_configs:
                await interaction.followup.send(f"Server `{server}` not found or SFTP not configured")
                return
                
            config = server_configs[0]
            
            # Extract SFTP details
            host = config.get('hostname') or config.get('sftp_host')
            port = config.get('port') or config.get('sftp_port', 22)
            username = config.get('username') or config.get('sftp_username')
            password = config.get('password') or config.get('sftp_password')
            
            # Test connection
            success, error_message = await test_sftp_connection(
                guild_id=guild_id,
                host=host,
                port=port,
                username=username,
                password=password
            )
            
            if success:
                embed = discord.Embed(
                    title="SFTP Connection Test",
                    description=f"Successfully connected to SFTP server for `{server}`",
                    color=discord.Color.green()
                )
                
                # Add connection details
                embed.add_field(
                    name="Connection Details",
                    value=f"Host: `{host}`\nPort: `{port}`\nUsername: `{username}`",
                    inline=False
                )
                
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                embed = discord.Embed(
                    title="SFTP Connection Test Failed",
                    description=f"Could not connect to SFTP server for `{server}`",
                    color=discord.Color.red()
                )
                
                # Add error message and connection details
                embed.add_field(
                    name="Error",
                    value=error_message or "Unknown error",
                    inline=False
                )
                
                embed.add_field(
                    name="Connection Details",
                    value=f"Host: `{host}`\nPort: `{port}`\nUsername: `{username}`",
                    inline=False
                )
                
                await interaction.followup.send(embed=embed, ephemeral=True)
                
        except Exception as e:
            logger.error(f"Error testing SFTP connection: {e}")
            traceback.print_exc()
            
            # Send error message
            await interaction.followup.send(
                f"Error testing SFTP connection: {str(e)}",
                ephemeral=True
            )
    
    @app_commands.command(
        name="list_sftp_files",
        description="List files available on SFTP server"
    )
    @app_commands.describe(
        server="Server to list files from",
        path="Directory path to list (default: /)",
        pattern="File pattern to filter by (e.g., *.csv)"
    )
    @app_commands.autocomplete(server=get_server_choices)
    async def list_sftp_files(
        self, 
        interaction: discord.Interaction, 
        server: str, 
        path: Optional[str] = "/",
        pattern: Optional[str] = None
    ):
        """List files on an SFTP server
        
        Args:
            interaction: Discord interaction
            server: Server ID to list files from
            path: Directory path to list
            pattern: Optional file pattern to filter by
        """
        await interaction.response.defer()
        
        try:
            # Get server configuration
            guild_id = str(interaction.guild.id)
            server_configs = await self.get_server_config(guild_id, server)
            
            if not server_configs:
                await interaction.followup.send(f"Server `{server}` not found or SFTP not configured")
                return
                
            config = server_configs[0]
            
            # Extract SFTP details
            host = config.get('hostname') or config.get('sftp_host')
            port = config.get('port') or config.get('sftp_port', 22)
            username = config.get('username') or config.get('sftp_username')
            password = config.get('password') or config.get('sftp_password')
            
            # Normalize path
            if not path:
                path = "/"
                
            # List files
            files = await list_directory(
                guild_id=guild_id,
                host=host,
                port=port,
                username=username,
                password=password,
                path=path,
                pattern=pattern,
                include_dirs=True
            )
            
            if not files:
                await interaction.followup.send(f"No files found in `{path}` on server `{server}`")
                return
                
            # Create embed with file listing
            embed = discord.Embed(
                title=f"SFTP Files on {server}",
                description=f"Directory: `{path}`" + (f"\nFilter: `{pattern}`" if pattern else ""),
                color=discord.Color.blue()
            )
            
            # Group by type
            directories = []
            regular_files = []
            
            for file_info in files:
                if file_info.get('type') == 'directory':
                    directories.append(file_info)
                else:
                    regular_files.append(file_info)
            
            # Sort directories and files by name
            directories.sort(key=lambda x: x.get('name', '').lower())
            regular_files.sort(key=lambda x: x.get('name', '').lower())
            
            # Add directories to embed
            if directories:
                directory_list = "\n".join([f"📁 `{d.get('name')}/`" for d in directories[:10]])
                if len(directories) > 10:
                    directory_list += f"\n... and {len(directories) - 10} more"
                    
                embed.add_field(
                    name=f"Directories ({len(directories)})",
                    value=directory_list,
                    inline=False
                )
            
            # Add files to embed
            if regular_files:
                # Format file information
                file_entries = []
                for f in regular_files[:10]:
                    size = f.get('size', 0)
                    size_str = f"{size} bytes"
                    if size >= 1024:
                        size_str = f"{size / 1024:.1f} KB"
                    if size >= 1024 * 1024:
                        size_str = f"{size / (1024 * 1024):.1f} MB"
                        
                    mtime = f.get('mtime')
                    if mtime:
                        date_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
                        file_entries.append(f"📄 `{f.get('name')}` - {size_str} - {date_str}")
                    else:
                        file_entries.append(f"📄 `{f.get('name')}` - {size_str}")
                
                if len(regular_files) > 10:
                    file_entries.append(f"... and {len(regular_files) - 10} more")
                    
                file_list = "\n".join(file_entries)
                embed.add_field(
                    name=f"Files ({len(regular_files)})",
                    value=file_list,
                    inline=False
                )
            
            # Add footer with timestamp
            embed.set_footer(text=f"Listed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            await interaction.followup.send(embed=embed)
                
        except Exception as e:
            logger.error(f"Error listing SFTP files: {e}")
            traceback.print_exc()
            
            # Send error message
            if isinstance(e, SFTPError):
                await interaction.followup.send(
                    f"Error listing SFTP files: {format_error_for_user(e)}",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    f"Error listing SFTP files: {str(e)}",
                    ephemeral=True
                )
    
    @app_commands.command(
        name="get_latest_logs",
        description="Get latest log files from SFTP server"
    )
    @app_commands.describe(
        server="Server to get logs from",
        hours="Maximum age of logs in hours (default: 24)",
        count="Maximum number of logs to list (default: 5)"
    )
    @app_commands.autocomplete(server=get_server_choices)
    @is_premium_guild()
    async def get_latest_logs(
        self, 
        interaction: discord.Interaction, 
        server: str, 
        hours: Optional[int] = 24,
        count: Optional[int] = 5
    ):
        """Get latest log files from server
        
        Args:
            interaction: Discord interaction
            server: Server ID to get logs from
            hours: Maximum age of logs in hours
            count: Maximum number of logs to list
        """
        await interaction.response.defer()
        
        try:
            # Get server configuration
            guild_id = str(interaction.guild.id)
            server_configs = await self.get_server_config(guild_id, server)
            
            if not server_configs:
                await interaction.followup.send(f"Server `{server}` not found or SFTP not configured")
                return
                
            config = server_configs[0]
            
            # Extract SFTP details
            host = config.get('hostname') or config.get('sftp_host')
            port = config.get('port') or config.get('sftp_port', 22)
            username = config.get('username') or config.get('sftp_username')
            password = config.get('password') or config.get('sftp_password')
            
            # Normalize parameters
            if hours < 1:
                hours = 24
            if count < 1:
                count = 5
            if count > 20:
                count = 20  # Limit maximum to prevent abuse
            
            # Get log paths from config or use defaults
            log_paths = config.get('log_paths', self.default_search_paths)
            if not log_paths:
                log_paths = self.default_search_paths
                
            # Search for logs
            csv_files = await search_for_csv_files(
                guild_id=guild_id,
                host=host,
                port=port,
                username=username,
                password=password,
                search_paths=log_paths,
                max_files=count
            )
            
            if not csv_files:
                # Try a more exhaustive search
                all_paths = []
                for base_path in self.default_search_paths:
                    # Add some common variations
                    all_paths.append(base_path)
                    all_paths.append(f"{base_path}/logs")
                    all_paths.append(f"{base_path}/Logs")
                
                csv_files = await search_for_csv_files(
                    guild_id=guild_id,
                    host=host,
                    port=port,
                    username=username,
                    password=password,
                    search_paths=all_paths,
                    max_files=count
                )
            
            if not csv_files:
                await interaction.followup.send(f"No log files found on server `{server}`")
                return
                
            # Filter by age
            if hours > 0:
                now = datetime.now()
                oldest_time = now - timedelta(hours=hours)
                
                filtered_files = []
                for file_info in csv_files:
                    mtime = file_info.get("mtime")
                    if mtime:
                        file_time = datetime.fromtimestamp(mtime)
                        if file_time >= oldest_time:
                            filtered_files.append(file_info)
                
                csv_files = filtered_files
            
            if not csv_files:
                await interaction.followup.send(f"No log files found in the last {hours} hours on server `{server}`")
                return
                
            # Create embed with file listing
            embed = discord.Embed(
                title=f"Latest Log Files on {server}",
                description=f"Showing up to {count} log files from the last {hours} hours",
                color=discord.Color.blue()
            )
            
            # Add files to embed
            file_entries = []
            for f in csv_files:
                name = f.get('name', '')
                path = f.get('full_path', '')
                size = f.get('size', 0)
                
                size_str = f"{size} bytes"
                if size >= 1024:
                    size_str = f"{size / 1024:.1f} KB"
                if size >= 1024 * 1024:
                    size_str = f"{size / (1024 * 1024):.1f} MB"
                    
                mtime = f.get('mtime')
                if mtime:
                    date_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
                    file_entries.append(f"📄 `{name}` - {size_str} - {date_str}\nPath: `{path}`")
                else:
                    file_entries.append(f"📄 `{name}` - {size_str}\nPath: `{path}`")
            
            # Split into fields if needed (Discord field value limit is 1024 chars)
            remaining_entries = file_entries
            field_num = 1
            
            while remaining_entries:
                current_entries = []
                current_length = 0
                
                # Fill current field
                while remaining_entries and current_length + len(remaining_entries[0]) + 1 < 1024:
                    entry = remaining_entries[0]
                    current_entries.append(entry)
                    current_length += len(entry) + 1  # +1 for newline
                    remaining_entries.pop(0)
                
                # Add field
                embed.add_field(
                    name=f"Files {field_num}-{field_num + len(current_entries) - 1}",
                    value="\n".join(current_entries),
                    inline=False
                )
                
                field_num += len(current_entries)
            
            # Add footer with timestamp
            embed.set_footer(text=f"Listed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            await interaction.followup.send(embed=embed)
                
        except Exception as e:
            logger.error(f"Error getting latest logs: {e}")
            traceback.print_exc()
            
            # Send error message
            if isinstance(e, SFTPError):
                await interaction.followup.send(
                    f"Error getting latest logs: {format_error_for_user(e)}",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    f"Error getting latest logs: {str(e)}",
                    ephemeral=True
                )
    
    @app_commands.command(
        name="download_log",
        description="Download a specific log file from SFTP server"
    )
    @app_commands.describe(
        server="Server to download from",
        path="Path to the log file"
    )
    @app_commands.autocomplete(server=get_server_choices)
    @is_premium_guild()
    async def download_log(
        self, 
        interaction: discord.Interaction, 
        server: str, 
        path: str
    ):
        """Download a specific log file
        
        Args:
            interaction: Discord interaction
            server: Server ID to download from
            path: Path to log file
        """
        await interaction.response.defer()
        
        try:
            # Get server configuration
            guild_id = str(interaction.guild.id)
            server_configs = await self.get_server_config(guild_id, server)
            
            if not server_configs:
                await interaction.followup.send(f"Server `{server}` not found or SFTP not configured")
                return
                
            config = server_configs[0]
            
            # Extract SFTP details
            host = config.get('hostname') or config.get('sftp_host')
            port = config.get('port') or config.get('sftp_port', 22)
            username = config.get('username') or config.get('sftp_username')
            password = config.get('password') or config.get('sftp_password')
            
            # Ensure path starts with a slash
            if not path.startswith('/'):
                path = '/' + path
            
            # Read file
            file_data = await read_file(
                guild_id=guild_id,
                host=host,
                port=port,
                username=username,
                password=password,
                path=path
            )
            
            # Get filename from path
            filename = os.path.basename(path)
            
            # Send file to Discord
            discord_file = discord.File(io.BytesIO(file_data), filename=filename)
            
            # Create embed with file info
            embed = discord.Embed(
                title=f"Downloaded File: {filename}",
                description=f"From server: `{server}`\nPath: `{path}`",
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name="File Size",
                value=f"{len(file_data)} bytes",
                inline=True
            )
            
            embed.add_field(
                name="Download Time",
                value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                inline=True
            )
            
            await interaction.followup.send(embed=embed, file=discord_file)
                
        except Exception as e:
            logger.error(f"Error downloading log file: {e}")
            traceback.print_exc()
            
            # Send error message
            if isinstance(e, SFTPError):
                await interaction.followup.send(
                    f"Error downloading log file: {format_error_for_user(e)}",
                    ephemeral=True
                )
            elif isinstance(e, ValueError) and "too large" in str(e):
                await interaction.followup.send(
                    f"Error: {str(e)}. Discord has a 25MB file size limit.",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    f"Error downloading log file: {str(e)}",
                    ephemeral=True
                )

async def setup(bot):
    """Add SFTP commands cog to bot"""
    await bot.add_cog(SFTPCommands(bot))