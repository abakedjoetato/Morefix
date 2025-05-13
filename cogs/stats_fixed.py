"""
Statistics commands for player and server stats
"""
import logging
import asyncio
import traceback
import discord
from discord.ext import commands
from utils.discord_patches import app_commands
from typing import Union, List, Dict, Any, Optional
from datetime import datetime, timedelta

# Import the standardized premium verification
from utils.premium_verification import premium_feature_required, verify_premium_access
from utils.discord_compat import guild_only as discord_compat_guild_only

from models.server import Server
from models.player import Player
from models.guild import Guild
from utils.embed_builder import EmbedBuilder
from config import EMBED_COLOR, EMBED_FOOTER
from utils.helpers import paginate_embeds, format_time_ago
from utils.discord_utils import server_id_autocomplete

logger = logging.getLogger(__name__)


async def player_name_autocomplete(interaction: discord.Interaction, current: str):
    """Autocomplete for player names"""
    try:
        # Get user's guild ID
        guild_id = str(interaction.guild_id) if interaction.guild_id else None

        if guild_id is None:
            return [app_commands.Choice(name="Must use in a server", value="")]

        # Try to get the server_id from the interaction
        server_id = None
        try:
            # Get focused option (field that's currently being typed in)
            focused = None
            for option in interaction.data.get("options", []):
                if option.get("focused", False):
                    focused = option
                    break

            # Get the other options to find server_id if available
            for option in interaction.data.get("options", []):
                if option.get("name") == "server_id" and not option.get("focused", False):
                    server_id = option.get("value")
                    break
        except Exception as e:
            logger.error(f"Error getting server_id from interaction: {e}")

        # Find the Stats cog instance to access cache
        cog = None
        for c in interaction.client.cogs.values():
            if isinstance(c, StatsFixed):
                cog = c
                break

        if cog is None:
            return [app_commands.Choice(name="Error finding stats module", value="")]

        # Create cache key
        cache_key = f"{guild_id}:{server_id}" if server_id else guild_id

        # Get guild
        guild = await Guild.get_guild(interaction.client.db, guild_id)
        if not guild:
            return [app_commands.Choice(name="Guild not found", value="")]

        # If a specific server_id was provided, validate it exists
        if server_id:
            if server_id not in guild.servers:
                return [app_commands.Choice(name="Invalid server", value="")]
        # If no server_id was provided, but guild has only one server, use that
        elif len(guild.servers) == 1:
            server_id = list(guild.servers.keys())[0]
            # Update cache key
            cache_key = f"{guild_id}:{server_id}"

        # Check if we have a cached version that's recent
        cache_data = cog.player_autocomplete_cache.get(cache_key, None)
        if (cache_data is None or
            (datetime.now() - cache_data.get("last_update", datetime.now())).total_seconds() > 300):

            # No recent cache, need to fetch from database
            try:
                # Get player list from database with timeout
                if server_id:
                    task = Player.get_player_list(
                        interaction.client.db,
                        server_id,
                        search_name=current if current else None
                    )
                    players = await asyncio.wait_for(
                        task,
                        timeout=2.0
                    )

                    if players is not None:
                        # Update cache with valid player data
                        player_list = []
                        for player_data in players:
                            player_id = player_data.get("player_id", "")
                            player_name = player_data.get("player_name", "Unknown Player")

                            # Skip invalid entries
                            if player_name is None or player_name == "" or player_name == "Unknown Player":
                                continue

                            player_list.append({
                                "id": player_id,
                                "name": player_name
                            })

                        # Update cache
                        cog.player_autocomplete_cache[cache_key] = {
                            "players": player_list,
                            "last_update": datetime.now()
                        }
            except asyncio.TimeoutError:
                logger.warning(f"Database timeout in player_name_autocomplete for server {server_id}")
                # Use existing cache if available
                if cache_key not in cog.player_autocomplete_cache:
                    return [app_commands.Choice(name="Timeout loading players", value="")]
            except Exception as e:
                logger.error(f"Error fetching players: {e}")
                # Use existing cache if available
                if cache_key not in cog.player_autocomplete_cache:
                    return [app_commands.Choice(name="Error loading players", value="")]

        # Get players from cache
        players = cog.player_autocomplete_cache.get(cache_key, {}).get("players", [])

        if players is None or len(players) == 0:
            return [app_commands.Choice(name="No players found", value="")]

        # Filter players for autocomplete
        if current:
            current_lower = current.lower()
            matches = [
                p for p in players
                if current_lower in p.get("name", "").lower()
            ]
        else:
            # No search term, return all (up to 25)
            matches = players[:25]

        # Sort matches by name
        matches.sort(key=lambda p: p.get("name", ""))

        # Return choices
        return [
            app_commands.Choice(name=player.get("name", "Unknown"), value=player.get("name", ""))
            for player in matches[:25]  # Limit to 25 results
        ]

    except Exception as e:
        logger.error(f"Error in player_name_autocomplete: {e}")
        return [app_commands.Choice(name=f"Error: {str(e)[:90]}", value="")]


class StatsFixed(commands.Cog):
    """Stats commands for player and server stats"""

    def __init__(self, bot):
        self.bot = bot
        # Cache for player autocomplete
        self.player_autocomplete_cache = {}

    # Renamed command group to game_stats to avoid conflict
    @commands.hybrid_group(name="game_stats", description="Game statistics commands")
    @discord_compat_guild_only()  # Using our compatibility wrapper
    @premium_feature_required(feature_name="stats")  # Using standardized feature-based access control
    async def game_stats(self, ctx):
        """Stats command group"""
        # Log command access for debugging
        logger.info(f"Stats command accessed by user {ctx.author.id} in guild {ctx.guild.id}")

        # Premium tier access already verified by the decorator

        if ctx.invoked_subcommand is None:
            await ctx.send("Please specify a subcommand.")

    @game_stats.command(name="player", description="View player statistics")
    @app_commands.describe(
        server_id="Select a server by name to check stats for",
        player_name="The player name to search for"
    )
    @app_commands.autocomplete(server_id=server_id_autocomplete, player_name=player_name_autocomplete)
    @premium_feature_required(feature_name="stats")  # Stats require premium access
    async def player_stats(self, ctx, server_id: str, player_name: str):
        """View statistics for a player"""
        try:
            # Initialize guild_model to None first to avoid UnboundLocalError
            guild_model = None

            # Defer response to prevent timeout
            await ctx.defer()

            # Get guild using the get_guild method for consistency
            guild = await Guild.get_guild(self.bot.db, ctx.guild.id)
            guild_model = guild  # Use the guild as the model for embed theming
            
            if not guild:
                embed = await EmbedBuilder.create_error_embed(
                    title="Error",
                    description="Guild not found in database"
                )
                await ctx.followup.send(embed=embed)
                return

            # Verify premium access (this is also done by the decorator)
            if not await verify_premium_access(self.bot.db, ctx.guild.id, "stats"):
                embed = await EmbedBuilder.create_error_embed(
                    title="Premium Feature",
                    description="Stats commands require premium access. Please upgrade to use this feature."
                )
                await ctx.followup.send(embed=embed)
                return

            # Verify server exists for this guild
            if server_id not in guild.servers:
                embed = await EmbedBuilder.create_error_embed(
                    guild=guild_model,
                    title="Invalid Server",
                    description=f"Server '{server_id}' not found. Use `/listservers` to see available servers."
                )
                await ctx.followup.send(embed=embed)
                return

            # Get player data
            player = await Player.get_by_name(self.bot.db, player_name, server_id)
            if not player:
                embed = await EmbedBuilder.create_error_embed(
                    guild=guild_model,
                    title="Player Not Found",
                    description=f"Player '{player_name}' not found on server '{server_id}'."
                )
                await ctx.followup.send(embed=embed)
                return

            # Get server object
            server = Server.from_dict(guild.servers.get(server_id))

            # Create base embed
            embed = await EmbedBuilder.create_base_embed(
                guild=guild_model,
                title=f"Player Stats for {player.name}",
                description=f"Statistics for {player.name} on {server.name}"
            )

            # Add player info
            embed.add_field(
                name="Player Info",
                value=f"**Name:** {player.name}\n**ID:** {player.player_id}\n**Last Seen:** {format_time_ago(player.last_seen)}",
                inline=False
            )

            # Add kill stats
            embed.add_field(
                name="Kill Statistics",
                value=f"**Kills:** {player.kills}\n**Deaths:** {player.deaths}\n**K/D Ratio:** {player.kd_ratio:.2f}",
                inline=True
            )

            # Add additional stats
            embed.add_field(
                name="Additional Stats",
                value=f"**Longest Kill:** {player.longest_kill}m\n**Last Killer:** {player.last_killer or 'None'}\n**Last Victim:** {player.last_victim or 'None'}",
                inline=True
            )

            # Add timestamp
            embed.set_footer(text=f"Last updated {format_time_ago(player.last_updated)}")

            await ctx.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in player_stats command: {e}")
            logger.error(traceback.format_exc())
            
            # Create error embed
            try:
                embed = await EmbedBuilder.create_error_embed(
                    guild=guild_model,
                    title="Error",
                    description=f"An error occurred: {str(e)}"
                )
                await ctx.followup.send(embed=embed)
            except:
                # Fallback if custom embed fails
                await ctx.followup.send(f"An error occurred: {str(e)}")

    @game_stats.command(name="server", description="View server statistics")
    @app_commands.describe(
        server_id="Select a server by name to check stats for"
    )
    @app_commands.autocomplete(server_id=server_id_autocomplete)
    @premium_feature_required(feature_name="stats")  # Stats require premium access
    async def server_stats(self, ctx, server_id: str):
        """View statistics for a server"""
        try:
            # Initialize guild_model to None first to avoid UnboundLocalError
            guild_model = None

            # Defer response to prevent timeout
            await ctx.defer()

            # Get guild using the get_guild method for consistency
            guild = await Guild.get_guild(self.bot.db, ctx.guild.id)
            guild_model = guild  # Use the guild as the model for embed theming
            
            if not guild:
                embed = await EmbedBuilder.create_error_embed(
                    title="Error",
                    description="Guild not found in database"
                )
                await ctx.followup.send(embed=embed)
                return

            # Verify premium access (this is also done by the decorator)
            if not await verify_premium_access(self.bot.db, ctx.guild.id, "stats"):
                embed = await EmbedBuilder.create_error_embed(
                    title="Premium Feature",
                    description="Stats commands require premium access. Please upgrade to use this feature."
                )
                await ctx.followup.send(embed=embed)
                return

            # Verify server exists for this guild
            if server_id not in guild.servers:
                embed = await EmbedBuilder.create_error_embed(
                    guild=guild_model,
                    title="Invalid Server",
                    description=f"Server '{server_id}' not found. Use `/listservers` to see available servers."
                )
                await ctx.followup.send(embed=embed)
                return

            # Get server data
            server = Server.from_dict(guild.servers.get(server_id))

            # Get server stats
            stats = await Player.get_server_stats(self.bot.db, server_id)
            if not stats:
                embed = await EmbedBuilder.create_error_embed(
                    guild=guild_model,
                    title="Statistics Not Available",
                    description=f"No statistics available for server '{server_id}'."
                )
                await ctx.followup.send(embed=embed)
                return

            # Create base embed
            embed = await EmbedBuilder.create_base_embed(
                guild=guild_model,
                title=f"Server Stats for {server.name}",
                description=f"Statistics for {server.name}"
            )

            # Add server info
            embed.add_field(
                name="Server Info",
                value=f"**Name:** {server.name}\n**ID:** {server_id}",
                inline=False
            )

            # Add general stats
            embed.add_field(
                name="General Statistics",
                value=f"**Total Players:** {stats.get('total_players', 0)}\n**Total Kills:** {stats.get('total_kills', 0)}\n**Total Deaths:** {stats.get('total_deaths', 0)}",
                inline=True
            )

            # Add top killer
            top_killer = stats.get('top_killer', {})
            top_killer_name = top_killer.get('name', 'None')
            top_killer_kills = top_killer.get('kills', 0)
            
            embed.add_field(
                name="Top Killer",
                value=f"**Player:** {top_killer_name}\n**Kills:** {top_killer_kills}",
                inline=True
            )

            # Add timestamp
            embed.set_footer(text=f"Last updated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

            await ctx.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in server_stats command: {e}")
            logger.error(traceback.format_exc())
            
            # Create error embed
            try:
                embed = await EmbedBuilder.create_error_embed(
                    guild=guild_model,
                    title="Error",
                    description=f"An error occurred: {str(e)}"
                )
                await ctx.followup.send(embed=embed)
            except:
                # Fallback if custom embed fails
                await ctx.followup.send(f"An error occurred: {str(e)}")

    @game_stats.command(name="top", description="View top players on a server")
    @app_commands.describe(
        server_id="Select a server by name to check stats for",
        stat="Statistic to sort by",
        limit="Number of players to show (max 25)"
    )
    @app_commands.choices(stat=[
        app_commands.Choice(name="Kills", value="kills"),
        app_commands.Choice(name="Deaths", value="deaths"),
        app_commands.Choice(name="K/D Ratio", value="kd_ratio"),
        app_commands.Choice(name="Longest Kill", value="longest_kill"),
    ])
    @app_commands.autocomplete(server_id=server_id_autocomplete)
    @premium_feature_required(feature_name="stats")  # Stats require premium access
    async def top_players(self, ctx, server_id: str, stat: str, limit: int = 10):
        """View top players on a server"""
        try:
            # Initialize guild_model to None first to avoid UnboundLocalError
            guild_model = None

            # Validate limit
            if limit < 1:
                limit = 10
            elif limit > 25:
                limit = 25

            # Defer response to prevent timeout
            await ctx.defer()

            # Get guild using the get_guild method for consistency
            guild = await Guild.get_guild(self.bot.db, ctx.guild.id)
            guild_model = guild  # Use the guild as the model for embed theming
            
            if not guild:
                embed = await EmbedBuilder.create_error_embed(
                    title="Error",
                    description="Guild not found in database"
                )
                await ctx.followup.send(embed=embed)
                return

            # Verify premium access (this is also done by the decorator)
            if not await verify_premium_access(self.bot.db, ctx.guild.id, "stats"):
                embed = await EmbedBuilder.create_error_embed(
                    title="Premium Feature",
                    description="Stats commands require premium access. Please upgrade to use this feature."
                )
                await ctx.followup.send(embed=embed)
                return

            # Verify server exists for this guild
            if server_id not in guild.servers:
                embed = await EmbedBuilder.create_error_embed(
                    guild=guild_model,
                    title="Invalid Server",
                    description=f"Server '{server_id}' not found. Use `/listservers` to see available servers."
                )
                await ctx.followup.send(embed=embed)
                return

            # Get server data
            server = Server.from_dict(guild.servers.get(server_id))

            # Get top players for the selected stat
            top_players = await Player.get_top_players(self.bot.db, server_id, stat, limit)
            if not top_players:
                embed = await EmbedBuilder.create_error_embed(
                    guild=guild_model,
                    title="No Players",
                    description=f"No player statistics available for server '{server_id}'."
                )
                await ctx.followup.send(embed=embed)
                return

            # Create base embed
            stat_name = {
                "kills": "Kills",
                "deaths": "Deaths",
                "kd_ratio": "K/D Ratio",
                "longest_kill": "Longest Kill"
            }.get(stat, stat.capitalize())
            
            embed = await EmbedBuilder.create_base_embed(
                guild=guild_model,
                title=f"Top Players by {stat_name}",
                description=f"Top {len(top_players)} players on {server.name} by {stat_name.lower()}"
            )

            # Format players list
            players_text = ""
            for i, player in enumerate(top_players):
                # Format the stat value based on the type
                if stat == "kd_ratio":
                    stat_value = f"{player.get(stat, 0):.2f}"
                elif stat == "longest_kill":
                    stat_value = f"{player.get(stat, 0)}m"
                else:
                    stat_value = str(player.get(stat, 0))
                    
                players_text += f"**{i+1}.** {player.get('name', 'Unknown')}: {stat_value}\n"

            embed.add_field(
                name=f"Top Players by {stat_name}",
                value=players_text or "No players found",
                inline=False
            )

            # Add timestamp
            embed.set_footer(text=f"Last updated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

            await ctx.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in top_players command: {e}")
            logger.error(traceback.format_exc())
            
            # Create error embed
            try:
                embed = await EmbedBuilder.create_error_embed(
                    guild=guild_model,
                    title="Error",
                    description=f"An error occurred: {str(e)}"
                )
                await ctx.followup.send(embed=embed)
            except:
                # Fallback if custom embed fails
                await ctx.followup.send(f"An error occurred: {str(e)}")

async def setup(bot):
    await bot.add_cog(StatsFixed(bot))