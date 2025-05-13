"""
Multi-Guild Tests for Tower of Temptation PvP Statistics Bot

This module provides multi-guild isolation tests:
1. Data isolation between guilds
2. Guild-specific configuration
3. Cross-guild user interactions

These tests verify that data remains properly isolated between guilds
while allowing users to interact across multiple servers.
"""
import os
import sys
import asyncio
import datetime
import logging
from unittest.mock import MagicMock, AsyncMock, patch
from typing import Dict, List, Any, Optional, Union

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import test modules
from tests.command_tester import (
    CommandTestSuite, CommandValidator, ResponseValidator, ExceptionValidator, StateValidator,
    create_slash_command_test, create_prefix_command_test, run_tests
)
from tests.test_fixtures import setup_test_database
from tests.discord_mocks import (
    MockUser, MockGuild, MockChannel, MockMessage, 
    MockInteraction, MockContext, MockApplicationContext,
    create_mock_user, create_mock_guild, create_mock_interaction, 
    create_mock_context, create_mock_application_context
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("multi_guild_tests")

# Guild isolation validator
class GuildIsolationValidator(CommandValidator):
    """Validates that data is properly isolated between guilds"""
    
    def __init__(self, collection, guild_id_field, query, expected_count=1):
        """Initialize guild isolation validator
        
        Args:
            collection: Database collection to query
            guild_id_field: Field name that contains guild ID
            query: MongoDB query to execute
            expected_count: Expected number of documents to find
        """
        super().__init__(name="GuildIsolationValidator")
        self.collection = collection
        self.guild_id_field = guild_id_field
        self.query = query
        self.expected_count = expected_count
    
    async def validate(self, result, test_case):
        """Validate guild isolation
        
        Args:
            result: Test result
            test_case: Test case
            
        Returns:
            Validation result
        """
        # Check if database is available
        if not test_case.db:
            return {
                "passed": False,
                "message": "Database not available for validation"
            }
        
        try:
            # Get collection
            collection = getattr(test_case.db, self.collection)
            
            # Execute query
            count = await collection.count_documents(self.query)
            
            # Verify count matches expected
            if count != self.expected_count:
                return {
                    "passed": False,
                    "message": f"Found {count} documents, expected {self.expected_count}"
                }
            
            # Verify all documents belong to the correct guild
            cursor = collection.find(self.query)
            documents = await cursor.to_list(length=100)
            
            # Check guild IDs
            for doc in documents:
                # Handle nested fields
                parts = self.guild_id_field.split('.')
                value = doc
                for part in parts:
                    if part not in value:
                        return {
                            "passed": False,
                            "message": f"Field {self.guild_id_field} not found in document"
                        }
                    value = value[part]
                
                # Verify guild ID
                if value != test_case.guild_id:
                    return {
                        "passed": False,
                        "message": f"Document has guild ID {value}, expected {test_case.guild_id}"
                    }
            
            # All validations passed
            return {
                "passed": True,
                "message": None
            }
        
        except Exception as e:
            return {
                "passed": False,
                "message": f"Guild isolation validation error: {type(e).__name__}: {e}"
            }

# Test suite for canvas isolation
def build_canvas_isolation_test_suite():
    """Build canvas isolation test suite
    
    Returns:
        CommandTestSuite instance
    """
    suite = CommandTestSuite("Canvas Isolation")
    
    # Add setup function
    async def setup(bot, db):
        """Set up test environment"""
        # Create test guilds
        await db.guilds.insert_one({
            "_id": "guild:100000000000000000",
            "guild_id": "100000000000000000",
            "name": "Guild A",
            "settings": {
                "canvas_enabled": True,
                "canvas_size": 32,
                "canvas_default_color": "#FFFFFF"
            }
        })
        
        await db.guilds.insert_one({
            "_id": "guild:200000000000000000",
            "guild_id": "200000000000000000",
            "name": "Guild B",
            "settings": {
                "canvas_enabled": True,
                "canvas_size": 64,  # Different size
                "canvas_default_color": "#000000"  # Different default color
            }
        })
        
        # Create test user (member of both guilds)
        await db.users.insert_one({
            "_id": "user:300000000000000000",
            "user_id": "300000000000000000",
            "username": "TestUser",
            "guilds": ["100000000000000000", "200000000000000000"],
            "inventory": {
                "credits": 500,
                "colors": ["#FF0000", "#00FF00", "#0000FF"]
            }
        })
        
        # Create initial canvas data for Guild A
        await db.canvas.insert_one({
            "_id": "canvas:100000000000000000",
            "guild_id": "100000000000000000",
            "size": 32,
            "default_color": "#FFFFFF",
            "pixels": {
                "5,5": {
                    "color": "#FF0000",
                    "user_id": "300000000000000000",
                    "timestamp": datetime.datetime.now() - datetime.timedelta(hours=1)
                }
            }
        })
        
        # Create initial canvas data for Guild B
        await db.canvas.insert_one({
            "_id": "canvas:200000000000000000",
            "guild_id": "200000000000000000",
            "size": 64,
            "default_color": "#000000",
            "pixels": {
                "10,10": {
                    "color": "#00FF00",
                    "user_id": "300000000000000000",
                    "timestamp": datetime.datetime.now() - datetime.timedelta(hours=1)
                }
            }
        })
        
        # Mock canvas command implementation
        async def mock_canvas_command(ctx):
            # Get guild canvas
            canvas_doc = await db.canvas.find_one({"guild_id": ctx.guild.id})
            if not canvas_doc:
                await ctx.send("Canvas not found for this guild")
                return
            
            # Get coordinate focus if provided
            x = ctx.options.get("x")
            y = ctx.options.get("y")
            
            # Create response
            if x is not None and y is not None:
                # Get pixel at coordinates
                pixel_key = f"{x},{y}"
                pixel = canvas_doc.get("pixels", {}).get(pixel_key)
                
                if pixel:
                    await ctx.send(f"Pixel at ({x}, {y}) is {pixel['color']} placed by <@{pixel['user_id']}>")
                else:
                    default_color = canvas_doc.get("default_color", "#FFFFFF")
                    await ctx.send(f"Pixel at ({x}, {y}) is empty (default: {default_color})")
            else:
                # Return full canvas
                size = canvas_doc.get("size", 32)
                pixel_count = len(canvas_doc.get("pixels", {}))
                await ctx.send(f"Canvas for {ctx.guild.name} ({size}x{size}) with {pixel_count} pixels placed")
        
        # Mock pixel command implementation
        async def mock_pixel_command(ctx):
            # Get coordinates and color
            x = ctx.options.get("x", 0)
            y = ctx.options.get("y", 0)
            color = ctx.options.get("color", "#000000")
            
            # Get guild canvas
            canvas_doc = await db.canvas.find_one({"guild_id": ctx.guild.id})
            if not canvas_doc:
                await ctx.send("Canvas not found for this guild")
                return
            
            # Check if coordinates are valid
            size = canvas_doc.get("size", 32)
            if x < 0 or x >= size or y < 0 or y >= size:
                await ctx.send(f"Invalid coordinates. Canvas size is {size}x{size}")
                return
            
            # Update canvas
            await db.canvas.update_one(
                {"guild_id": ctx.guild.id},
                {
                    "$set": {
                        f"pixels.{x},{y}": {
                            "color": color,
                            "user_id": ctx.user.id,
                            "timestamp": datetime.datetime.now()
                        }
                    }
                }
            )
            
            await ctx.send(f"Pixel placed at ({x}, {y}) with color {color} in {ctx.guild.name}")
        
        # Register commands in bot mock
        canvas_command = MagicMock()
        canvas_command.name = "canvas"
        canvas_command._invoke = AsyncMock(side_effect=mock_canvas_command)
        
        pixel_command = MagicMock()
        pixel_command.name = "pixel"
        pixel_command._invoke = AsyncMock(side_effect=mock_pixel_command)
        
        # Add to bot's application commands
        bot.application_commands = [
            canvas_command,
            pixel_command
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
    
    # 1. Test canvas command in Guild A
    suite.add_test(create_slash_command_test(
        command_name="canvas",
        guild_id="100000000000000000",  # Guild A
        user_id="300000000000000000",
        validators=[
            ResponseValidator(
                content_contains=["Canvas for Guild A", "32x32", "1 pixels"]
            )
        ]
    ))
    
    # 2. Test canvas command in Guild B
    suite.add_test(create_slash_command_test(
        command_name="canvas",
        guild_id="200000000000000000",  # Guild B
        user_id="300000000000000000",
        validators=[
            ResponseValidator(
                content_contains=["Canvas for Guild B", "64x64", "1 pixels"]
            )
        ]
    ))
    
    # 3. Test checking pixel in Guild A
    suite.add_test(create_slash_command_test(
        command_name="canvas",
        guild_id="100000000000000000",  # Guild A
        user_id="300000000000000000",
        options={"x": 5, "y": 5},
        validators=[
            ResponseValidator(
                content_contains=["Pixel at (5, 5)", "#FF0000"]
            )
        ]
    ))
    
    # 4. Test checking same coordinates in Guild B (should be different)
    suite.add_test(create_slash_command_test(
        command_name="canvas",
        guild_id="200000000000000000",  # Guild B
        user_id="300000000000000000",
        options={"x": 5, "y": 5},
        validators=[
            ResponseValidator(
                content_contains=["empty", "default: #000000"]  # Different default color
            )
        ]
    ))
    
    # 5. Test placing a pixel in Guild A
    suite.add_test(create_slash_command_test(
        command_name="pixel",
        guild_id="100000000000000000",  # Guild A
        user_id="300000000000000000",
        options={"x": 15, "y": 15, "color": "#FF00FF"},
        validators=[
            ResponseValidator(
                content_contains=["Pixel placed", "15, 15", "#FF00FF", "Guild A"]
            ),
            # Verify pixel was added to Guild A only
            GuildIsolationValidator(
                collection="canvas",
                guild_id_field="guild_id",
                query={"pixels.15,15": {"$exists": True}},
                expected_count=1
            )
        ]
    ))
    
    # 6. Test placing a pixel at same coordinates in Guild B
    suite.add_test(create_slash_command_test(
        command_name="pixel",
        guild_id="200000000000000000",  # Guild B
        user_id="300000000000000000",
        options={"x": 15, "y": 15, "color": "#00FFFF"},  # Different color
        validators=[
            ResponseValidator(
                content_contains=["Pixel placed", "15, 15", "#00FFFF", "Guild B"]
            )
        ]
    ))
    
    # 7. Verify pixel in Guild A didn't change
    suite.add_test(create_slash_command_test(
        command_name="canvas",
        guild_id="100000000000000000",  # Guild A
        user_id="300000000000000000",
        options={"x": 15, "y": 15},
        validators=[
            ResponseValidator(
                content_contains=["#FF00FF"]  # Still the color we set for Guild A
            )
        ]
    ))
    
    # 8. Verify pixel in Guild B has its own value
    suite.add_test(create_slash_command_test(
        command_name="canvas",
        guild_id="200000000000000000",  # Guild B
        user_id="300000000000000000",
        options={"x": 15, "y": 15},
        validators=[
            ResponseValidator(
                content_contains=["#00FFFF"]  # The color we set for Guild B
            )
        ]
    ))
    
    # 9. Test out-of-bounds coordinates (different for each guild)
    suite.add_test(create_slash_command_test(
        command_name="pixel",
        guild_id="100000000000000000",  # Guild A (32x32)
        user_id="300000000000000000",
        options={"x": 40, "y": 40, "color": "#FFFFFF"},
        validators=[
            ResponseValidator(
                content_contains=["Invalid coordinates", "32x32"]
            )
        ]
    ))
    
    # 10. Same coordinates should be valid in Guild B
    suite.add_test(create_slash_command_test(
        command_name="pixel",
        guild_id="200000000000000000",  # Guild B (64x64)
        user_id="300000000000000000",
        options={"x": 40, "y": 40, "color": "#FFFFFF"},
        validators=[
            ResponseValidator(
                content_contains=["Pixel placed", "40, 40"]  # Valid in 64x64 canvas
            )
        ]
    ))
    
    return suite

# Test suite for guild configuration isolation
def build_config_isolation_test_suite():
    """Build configuration isolation test suite
    
    Returns:
        CommandTestSuite instance
    """
    suite = CommandTestSuite("Configuration Isolation")
    
    # Add setup function
    async def setup(bot, db):
        """Set up test environment"""
        # Create test guilds with different configurations
        await db.guilds.insert_one({
            "_id": "guild:100000000000000000",
            "guild_id": "100000000000000000",
            "name": "Guild A",
            "settings": {
                "prefix": "!",
                "language": "en",
                "timezone": "UTC",
                "daily_credits": 100,
                "admin_role": "100000000000000001",
                "welcome_channel": "100000000000000002",
                "log_channel": "100000000000000003"
            }
        })
        
        await db.guilds.insert_one({
            "_id": "guild:200000000000000000",
            "guild_id": "200000000000000000",
            "name": "Guild B",
            "settings": {
                "prefix": "?",
                "language": "fr",
                "timezone": "Europe/Paris",
                "daily_credits": 200,
                "admin_role": "200000000000000001",
                "welcome_channel": "200000000000000002",
                "log_channel": "200000000000000003"
            }
        })
        
        # Create admin user for both guilds
        await db.users.insert_one({
            "_id": "user:300000000000000000",
            "user_id": "300000000000000000",
            "username": "Admin",
            "guilds": ["100000000000000000", "200000000000000000"],
            "permissions": {
                "admin": True
            }
        })
        
        # Create regular user for both guilds
        await db.users.insert_one({
            "_id": "user:400000000000000000",
            "user_id": "400000000000000000",
            "username": "User",
            "guilds": ["100000000000000000", "200000000000000000"],
            "permissions": {
                "admin": False
            }
        })
        
        # Mock settings command implementation
        async def mock_settings_command(ctx):
            # Get guild settings
            guild_doc = await db.guilds.find_one({"guild_id": ctx.guild.id})
            if not guild_doc:
                await ctx.send("Guild not found")
                return
            
            settings = guild_doc.get("settings", {})
            
            # Sub-command
            subcommand = ctx.options.get("subcommand", "view")
            
            if subcommand == "view":
                # View settings
                settings_text = "\n".join([f"{k}: {v}" for k, v in settings.items()])
                await ctx.send(f"Settings for {ctx.guild.name}:\n{settings_text}")
            
            elif subcommand == "set":
                # Set a setting
                key = ctx.options.get("key")
                value = ctx.options.get("value")
                
                if not key or not value:
                    await ctx.send("Missing key or value")
                    return
                
                # Check if admin
                user_doc = await db.users.find_one({"user_id": ctx.user.id})
                if not user_doc or not user_doc.get("permissions", {}).get("admin", False):
                    await ctx.send("You need admin permissions to change settings")
                    return
                
                # Update setting
                await db.guilds.update_one(
                    {"guild_id": ctx.guild.id},
                    {
                        "$set": {
                            f"settings.{key}": value
                        }
                    }
                )
                
                await ctx.send(f"Setting {key} updated to {value} for {ctx.guild.name}")
            
            else:
                await ctx.send(f"Unknown subcommand: {subcommand}")
        
        # Mock get configuration helper function
        async def get_guild_config(guild_id, setting=None, default=None):
            """Get configuration for a guild"""
            guild_doc = await db.guilds.find_one({"guild_id": guild_id})
            if not guild_doc:
                return default
            
            settings = guild_doc.get("settings", {})
            
            if setting:
                return settings.get(setting, default)
            
            return settings
        
        # Mock language command implementation
        async def mock_language_command(ctx):
            # Get current language setting
            language = await get_guild_config(ctx.guild.id, "language", "en")
            
            # New language if provided
            new_language = ctx.options.get("language")
            
            if new_language:
                # Check if admin
                user_doc = await db.users.find_one({"user_id": ctx.user.id})
                if not user_doc or not user_doc.get("permissions", {}).get("admin", False):
                    await ctx.send("You need admin permissions to change language")
                    return
                
                # Update language
                await db.guilds.update_one(
                    {"guild_id": ctx.guild.id},
                    {
                        "$set": {
                            "settings.language": new_language
                        }
                    }
                )
                
                await ctx.send(f"Language updated to {new_language} for {ctx.guild.name}")
            else:
                # Just show current language
                await ctx.send(f"Current language for {ctx.guild.name} is {language}")
        
        # Register commands in bot mock
        settings_command = MagicMock()
        settings_command.name = "settings"
        settings_command._invoke = AsyncMock(side_effect=mock_settings_command)
        
        language_command = MagicMock()
        language_command.name = "language"
        language_command._invoke = AsyncMock(side_effect=mock_language_command)
        
        # Add to bot's application commands
        bot.application_commands = [
            settings_command,
            language_command
        ]
        
        # Add helper to bot
        bot.get_guild_config = get_guild_config
    
    suite.add_setup(setup)
    
    # Add teardown function
    async def teardown(bot, db):
        """Clean up test environment"""
        await db.guilds.delete_many({})
        await db.users.delete_many({})
    
    suite.add_teardown(teardown)
    
    # Test cases
    
    # 1. Test viewing settings in Guild A
    suite.add_test(create_slash_command_test(
        command_name="settings",
        guild_id="100000000000000000",  # Guild A
        user_id="300000000000000000",
        options={"subcommand": "view"},
        validators=[
            ResponseValidator(
                content_contains=["Settings for Guild A", "prefix: !", "language: en", "daily_credits: 100"]
            )
        ]
    ))
    
    # 2. Test viewing settings in Guild B
    suite.add_test(create_slash_command_test(
        command_name="settings",
        guild_id="200000000000000000",  # Guild B
        user_id="300000000000000000",
        options={"subcommand": "view"},
        validators=[
            ResponseValidator(
                content_contains=["Settings for Guild B", "prefix: ?", "language: fr", "daily_credits: 200"]
            )
        ]
    ))
    
    # 3. Test changing a setting in Guild A as admin
    suite.add_test(create_slash_command_test(
        command_name="settings",
        guild_id="100000000000000000",  # Guild A
        user_id="300000000000000000",  # Admin user
        options={"subcommand": "set", "key": "daily_credits", "value": "150"},
        validators=[
            ResponseValidator(
                content_contains=["Setting daily_credits updated to 150 for Guild A"]
            ),
            # Verify setting was updated in Guild A only
            GuildIsolationValidator(
                collection="guilds",
                guild_id_field="guild_id",
                query={"settings.daily_credits": "150"},
                expected_count=1
            )
        ]
    ))
    
    # 4. Verify setting didn't change in Guild B
    suite.add_test(create_slash_command_test(
        command_name="settings",
        guild_id="200000000000000000",  # Guild B
        user_id="300000000000000000",
        options={"subcommand": "view"},
        validators=[
            ResponseValidator(
                content_contains=["daily_credits: 200"]  # Still 200, not 150
            )
        ]
    ))
    
    # 5. Test changing a setting as regular user (should fail)
    suite.add_test(create_slash_command_test(
        command_name="settings",
        guild_id="100000000000000000",  # Guild A
        user_id="400000000000000000",  # Regular user
        options={"subcommand": "set", "key": "daily_credits", "value": "300"},
        validators=[
            ResponseValidator(
                content_contains=["need admin permissions"]
            )
        ]
    ))
    
    # 6. Test language command in Guild A
    suite.add_test(create_slash_command_test(
        command_name="language",
        guild_id="100000000000000000",  # Guild A
        user_id="300000000000000000",
        validators=[
            ResponseValidator(
                content_contains=["Current language for Guild A is en"]
            )
        ]
    ))
    
    # 7. Test changing language in Guild B
    suite.add_test(create_slash_command_test(
        command_name="language",
        guild_id="200000000000000000",  # Guild B
        user_id="300000000000000000",  # Admin user
        options={"language": "es"},
        validators=[
            ResponseValidator(
                content_contains=["Language updated to es for Guild B"]
            ),
            # Verify language was updated in Guild B only
            GuildIsolationValidator(
                collection="guilds",
                guild_id_field="guild_id",
                query={"settings.language": "es"},
                expected_count=1
            )
        ]
    ))
    
    # 8. Verify language didn't change in Guild A
    suite.add_test(create_slash_command_test(
        command_name="language",
        guild_id="100000000000000000",  # Guild A
        user_id="300000000000000000",
        validators=[
            ResponseValidator(
                content_contains=["Current language for Guild A is en"]  # Still en, not es
            )
        ]
    ))
    
    return suite

# Run multi-guild tests
async def run_multi_guild_tests():
    """Run all multi-guild tests"""
    logger.info("Setting up test environment")
    
    # Set up database
    client, db = await setup_test_database()
    
    # Create mock bot
    bot = MagicMock()
    bot.db = db
    bot.application_commands = []
    
    # Create test suites
    canvas_suite = build_canvas_isolation_test_suite()
    config_suite = build_config_isolation_test_suite()
    
    # Run the suites
    logger.info("Running multi-guild tests")
    results = await run_tests([canvas_suite, config_suite], bot, db)
    
    logger.info("Tests complete")
    
    # Print detailed results
    for suite_name, suite_results in results.items():
        print(f"\n=== {suite_name} ===")
        
        passed = sum(1 for r in suite_results if r.success)
        total = len(suite_results)
        
        print(f"Passed: {passed}/{total} ({passed/total:.1%})")
        
        if passed < total:
            print("\nFailed tests:")
            for result in suite_results:
                if not result.success:
                    print(f" - {result.command_name}")
                    if result.exception:
                        print(f"   Exception: {type(result.exception).__name__}: {result.exception}")
                    for vr in result.validation_results:
                        if not vr["passed"]:
                            print(f"   Failed validation: {vr['validator']}")
                            print(f"     {vr['message']}")

if __name__ == "__main__":
    asyncio.run(run_multi_guild_tests())