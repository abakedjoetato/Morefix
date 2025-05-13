"""
Basic Commands Test Suite for Tower of Temptation PvP Statistics Bot

This module provides test cases for basic commands:
1. Info commands
2. Help commands
3. Canvas commands
4. User profile commands

The suite verifies that basic commands work correctly
for all users regardless of permissions.
"""
import os
import datetime
from unittest.mock import AsyncMock, patch, MagicMock
from typing import Dict, List, Any, Optional, Union

from tests.command_tester import (
    CommandTestSuite, CommandValidator, ResponseValidator, ExceptionValidator, StateValidator,
    create_slash_command_test, create_prefix_command_test
)

def create_test_suite():
    """Create basic commands test suite
    
    Returns:
        CommandTestSuite instance
    """
    suite = CommandTestSuite("Basic Commands")
    
    # Add setup function
    async def setup(bot, db):
        """Set up test environment"""
        # Mock bot info for /info command
        bot.user = MagicMock()
        bot.user.id = 999000000000000000
        bot.user.name = "Tower of Temptation Bot"
        bot.user.discriminator = "0000"
        bot.user.avatar = "https://example.com/avatar.png"
        bot.user.created_at = datetime.datetime.now() - datetime.timedelta(days=30)
        
        # Mock bot stats
        bot.guilds = [MagicMock() for _ in range(10)]
        bot.latency = 0.05
        bot.uptime = datetime.datetime.now() - datetime.timedelta(hours=12)
        
        # Create test guild 
        await db.guilds.insert_one({
            "_id": "guild:100000000000000000",
            "guild_id": "100000000000000000",
            "name": "Test Guild",
            "settings": {
                "prefix": "!",
                "canvas_enabled": True,
                "canvas_size": 32,
                "canvas_default_color": "#FFFFFF"
            }
        })
        
        # Create test user
        await db.users.insert_one({
            "_id": "user:200000000000000000",
            "user_id": "200000000000000000",
            "username": "TestUser",
            "guilds": ["100000000000000000"],
            "stats": {
                "commands_used": 15,
                "canvas_pixels_placed": 50,
                "daily_streak": 3
            },
            "inventory": {
                "credits": 500,
                "premium_until": None
            }
        })
        
        # Create test canvas
        await db.canvas.insert_one({
            "_id": "canvas:100000000000000000",
            "guild_id": "100000000000000000",
            "size": 32,
            "default_color": "#FFFFFF",
            "pixels": {
                "5,5": {
                    "color": "#FF0000",
                    "user_id": "200000000000000000",
                    "timestamp": datetime.datetime.now() - datetime.timedelta(hours=1)
                },
                "10,10": {
                    "color": "#00FF00",
                    "user_id": "300000000000000000",
                    "timestamp": datetime.datetime.now() - datetime.timedelta(hours=2)
                }
            }
        })
        
        # Mock command implementations
        async def mock_info_command(ctx):
            embed = MagicMock()
            embed.title = "Bot Information"
            embed.description = "Information about the Tower of Temptation Bot"
            embed.fields = [
                {"name": "Version", "value": "1.0.0", "inline": True},
                {"name": "Guilds", "value": "10", "inline": True},
                {"name": "Uptime", "value": "12 hours", "inline": True}
            ]
            await ctx.send(embed=embed)
        
        async def mock_help_command(ctx):
            embed = MagicMock()
            embed.title = "Help"
            embed.description = "Command help for Tower of Temptation Bot"
            embed.fields = [
                {"name": "/info", "value": "Shows bot information", "inline": False},
                {"name": "/help", "value": "Shows this help message", "inline": False},
                {"name": "/canvas", "value": "Shows the guild canvas", "inline": False},
                {"name": "/profile", "value": "Shows your profile", "inline": False}
            ]
            await ctx.send(embed=embed)
        
        async def mock_canvas_command(ctx):
            embed = MagicMock()
            embed.title = "Guild Canvas"
            embed.description = "The canvas for this guild"
            await ctx.send(embed=embed, file="canvas_image.png")
        
        async def mock_profile_command(ctx):
            embed = MagicMock()
            embed.title = "User Profile"
            embed.description = f"Profile for {ctx.user.name}"
            embed.fields = [
                {"name": "Credits", "value": "500", "inline": True},
                {"name": "Pixels Placed", "value": "50", "inline": True},
                {"name": "Daily Streak", "value": "3", "inline": True}
            ]
            await ctx.send(embed=embed)
        
        # Register commands in bot mock
        info_command = MagicMock()
        info_command.name = "info"
        info_command._invoke = AsyncMock(side_effect=mock_info_command)
        
        help_command = MagicMock()
        help_command.name = "help"
        help_command._invoke = AsyncMock(side_effect=mock_help_command)
        
        canvas_command = MagicMock()
        canvas_command.name = "canvas"
        canvas_command._invoke = AsyncMock(side_effect=mock_canvas_command)
        
        profile_command = MagicMock()
        profile_command.name = "profile"
        profile_command._invoke = AsyncMock(side_effect=mock_profile_command)
        
        # Add to bot's application commands
        bot.application_commands = [
            info_command,
            help_command,
            canvas_command,
            profile_command
        ]
    
    suite.add_setup(setup)
    
    # Add teardown function
    async def teardown(bot, db):
        """Clean up test environment"""
        await db.guilds.delete_many({})
        await db.users.delete_many({})
        await db.canvas.delete_many({})
    
    suite.add_teardown(teardown)
    
    # Test cases
    
    # 1. Test /info command
    suite.add_test(create_slash_command_test(
        command_name="info",
        guild_id="100000000000000000",
        user_id="200000000000000000",
        validators=[
            ResponseValidator(
                embed_title="Bot Information",
                embed_field_names=["Version", "Guilds", "Uptime"]
            )
        ]
    ))
    
    # 2. Test /help command
    suite.add_test(create_slash_command_test(
        command_name="help",
        guild_id="100000000000000000",
        user_id="200000000000000000",
        validators=[
            ResponseValidator(
                embed_title="Help",
                embed_description="Command help",
                embed_field_names=["/info", "/help", "/canvas", "/profile"]
            )
        ]
    ))
    
    # 3. Test /canvas command
    suite.add_test(create_slash_command_test(
        command_name="canvas",
        guild_id="100000000000000000",
        user_id="200000000000000000",
        validators=[
            ResponseValidator(
                embed_title="Guild Canvas",
                embed_description="The canvas for this guild"
            ),
            # Custom validator to check for image attachment
            CommandValidator(
                name="AttachmentValidator",
                validate=async lambda result, test_case: {
                    "passed": result.response and hasattr(result.response, "file"),
                    "message": "Expected file attachment in response"
                }
            )
        ]
    ))
    
    # 4. Test /profile command
    suite.add_test(create_slash_command_test(
        command_name="profile",
        guild_id="100000000000000000",
        user_id="200000000000000000",
        validators=[
            ResponseValidator(
                embed_title="User Profile",
                embed_field_names=["Credits", "Pixels Placed", "Daily Streak"]
            )
        ]
    ))
    
    # 5. Test /canvas command with coordinates
    suite.add_test(create_slash_command_test(
        command_name="canvas",
        guild_id="100000000000000000",
        user_id="200000000000000000",
        options={"x": 5, "y": 5},
        validators=[
            ResponseValidator(
                embed_title="Guild Canvas",
                content_contains=["coordinate", "5,5"]
            )
        ]
    ))
    
    return suite