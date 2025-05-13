"""
Premium Commands Test Suite for Tower of Temptation PvP Statistics Bot

This module provides test cases for premium commands:
1. Premium-only commands
2. Premium feature access tests
3. Premium feature error handling

The suite verifies that premium commands work correctly
for premium users and are properly restricted for non-premium users.
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
    """Create premium commands test suite
    
    Returns:
        CommandTestSuite instance
    """
    suite = CommandTestSuite("Premium Commands")
    
    # Add setup function
    async def setup(bot, db):
        """Set up test environment"""
        # Create test guild with premium status
        await db.guilds.insert_one({
            "_id": "guild:100000000000000000",
            "guild_id": "100000000000000000",
            "name": "Premium Test Guild",
            "settings": {
                "premium": True,
                "canvas_size": 64,  # Premium size
                "custom_themes": ["dark", "light", "premium"]
            }
        })
        
        # Create non-premium guild
        await db.guilds.insert_one({
            "_id": "guild:200000000000000000",
            "guild_id": "200000000000000000",
            "name": "Standard Test Guild",
            "settings": {
                "premium": False,
                "canvas_size": 32  # Standard size
            }
        })
        
        # Create premium user
        await db.users.insert_one({
            "_id": "user:300000000000000000",
            "user_id": "300000000000000000",
            "username": "PremiumUser",
            "guilds": ["100000000000000000", "200000000000000000"],
            "inventory": {
                "credits": 1000,
                "premium_until": datetime.datetime.now() + datetime.timedelta(days=30),
                "premium_tier": "pro"
            }
        })
        
        # Create standard user
        await db.users.insert_one({
            "_id": "user:400000000000000000",
            "user_id": "400000000000000000",
            "username": "StandardUser",
            "guilds": ["100000000000000000", "200000000000000000"],
            "inventory": {
                "credits": 500,
                "premium_until": None
            }
        })
        
        # Mock premium command implementations
        async def mock_theme_command(ctx):
            """Custom theme command (premium only)"""
            # Check if premium
            guild_doc = await db.guilds.find_one({"guild_id": ctx.guild.id})
            if not guild_doc or not guild_doc.get("settings", {}).get("premium", False):
                embed = MagicMock()
                embed.title = "Premium Required"
                embed.description = "This command requires a premium subscription."
                await ctx.send(embed=embed)
                return
            
            theme = ctx.options.get("theme", "default")
            embed = MagicMock()
            embed.title = "Theme Applied"
            embed.description = f"Theme '{theme}' has been applied to the guild."
            await ctx.send(embed=embed)
        
        async def mock_export_command(ctx):
            """Export command (premium only)"""
            # Check if premium
            guild_doc = await db.guilds.find_one({"guild_id": ctx.guild.id})
            if not guild_doc or not guild_doc.get("settings", {}).get("premium", False):
                embed = MagicMock()
                embed.title = "Premium Required"
                embed.description = "This command requires a premium subscription."
                await ctx.send(embed=embed)
                return
            
            format_type = ctx.options.get("format", "csv")
            embed = MagicMock()
            embed.title = "Data Export"
            embed.description = f"Your data has been exported in {format_type} format."
            await ctx.send(embed=embed, file=f"export.{format_type}")
        
        async def mock_analytics_command(ctx):
            """Analytics command (premium only)"""
            # Check if premium
            guild_doc = await db.guilds.find_one({"guild_id": ctx.guild.id})
            if not guild_doc or not guild_doc.get("settings", {}).get("premium", False):
                embed = MagicMock()
                embed.title = "Premium Required"
                embed.description = "This command requires a premium subscription."
                await ctx.send(embed=embed)
                return
            
            period = ctx.options.get("period", "month")
            embed = MagicMock()
            embed.title = "Guild Analytics"
            embed.description = f"Analytics for the past {period}."
            embed.fields = [
                {"name": "Active Users", "value": "42", "inline": True},
                {"name": "Commands Used", "value": "530", "inline": True},
                {"name": "Popular Commands", "value": "canvas, profile, info", "inline": False}
            ]
            await ctx.send(embed=embed)
        
        # Register commands in bot mock
        theme_command = MagicMock()
        theme_command.name = "theme"
        theme_command._invoke = AsyncMock(side_effect=mock_theme_command)
        
        export_command = MagicMock()
        export_command.name = "export"
        export_command._invoke = AsyncMock(side_effect=mock_export_command)
        
        analytics_command = MagicMock()
        analytics_command.name = "analytics"
        analytics_command._invoke = AsyncMock(side_effect=mock_analytics_command)
        
        # Add premium status checker
        bot.is_premium = AsyncMock(side_effect=lambda guild_id: guild_id == "100000000000000000")
        bot.is_premium_user = AsyncMock(side_effect=lambda user_id: user_id == "300000000000000000")
        
        # Add to bot's application commands
        bot.application_commands.extend([
            theme_command,
            export_command,
            analytics_command
        ])
    
    suite.add_setup(setup)
    
    # Add teardown function
    async def teardown(bot, db):
        """Clean up test environment"""
        await db.guilds.delete_many({})
        await db.users.delete_many({})
    
    suite.add_teardown(teardown)
    
    # Test cases
    
    # 1. Test premium user in premium guild using premium command
    suite.add_test(create_slash_command_test(
        command_name="theme",
        guild_id="100000000000000000",  # Premium guild
        user_id="300000000000000000",  # Premium user
        options={"theme": "dark"},
        validators=[
            ResponseValidator(
                embed_title="Theme Applied",
                embed_description="Theme 'dark' has been applied to the guild."
            )
        ]
    ))
    
    # 2. Test standard user in premium guild using premium command
    # (should still work because guild is premium)
    suite.add_test(create_slash_command_test(
        command_name="export",
        guild_id="100000000000000000",  # Premium guild
        user_id="400000000000000000",  # Standard user
        options={"format": "csv"},
        validators=[
            ResponseValidator(
                embed_title="Data Export",
                embed_description="Your data has been exported in csv format."
            ),
            # Custom validator to check for file attachment
            CommandValidator(
                name="AttachmentValidator",
                validate=async lambda result, test_case: {
                    "passed": result.response and hasattr(result.response, "file"),
                    "message": "Expected file attachment in response"
                }
            )
        ]
    ))
    
    # 3. Test premium user in standard guild using premium command
    # (should fail because guild isn't premium)
    suite.add_test(create_slash_command_test(
        command_name="analytics",
        guild_id="200000000000000000",  # Standard guild
        user_id="300000000000000000",  # Premium user
        options={"period": "month"},
        validators=[
            ResponseValidator(
                embed_title="Premium Required",
                embed_description="This command requires a premium subscription."
            )
        ]
    ))
    
    # 4. Test standard user in standard guild using premium command
    # (should fail because neither user nor guild is premium)
    suite.add_test(create_slash_command_test(
        command_name="theme",
        guild_id="200000000000000000",  # Standard guild
        user_id="400000000000000000",  # Standard user
        options={"theme": "dark"},
        validators=[
            ResponseValidator(
                embed_title="Premium Required",
                embed_description="This command requires a premium subscription."
            )
        ]
    ))
    
    # 5. Test premium feature with higher canvas resolution
    suite.add_test(create_slash_command_test(
        command_name="canvas",
        guild_id="100000000000000000",  # Premium guild (64x64 canvas)
        user_id="300000000000000000",  # Premium user
        options={"x": 50, "y": 50},  # Beyond standard canvas size
        validators=[
            ResponseValidator(
                embed_title="Guild Canvas",
                content_contains=["coordinate", "50,50"]
            )
        ]
    ))
    
    # 6. Test invalid coordinates for standard canvas size
    suite.add_test(create_slash_command_test(
        command_name="canvas",
        guild_id="200000000000000000",  # Standard guild (32x32 canvas)
        user_id="400000000000000000",  # Standard user
        options={"x": 50, "y": 50},  # Beyond standard canvas size
        validators=[
            ResponseValidator(
                embed_title="Error",
                content_contains=["invalid", "coordinates", "out of bounds"]
            )
        ]
    ))
    
    return suite