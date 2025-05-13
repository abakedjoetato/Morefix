import discord
from discord.ext import commands
import logging
from utils.database import Database

logger = logging.getLogger("discord_bot")

class General(commands.Cog):
    """General purpose commands for the bot"""
    
    def __init__(self, bot):
        self.bot = bot
        self.db = Database()
    
    @commands.command(name="ping")
    async def ping(self, ctx):
        """Check the bot's latency"""
        latency = round(self.bot.latency * 1000)
        await ctx.send(f"Pong! Bot latency: {latency}ms")
    
    @commands.command(name="userinfo")
    async def userinfo(self, ctx, member: discord.Member = None):
        """Display information about a user"""
        member = member or ctx.author
        
        # Check if the user exists in the database, if not create a profile
        user_data = await self.db.get_user(member.id)
        if not user_data:
            user_data = await self.db.create_user(member.id, member.name)
        
        # Get the user's command usage count
        command_count = user_data.get("command_count", 0)
        
        # Create an embed with user information
        embed = discord.Embed(
            title=f"User Info - {member.name}",
            color=member.color
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="ID", value=member.id, inline=True)
        embed.add_field(name="Nickname", value=member.display_name, inline=True)
        embed.add_field(name="Account Created", value=member.created_at.strftime("%Y-%m-%d"), inline=True)
        embed.add_field(name="Joined Server", value=member.joined_at.strftime("%Y-%m-%d"), inline=True)
        embed.add_field(name="Roles", value=", ".join([role.name for role in member.roles[1:]]) or "None", inline=False)
        embed.add_field(name="Commands Used", value=command_count, inline=True)
        
        await ctx.send(embed=embed)
        
        # Update command usage count
        await self.db.increment_command_count(member.id)

    @commands.command(name="serverinfo")
    async def serverinfo(self, ctx):
        """Display information about the server"""
        guild = ctx.guild
        
        # Store server stats in the database
        await self.db.update_server_stats(
            guild.id,
            {
                "name": guild.name,
                "member_count": guild.member_count,
                "channel_count": len(guild.channels),
                "role_count": len(guild.roles)
            }
        )
        
        # Create an embed with server information
        embed = discord.Embed(
            title=f"Server Info - {guild.name}",
            color=discord.Color.blue()
        )
        embed.set_thumbnail(url=guild.icon.url if guild.icon else "")
        embed.add_field(name="ID", value=guild.id, inline=True)
        embed.add_field(name="Owner", value=guild.owner.name, inline=True)
        embed.add_field(name="Created On", value=guild.created_at.strftime("%Y-%m-%d"), inline=True)
        embed.add_field(name="Member Count", value=guild.member_count, inline=True)
        embed.add_field(name="Channels", value=len(guild.channels), inline=True)
        embed.add_field(name="Roles", value=len(guild.roles), inline=True)
        
        await ctx.send(embed=embed)
        
        # Update command usage count
        await self.db.increment_command_count(ctx.author.id)

    @commands.Cog.listener()
    async def on_message(self, message):
        """Process each message sent in channels the bot can see"""
        # Ignore messages from bots
        if message.author.bot:
            return
        
        # Log message activity to the database
        await self.db.log_message_activity(
            message.author.id,
            message.guild.id if message.guild else None,
            message.channel.id,
            len(message.content)
        )

async def setup(bot):
    await bot.add_cog(General(bot))
    logger.info("General commands cog loaded")
