"""
Setup commands for configuring servers and channels
"""
import logging
import os
import re
import psutil
import discord
from discord.ext import commands
from utils.discord_patches import app_commands
from typing import Dict, List, Any, Optional
import asyncio
from datetime import datetime

from models.guild import Guild
from models.server import Server
from utils.sftp import SFTPClient
from utils.embed_builder import EmbedBuilder
from utils.helpers import has_admin_permission
from utils.csv_parser import CSVParser
from utils.premium_verification import premium_feature_required  # Use standardized premium verification
from utils.discord_utils import server_id_autocomplete, hybrid_send
from utils.discord_compat import guild_only as discord_compat_guild_only
from utils.interaction_handlers import safely_respond_to_interaction
from config import PREMIUM_TIERS

async def confirm(ctx, message, ephemeral=False):
    """
    Send a confirmation message and wait for user response
    
    Args:
        ctx: Command context or interaction
        message: Message to display
        ephemeral: Whether the message should be ephemeral
        
    Returns:
        bool: True if confirmed, False if cancelled or timed out
    """
    # Create confirm/cancel buttons
    class ConfirmView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=60.0)
            self.value = None
            
        @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
        async def confirm(self, interaction, button):
            if interaction.user != ctx.user:
                await interaction.response.send_message("You cannot use this confirmation dialog.", ephemeral=True)
                return
                
            self.value = True
            self.stop()
            
        @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
        async def cancel(self, interaction, button):
            if interaction.user != ctx.user:
                await interaction.response.send_message("You cannot use this confirmation dialog.", ephemeral=True)
                return
                
            self.value = False
            self.stop()
            
    view = ConfirmView()
    
    # Send the confirmation message
    if hasattr(ctx, 'followup') and hasattr(ctx.followup, 'send'):
        msg = await ctx.followup.send(message, view=view, ephemeral=ephemeral)
    elif hasattr(ctx, 'send'):
        msg = await ctx.send(message, view=view, ephemeral=ephemeral)
    else:
        # Last resort - try to use safely_respond_to_interaction
        await safely_respond_to_interaction(ctx, content=message, view=view, ephemeral=ephemeral)
        msg = None  # We don't have a message reference for this case
        
    # Wait for confirmation
    await view.wait()
    
    # Clean up the message if possible
    if msg is not None and hasattr(msg, 'edit'):
        try:
            await msg.edit(view=None)
        except Exception:
            # Ignore errors during cleanup
            pass
            
    return view.value

logger = logging.getLogger(__name__)

class Setup(commands.Cog):
    """Setup commands for configuring servers and channels"""

    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_group(name="setup", description="Server setup commands")
    # Use our compatibility layer's guild_only instead of commands.guild_only
    @discord_compat_guild_only()
    async def setup(self, ctx):
        """Setup command group"""
        if ctx.invoked_subcommand is None:
            await ctx.send("Please specify a subcommand.")

    @setup.command(name="addserver", description="Add a game server to track PvP stats")
    @app_commands.describe(
        server_name="Friendly name to display for this server",
        host="SFTP host address",
        port="SFTP port",
        username="SFTP username",
        password="SFTP password for authentication",
        log_path="Path to the server logs on the remote system",
        enabled="Whether this server is enabled (default: True)",
        sync_frequency="How often to sync logs (in minutes)"
    )
    @has_admin_permission()
    @discord_compat_guild_only()  # Use our compatibility layer's guild_only
    async def add_server(
        self, ctx,
        server_name: str,
        host: str,
        port: int,
        username: str,
        password: str,
        log_path: str,
        enabled: bool = True,
        sync_frequency: int = 5
    ):
        """Add a game server to track via SFTP"""
        try:
            await ctx.defer(ephemeral=True)
            
            # Validate inputs
            if not server_name or not host or not username or not password or not log_path:
                await ctx.followup.send("All fields are required.", ephemeral=True)
                return
            
            # Sanitize inputs
            server_name = server_name.strip()
            host = host.strip()
            username = username.strip()
            password = password.strip()
            log_path = log_path.strip()
            
            # Normalize server name - make it a valid MongoDB key
            server_id = re.sub(r'[^a-zA-Z0-9_]', '_', server_name.lower())
            
            # Check if a server with this name or ID already exists
            guild = await Guild.get_guild(self.bot.db, ctx.guild.id)
            
            if not guild:
                guild = Guild(id=str(ctx.guild.id), name=ctx.guild.name)
                
            if server_id in guild.servers:
                await ctx.followup.send(f"A server with the name '{server_name}' already exists.", ephemeral=True)
                return
            
            # Test SFTP connection
            sftp_client = SFTPClient(host, port, username, password)
            
            connection_success = await sftp_client.test_connection()
            if not connection_success:
                await ctx.followup.send("Failed to connect to the SFTP server. Please check your credentials.", ephemeral=True)
                return
                
            # Verify log path exists
            path_exists = await sftp_client.path_exists(log_path)
            if not path_exists:
                await ctx.followup.send(f"The log path '{log_path}' does not exist on the remote server.", ephemeral=True)
                return
            
            # Create server document
            server = Server(
                id=server_id,
                name=server_name,
                host=host,
                port=port,
                username=username,
                password=password,
                log_path=log_path,
                enabled=enabled,
                sync_frequency=sync_frequency
            )
            
            # Add server to guild
            guild.servers[server_id] = server.to_dict()
            
            # Save guild
            await guild.save(self.bot.db)
            
            # Create success embed
            embed = await EmbedBuilder.create_success_embed(
                title="Server Added",
                description=f"Successfully added server '{server_name}'."
            )
            
            await ctx.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error adding server: {e}")
            await ctx.followup.send(f"An error occurred: {e}", ephemeral=True)

    @setup.command(name="removeserver", description="Remove a game server from tracking")
    @app_commands.describe(
        server_id="ID of the server to remove"
    )
    @has_admin_permission()
    @discord_compat_guild_only()  # Use our compatibility layer's guild_only
    async def remove_server(self, ctx, server_id: str):
        """Remove a game server from tracking"""
        try:
            await ctx.defer(ephemeral=True)
            
            # Get guild
            guild = await Guild.get_guild(self.bot.db, ctx.guild.id)
            
            if not guild or server_id not in guild.servers:
                await ctx.followup.send(f"Server '{server_id}' not found.", ephemeral=True)
                return
            
            # Get server name for confirmation
            server_name = guild.servers[server_id].get('name', server_id)
            
            # Ask for confirmation
            confirmation = await confirm(
                ctx, 
                f"Are you sure you want to remove the server '{server_name}'? This will delete all associated data and cannot be undone.",
                ephemeral=True
            )
            
            if not confirmation:
                await ctx.followup.send("Server removal cancelled.", ephemeral=True)
                return
            
            # Remove server
            del guild.servers[server_id]
            
            # Save guild
            await guild.save(self.bot.db)
            
            # Create success embed
            embed = await EmbedBuilder.create_success_embed(
                title="Server Removed",
                description=f"Successfully removed server '{server_name}'."
            )
            
            await ctx.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error removing server: {e}")
            await ctx.followup.send(f"An error occurred: {e}", ephemeral=True)

    @setup.command(name="listservers", description="List all configured game servers")
    @discord_compat_guild_only()  # Use our compatibility layer's guild_only
    async def list_servers(self, ctx):
        """List all configured game servers"""
        try:
            await ctx.defer(ephemeral=False)
            
            # Get guild
            guild = await Guild.get_guild(self.bot.db, ctx.guild.id)
            
            if not guild or not guild.servers:
                embed = await EmbedBuilder.create_info_embed(
                    title="No Servers",
                    description="No game servers have been configured for this Discord server."
                )
                await ctx.followup.send(embed=embed)
                return
            
            # Create embed
            embed = discord.Embed(
                title="Configured Game Servers",
                description=f"There are {len(guild.servers)} game servers configured for this Discord server.",
                color=discord.Color.blue()
            )
            
            # Add fields for each server
            for server_id, server in guild.servers.items():
                server_name = server.get('name', server_id)
                host = server.get('host', 'Unknown')
                enabled = "Enabled" if server.get('enabled', False) else "Disabled"
                sync_frequency = server.get('sync_frequency', 0)
                
                embed.add_field(
                    name=server_name,
                    value=f"**ID:** {server_id}\n**Host:** {host}\n**Status:** {enabled}\n**Sync:** Every {sync_frequency} minutes",
                    inline=False
                )
            
            await ctx.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error listing servers: {e}")
            await ctx.followup.send(f"An error occurred: {e}")

async def setup(bot):
    await bot.add_cog(Setup(bot))