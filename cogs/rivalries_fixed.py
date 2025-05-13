"""
Rivalries cog for Tower of Temptation PvP Statistics Discord Bot.

This cog provides commands for tracking and managing player rivalries, including:
1. Viewing individual player rivalries
2. Displaying top rivalries on a server
3. Showing closest and most intense rivalries
4. Managing rivalries and viewing recent activity
"""
import asyncio
import logging
import traceback
from datetime import datetime, timedelta
from typing import Union, Dict, List, Optional, Any, Union, Literal

import discord
from discord.ext import commands
from utils.discord_patches import app_commands

from models.rivalry import Rivalry
from models.player_link import PlayerLink
from models.guild import Guild
from models.server import Server
from models.player import Player
from utils.embed_builder import EmbedBuilder
from utils.helpers import paginate_embeds, has_admin_permission, has_mod_permission, confirm
from utils.premium_verification import premium_feature_required  # Use standardized premium verification
from utils.async_utils import BackgroundTask
from utils.discord_utils import server_id_autocomplete  # Import standardized autocomplete function
from utils.command_tree import create_command_tree

logger = logging.getLogger(__name__)

class RivalriesCog(commands.Cog):
    """Commands for managing rivalries in Tower of Temptation"""

    
    async def verify_premium(self, guild_id: Union[str, int], feature_name: str = None) -> bool:
        """
        Verify premium access for a feature
        
        Args:
            guild_id: Discord guild ID
            feature_name: The feature name to check
            
        Returns:
            bool: Whether access is granted
        """
        # Default feature name to cog name if not provided
        if feature_name is None:
            feature_name = self.__class__.__name__.lower()
            
        # Standardize guild_id to string
        guild_id_str = str(guild_id)
        
        try:
            # Import premium utils
            from utils import premium_utils
            
            # Use standardized premium check
            has_access = await premium_utils.verify_premium_for_feature(
                self.bot.db, guild_id_str, feature_name
            )
            
            # Log the result
            logger.info(f"Premium verification for {feature_name}: access={has_access}")
            return has_access
            
        except Exception as e:
            logger.error(f"Error verifying premium: {e}")
            traceback.print_exc()
            # Default to allowing access if there's an error
            return True

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        
        # Use our compatibility wrapper for the context menu
        try:
            # Create a context menu command using our compatibility layer
            self.ctx_menu = app_commands.ContextMenu(
                name="View Rivalries",
                callback=self.context_view_rivalries,
            )
            
            # Get the command tree for the bot to add the context menu
            command_tree = create_command_tree(bot)
            asyncio.create_task(command_tree.add_command(self.ctx_menu))
            logger.info("Successfully registered the View Rivalries context menu")
        except Exception as e:
            logger.error(f"Failed to register rivalries context menu: {e}")
            logger.error(traceback.format_exc())

    async def get_player_for_user(self, interaction: discord.Interaction, server_id: Optional[str] = None) -> Optional[str]:
        """Get the player ID for a Discord user
        
        Args:
            interaction: Discord interaction
            server_id: Optional server ID
            
        Returns:
            str: Player ID if found, None otherwise
        """
        # Get user Discord ID
        discord_id = str(interaction.user.id)
        
        # Get player link
        player_link = await PlayerLink.get_by_discord_id(self.bot.db, discord_id)
        if not player_link:
            # No player link, inform user
            embed = await EmbedBuilder.create_warning_embed(
                title="No Linked Player",
                description="You don't have any linked players. Use `/link player` to link your Discord account to an in-game player."
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return None

        # Check if user has a player on this server
        player_id = player_link.get_player_id_for_server(server_id)
        if player_id is None or player_id == "":
            # No player on this server, inform user
            embed = await EmbedBuilder.create_warning_embed(
                title="No Player on Server",
                description=f"You don't have a linked player on the selected server. Use `/link player` to link your Discord account to an in-game player."
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return None

        return player_id

    @premium_feature_required(feature_name="rivalries", min_tier=3)  # Rivalries require premium tier 3+
    async def context_view_rivalries(self, interaction: discord.Interaction, member: discord.Member) -> None:
        """Context menu command to view a user's rivalries

        Args:
            interaction: Discord interaction
            member: Discord member
        """
        await interaction.response.defer(ephemeral=True)
        
        # Check premium tier for guild
        guild = await Guild.get_guild(self.bot.db, interaction.guild_id)
        if guild is None or not guild.check_feature_access("rivalries"):
            embed = await EmbedBuilder.create_error_embed(
                "Premium Feature",
                "Rivalries are a premium feature (Tier 3+). Please upgrade to access this feature."
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        # Initialize server_id to None
        server_id = None
        
        # If guild has only one server, use that server
        if guild.servers and len(guild.servers) == 1:
            server_id = list(guild.servers.keys())[0]
        
        # Get member Discord ID
        discord_id = str(member.id)
        
        # Get player link
        player_link = await PlayerLink.get_by_discord_id(self.bot.db, discord_id)
        if not player_link:
            # No player link, inform user
            embed = await EmbedBuilder.create_warning_embed(
                title="No Linked Player",
                description=f"{member.display_name} doesn't have any linked players."
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
            
        # Get all player IDs for this user
        if server_id:
            # If we have a server ID, use that
            player_id = player_link.get_player_id_for_server(server_id)
            if not player_id:
                # No player on this server
                embed = await EmbedBuilder.create_warning_embed(
                    title="No Player on Server",
                    description=f"{member.display_name} doesn't have a linked player on the selected server."
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
                
            # Get rivalries
            rivalries = await Rivalry.get_by_player(self.bot.db, player_id, server_id)
            
        else:
            # No server ID specified, get all rivalries
            rivalries = []
            for srv_id, player_id in player_link.server_players.items():
                player_rivalries = await Rivalry.get_by_player(self.bot.db, player_id, srv_id)
                rivalries.extend(player_rivalries)
        
        if not rivalries:
            # No rivalries
            embed = await EmbedBuilder.create_info_embed(
                title="No Rivalries",
                description=f"{member.display_name} doesn't have any active rivalries."
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
            
        # Create rivalries embed
        user_avatars = {}  # Cache user avatars
        
        # Create rivalries embed
        embed = discord.Embed(
            title=f"{member.display_name}'s Rivalries",
            description=f"Showing {len(rivalries)} active rivalries.",
            color=discord.Color.blue()
        )
        
        # Add member avatar
        embed.set_thumbnail(url=member.display_avatar.url)
        
        # Add rivalries as fields
        for rivalry in rivalries[:10]:  # Limit to 10 rivalries
            # Get rival player
            rival_player_id = rivalry.player1_id if rivalry.player2_id == player_id else rivalry.player2_id
            rival_player = await Player.get_by_id(self.bot.db, rival_player_id, rivalry.server_id)
            
            # Get rival Discord user if linked
            rival_discord_id = None
            rival_user = None
            rival_player_link = await PlayerLink.get_by_player_id(self.bot.db, rival_player_id, rivalry.server_id)
            
            if rival_player_link:
                rival_discord_id = rival_player_link.discord_id
                if rival_discord_id and rival_discord_id not in user_avatars:
                    try:
                        rival_user = await self.bot.fetch_user(int(rival_discord_id))
                        user_avatars[rival_discord_id] = rival_user.display_avatar.url
                    except:
                        pass
            
            # Create a field for this rivalry
            if rivalry.player1_id == player_id:
                player_kills = rivalry.player1_kills
                player_deaths = rivalry.player1_deaths
            else:
                player_kills = rivalry.player2_kills
                player_deaths = rivalry.player2_deaths
                
            # Calculate rival kills and deaths
            rival_kills = rivalry.player2_kills if rivalry.player1_id == player_id else rivalry.player1_kills
            rival_deaths = rivalry.player2_deaths if rivalry.player1_id == player_id else rivalry.player1_deaths
            
            # Calculate KD ratio
            kd_ratio = player_kills / max(1, rival_deaths)
            rival_kd_ratio = rival_kills / max(1, player_deaths)
            
            # Format field value
            field_value = f"**Server:** {rivalry.server_id}\n"
            field_value += f"**Your Stats:** {player_kills} kills, {player_deaths} deaths (K/D: {kd_ratio:.2f})\n"
            field_value += f"**Rival Stats:** {rival_kills} kills, {rival_deaths} deaths (K/D: {rival_kd_ratio:.2f})\n"
            
            # Add last engagement time if available
            if rivalry.last_engagement:
                field_value += f"**Last Engagement:** <t:{int(rivalry.last_engagement.timestamp())}:R>\n"
                
            # Add Discord link if available
            if rival_discord_id:
                field_value += f"**Discord:** <@{rival_discord_id}>\n"
                
            # Add field
            rival_name = rival_player.name if rival_player else rival_player_id
            embed.add_field(
                name=f"Rivalry with {rival_name}",
                value=field_value,
                inline=False
            )
        
        await interaction.followup.send(embed=embed, ephemeral=True)

    @commands.hybrid_group(name="rivalries", description="Track and manage player rivalries")
    @premium_feature_required(feature_name="rivalries", min_tier=3)  # Rivalries require premium tier 3+
    async def rivalries(self, ctx):
        """Command group for managing rivalries"""
        if ctx.invoked_subcommand is None:
            await ctx.send("Please specify a subcommand.")

    @rivalries.command(name="view", description="View your rivalries")
    @app_commands.describe(
        server_id="Server ID to get rivalries from (optional)"
    )
    @app_commands.autocomplete(server_id=server_id_autocomplete)
    async def view_rivalries(
        self, 
        ctx, 
        server_id: Optional[str] = None
    ):
        """View your rivalries"""
        await ctx.defer(ephemeral=True)
        
        # Check premium tier for guild
        guild = await Guild.get_guild(self.bot.db, ctx.guild.id)
        if guild is None or not guild.check_feature_access("rivalries"):
            embed = await EmbedBuilder.create_error_embed(
                "Premium Feature",
                "Rivalries are a premium feature (Tier 3+). Please upgrade to access this feature."
            )
            await ctx.followup.send(embed=embed, ephemeral=True)
            return
        
        # Get player ID for user
        discord_id = str(ctx.author.id)
        player_link = await PlayerLink.get_by_discord_id(self.bot.db, discord_id)
        
        if not player_link:
            # No player link, inform user
            embed = await EmbedBuilder.create_warning_embed(
                title="No Linked Player",
                description="You don't have any linked players. Use `/link player` to link your Discord account to an in-game player."
            )
            await ctx.followup.send(embed=embed, ephemeral=True)
            return
        
        # If server_id is not specified and guild has only one server, use that server
        if not server_id and guild.servers and len(guild.servers) == 1:
            server_id = list(guild.servers.keys())[0]
        
        # Get rivalries
        rivalries = []
        
        if server_id:
            # Get player ID for this server
            player_id = player_link.get_player_id_for_server(server_id)
            
            if not player_id:
                # No player on this server
                embed = await EmbedBuilder.create_warning_embed(
                    title="No Player on Server",
                    description=f"You don't have a linked player on the selected server. Use `/link player` to link your Discord account to an in-game player."
                )
                await ctx.followup.send(embed=embed, ephemeral=True)
                return
                
            # Get rivalries for this player and server
            rivalries = await Rivalry.get_by_player(self.bot.db, player_id, server_id)
        else:
            # Get all rivalries for all servers
            for srv_id, player_id in player_link.server_players.items():
                player_rivalries = await Rivalry.get_by_player(self.bot.db, player_id, srv_id)
                rivalries.extend(player_rivalries)
        
        if not rivalries:
            # No rivalries
            embed = await EmbedBuilder.create_info_embed(
                title="No Rivalries",
                description="You don't have any active rivalries."
            )
            await ctx.followup.send(embed=embed, ephemeral=True)
            return
        
        # Create rivalries embed
        user_avatars = {}  # Cache user avatars
        
        # Create rivalries embed
        embed = discord.Embed(
            title="Your Rivalries",
            description=f"Showing {len(rivalries)} active rivalries.",
            color=discord.Color.blue()
        )
        
        # Add user avatar
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        
        # Add rivalries as fields
        for rivalry in rivalries[:10]:  # Limit to 10 rivalries
            # Determine which player is the user
            if server_id:
                player_id = player_link.get_player_id_for_server(server_id)
            else:
                player_id = player_link.get_player_id_for_server(rivalry.server_id)
                
            # Get rival player
            rival_player_id = rivalry.player1_id if rivalry.player2_id == player_id else rivalry.player2_id
            rival_player = await Player.get_by_id(self.bot.db, rival_player_id, rivalry.server_id)
            
            # Get rival Discord user if linked
            rival_discord_id = None
            rival_user = None
            rival_player_link = await PlayerLink.get_by_player_id(self.bot.db, rival_player_id, rivalry.server_id)
            
            if rival_player_link:
                rival_discord_id = rival_player_link.discord_id
                if rival_discord_id and rival_discord_id not in user_avatars:
                    try:
                        rival_user = await self.bot.fetch_user(int(rival_discord_id))
                        user_avatars[rival_discord_id] = rival_user.display_avatar.url
                    except:
                        pass
            
            # Create a field for this rivalry
            if rivalry.player1_id == player_id:
                player_kills = rivalry.player1_kills
                player_deaths = rivalry.player1_deaths
            else:
                player_kills = rivalry.player2_kills
                player_deaths = rivalry.player2_deaths
                
            # Calculate rival kills and deaths
            rival_kills = rivalry.player2_kills if rivalry.player1_id == player_id else rivalry.player1_kills
            rival_deaths = rivalry.player2_deaths if rivalry.player1_id == player_id else rivalry.player1_deaths
            
            # Calculate KD ratio
            kd_ratio = player_kills / max(1, rival_deaths)
            rival_kd_ratio = rival_kills / max(1, player_deaths)
            
            # Format field value
            field_value = f"**Server:** {rivalry.server_id}\n"
            field_value += f"**Your Stats:** {player_kills} kills, {player_deaths} deaths (K/D: {kd_ratio:.2f})\n"
            field_value += f"**Rival Stats:** {rival_kills} kills, {rival_deaths} deaths (K/D: {rival_kd_ratio:.2f})\n"
            
            # Add last engagement time if available
            if rivalry.last_engagement:
                field_value += f"**Last Engagement:** <t:{int(rivalry.last_engagement.timestamp())}:R>\n"
                
            # Add Discord link if available
            if rival_discord_id:
                field_value += f"**Discord:** <@{rival_discord_id}>\n"
                
            # Add field
            rival_name = rival_player.name if rival_player else rival_player_id
            embed.add_field(
                name=f"Rivalry with {rival_name}",
                value=field_value,
                inline=False
            )
        
        await ctx.followup.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(RivalriesCog(bot))