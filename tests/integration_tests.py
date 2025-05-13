"""
Integration Tests for Tower of Temptation PvP Statistics Bot

This module provides comprehensive integration tests:
1. End-to-end command execution
2. Database interactions
3. Cross-component functionality

These tests verify that components work correctly together
and maintain expected state across operations.
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
logger = logging.getLogger("integration_tests")

# Database integration tests
class DatabaseValidator(CommandValidator):
    """Validates database state after command execution"""
    
    def __init__(self, collection, query, expected_result=None, field_validators=None):
        """Initialize database validator
        
        Args:
            collection: Database collection to query
            query: MongoDB query to execute
            expected_result: Expected result document (or None to just check existence)
            field_validators: Dictionary of field name to validation function
        """
        super().__init__(name="DatabaseValidator")
        self.collection = collection
        self.query = query
        self.expected_result = expected_result
        self.field_validators = field_validators or {}
    
    async def validate(self, result, test_case):
        """Validate database state
        
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
            document = await collection.find_one(self.query)
            
            # Check if document exists
            if document is None:
                return {
                    "passed": False,
                    "message": f"Document not found in {self.collection} with query {self.query}"
                }
            
            # If expected result provided, check fields
            if self.expected_result:
                for key, value in self.expected_result.items():
                    if key not in document:
                        return {
                            "passed": False,
                            "message": f"Field {key} not found in document"
                        }
                    
                    if document[key] != value:
                        return {
                            "passed": False,
                            "message": f"Field {key} has value {document[key]}, expected {value}"
                        }
            
            # Apply field validators
            for field, validator_func in self.field_validators.items():
                if field not in document:
                    return {
                        "passed": False,
                        "message": f"Field {field} not found in document for validation"
                    }
                
                # Get validation result
                valid = validator_func(document[field])
                if not valid:
                    return {
                        "passed": False,
                        "message": f"Field {field} with value {document[field]} failed validation"
                    }
            
            # All validations passed
            return {
                "passed": True,
                "message": None
            }
        
        except Exception as e:
            return {
                "passed": False,
                "message": f"Database validation error: {type(e).__name__}: {e}"
            }

# Test suite for pixel placement and canvas interaction
def build_canvas_integration_test_suite():
    """Build canvas integration test suite
    
    Returns:
        CommandTestSuite instance
    """
    suite = CommandTestSuite("Canvas Integration")
    
    # Add setup function
    async def setup(bot, db):
        """Set up test environment"""
        # Create test guild
        await db.guilds.insert_one({
            "_id": "guild:100000000000000000",
            "guild_id": "100000000000000000",
            "name": "Test Guild",
            "settings": {
                "canvas_enabled": True,
                "canvas_size": 32,
                "canvas_default_color": "#FFFFFF"
            }
        })
        
        # Create test users
        await db.users.insert_one({
            "_id": "user:200000000000000000",
            "user_id": "200000000000000000",
            "username": "TestUser1",
            "guilds": ["100000000000000000"],
            "inventory": {
                "credits": 500,
                "colors": ["#FF0000", "#00FF00", "#0000FF"]
            }
        })
        
        await db.users.insert_one({
            "_id": "user:300000000000000000",
            "user_id": "300000000000000000",
            "username": "TestUser2",
            "guilds": ["100000000000000000"],
            "inventory": {
                "credits": 300,
                "colors": ["#FFFF00", "#00FFFF"]
            }
        })
        
        # Create initial canvas data
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
                }
            },
            "stats": {
                "total_pixels_placed": 1,
                "unique_users": 1,
                "last_update": datetime.datetime.now() - datetime.timedelta(hours=1)
            }
        })
        
        # Mock canvas image generation
        async def mock_generate_canvas_image(guild_id, **kwargs):
            return MagicMock()
        
        bot.generate_canvas_image = AsyncMock(side_effect=mock_generate_canvas_image)
        
        # Mock command implementations
        async def mock_canvas_command(ctx):
            # Return canvas image
            await ctx.send(file=await bot.generate_canvas_image(ctx.guild.id))
        
        async def mock_pixel_command(ctx):
            # Place a pixel
            x = ctx.options.get("x", 0)
            y = ctx.options.get("y", 0)
            color = ctx.options.get("color", "#000000")
            
            # Check if coordinates are valid
            if x < 0 or x >= 32 or y < 0 or y >= 32:
                await ctx.send("Invalid coordinates")
                return
            
            # Update database
            await db.canvas.update_one(
                {"guild_id": ctx.guild.id},
                {
                    "$set": {
                        f"pixels.{x},{y}": {
                            "color": color,
                            "user_id": ctx.user.id,
                            "timestamp": datetime.datetime.now()
                        },
                        "stats.last_update": datetime.datetime.now()
                    },
                    "$inc": {
                        "stats.total_pixels_placed": 1
                    }
                }
            )
            
            # Update user stats
            await db.users.update_one(
                {"user_id": ctx.user.id},
                {
                    "$inc": {
                        "stats.canvas_pixels_placed": 1
                    }
                },
                upsert=True
            )
            
            await ctx.send(f"Pixel placed at ({x}, {y}) with color {color}")
        
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
    
    # 1. Test pixel placement and verify database update
    suite.add_test(create_slash_command_test(
        command_name="pixel",
        guild_id="100000000000000000",
        user_id="200000000000000000",
        options={"x": 10, "y": 15, "color": "#FF0000"},
        validators=[
            ResponseValidator(
                content_contains=["Pixel placed", "10", "15", "#FF0000"]
            ),
            # Verify database was updated
            DatabaseValidator(
                collection="canvas",
                query={"guild_id": "100000000000000000"},
                field_validators={
                    "pixels": lambda pixels: "10,15" in pixels and pixels["10,15"]["color"] == "#FF0000",
                    "stats.total_pixels_placed": lambda count: count == 2  # Initial had 1
                }
            ),
            # Verify user stats were updated
            DatabaseValidator(
                collection="users",
                query={"user_id": "200000000000000000"},
                field_validators={
                    "stats.canvas_pixels_placed": lambda count: count == 1
                }
            )
        ]
    ))
    
    # 2. Test pixel overwrite by another user
    suite.add_test(create_slash_command_test(
        command_name="pixel",
        guild_id="100000000000000000",
        user_id="300000000000000000",  # Different user
        options={"x": 10, "y": 15, "color": "#00FFFF"},  # Same coordinates
        validators=[
            ResponseValidator(
                content_contains=["Pixel placed", "10", "15", "#00FFFF"]
            ),
            # Verify pixel was overwritten
            DatabaseValidator(
                collection="canvas",
                query={"guild_id": "100000000000000000"},
                field_validators={
                    "pixels": lambda pixels: pixels["10,15"]["color"] == "#00FFFF" and
                                           pixels["10,15"]["user_id"] == "300000000000000000",
                    "stats.total_pixels_placed": lambda count: count == 3  # Initial + 2 placements
                }
            )
        ]
    ))
    
    # 3. Test invalid coordinates
    suite.add_test(create_slash_command_test(
        command_name="pixel",
        guild_id="100000000000000000",
        user_id="200000000000000000",
        options={"x": 100, "y": 100, "color": "#FF0000"},  # Out of bounds
        validators=[
            ResponseValidator(
                content_contains=["Invalid coordinates"]
            ),
            # Verify total pixel count didn't change
            DatabaseValidator(
                collection="canvas",
                query={"guild_id": "100000000000000000"},
                field_validators={
                    "stats.total_pixels_placed": lambda count: count == 3  # Should be unchanged
                }
            )
        ]
    ))
    
    return suite

# Test suite for profile commands and inventory system
def build_profile_integration_test_suite():
    """Build profile integration test suite
    
    Returns:
        CommandTestSuite instance
    """
    suite = CommandTestSuite("Profile Integration")
    
    # Add setup function
    async def setup(bot, db):
        """Set up test environment"""
        # Create test guild
        await db.guilds.insert_one({
            "_id": "guild:100000000000000000",
            "guild_id": "100000000000000000",
            "name": "Test Guild",
            "settings": {
                "daily_credits": 100
            }
        })
        
        # Create test user
        await db.users.insert_one({
            "_id": "user:200000000000000000",
            "user_id": "200000000000000000",
            "username": "TestUser",
            "guilds": ["100000000000000000"],
            "stats": {
                "commands_used": 10,
                "canvas_pixels_placed": 5,
                "daily_streak": 2
            },
            "inventory": {
                "credits": 250,
                "colors": ["#FF0000", "#00FF00"],
                "items": [
                    {"id": "item1", "name": "Test Item", "quantity": 1}
                ],
                "last_daily": datetime.datetime.now() - datetime.timedelta(days=1)
            }
        })
        
        # Mock command implementations
        async def mock_profile_command(ctx):
            # Get user profile
            user_doc = await db.users.find_one({"user_id": ctx.user.id})
            if not user_doc:
                await ctx.send("User profile not found")
                return
            
            embed = MagicMock()
            embed.title = "User Profile"
            embed.description = f"Profile for {ctx.user.name}"
            embed.fields = [
                {"name": "Credits", "value": str(user_doc["inventory"]["credits"]), "inline": True},
                {"name": "Pixels Placed", "value": str(user_doc["stats"]["canvas_pixels_placed"]), "inline": True},
                {"name": "Daily Streak", "value": str(user_doc["stats"]["daily_streak"]), "inline": True}
            ]
            await ctx.send(embed=embed)
        
        async def mock_daily_command(ctx):
            # Get user profile
            user_doc = await db.users.find_one({"user_id": ctx.user.id})
            if not user_doc:
                await ctx.send("User profile not found")
                return
            
            # Get guild settings
            guild_doc = await db.guilds.find_one({"guild_id": ctx.guild.id})
            if not guild_doc:
                await ctx.send("Guild settings not found")
                return
            
            daily_credits = guild_doc["settings"].get("daily_credits", 100)
            
            # Check if daily already claimed
            last_daily = user_doc["inventory"].get("last_daily")
            now = datetime.datetime.now()
            
            if last_daily and (now - last_daily).total_seconds() < 86400:  # 24 hours
                # Already claimed
                next_daily = last_daily + datetime.timedelta(days=1)
                time_left = next_daily - now
                hours = int(time_left.total_seconds() / 3600)
                minutes = int((time_left.total_seconds() % 3600) / 60)
                
                await ctx.send(f"Daily already claimed. Next daily available in {hours}h {minutes}m")
                return
            
            # Update streak
            streak = user_doc["stats"].get("daily_streak", 0)
            
            if last_daily and (now - last_daily).total_seconds() < 172800:  # 48 hours
                # Continuous streak
                streak += 1
            else:
                # Streak reset
                streak = 1
            
            # Add bonus for streak
            bonus = min(streak * 10, 100)  # Cap at 100 bonus
            
            # Update database
            await db.users.update_one(
                {"user_id": ctx.user.id},
                {
                    "$set": {
                        "inventory.last_daily": now,
                        "stats.daily_streak": streak
                    },
                    "$inc": {
                        "inventory.credits": daily_credits + bonus
                    }
                }
            )
            
            await ctx.send(f"Daily claimed! You received {daily_credits} credits + {bonus} streak bonus! Current streak: {streak}")
        
        async def mock_inventory_command(ctx):
            # Get user profile
            user_doc = await db.users.find_one({"user_id": ctx.user.id})
            if not user_doc:
                await ctx.send("User profile not found")
                return
            
            inventory = user_doc.get("inventory", {})
            
            embed = MagicMock()
            embed.title = "Inventory"
            embed.description = f"Inventory for {ctx.user.name}"
            
            # Credits
            embed.fields = [
                {"name": "Credits", "value": str(inventory.get("credits", 0)), "inline": False}
            ]
            
            # Colors
            colors = inventory.get("colors", [])
            if colors:
                embed.fields.append({"name": "Colors", "value": ", ".join(colors), "inline": False})
            
            # Items
            items = inventory.get("items", [])
            if items:
                items_text = "\n".join([f"{item['name']} x{item['quantity']}" for item in items])
                embed.fields.append({"name": "Items", "value": items_text, "inline": False})
            
            await ctx.send(embed=embed)
        
        async def mock_buy_command(ctx):
            item_id = ctx.options.get("item", "")
            quantity = ctx.options.get("quantity", 1)
            
            # Item catalog
            items = {
                "color_red": {"name": "Red Color", "price": 100, "type": "color", "value": "#FF0000"},
                "color_blue": {"name": "Blue Color", "price": 100, "type": "color", "value": "#0000FF"},
                "color_green": {"name": "Green Color", "price": 100, "type": "color", "value": "#00FF00"},
                "boost": {"name": "XP Boost", "price": 200, "type": "item"}
            }
            
            if item_id not in items:
                await ctx.send(f"Item '{item_id}' not found in the shop")
                return
            
            item = items[item_id]
            total_price = item["price"] * quantity
            
            # Get user profile
            user_doc = await db.users.find_one({"user_id": ctx.user.id})
            if not user_doc:
                await ctx.send("User profile not found")
                return
            
            # Check if user has enough credits
            credits = user_doc.get("inventory", {}).get("credits", 0)
            if credits < total_price:
                await ctx.send(f"Not enough credits. You have {credits}, but need {total_price}")
                return
            
            # Process purchase
            if item["type"] == "color":
                # Add color to inventory if not already owned
                user_colors = user_doc.get("inventory", {}).get("colors", [])
                if item["value"] in user_colors:
                    await ctx.send(f"You already own this color")
                    return
                
                # Update database
                await db.users.update_one(
                    {"user_id": ctx.user.id},
                    {
                        "$push": {
                            "inventory.colors": item["value"]
                        },
                        "$inc": {
                            "inventory.credits": -total_price
                        }
                    }
                )
            elif item["type"] == "item":
                # Update database
                await db.users.update_one(
                    {"user_id": ctx.user.id},
                    {
                        "$inc": {
                            "inventory.credits": -total_price
                        }
                    }
                )
                
                # Check if item already exists in inventory
                item_in_inventory = False
                for inv_item in user_doc.get("inventory", {}).get("items", []):
                    if inv_item.get("id") == item_id:
                        item_in_inventory = True
                        # Update quantity
                        await db.users.update_one(
                            {"user_id": ctx.user.id, "inventory.items.id": item_id},
                            {
                                "$inc": {
                                    "inventory.items.$.quantity": quantity
                                }
                            }
                        )
                        break
                
                if not item_in_inventory:
                    # Add new item
                    await db.users.update_one(
                        {"user_id": ctx.user.id},
                        {
                            "$push": {
                                "inventory.items": {
                                    "id": item_id,
                                    "name": item["name"],
                                    "quantity": quantity
                                }
                            }
                        }
                    )
            
            await ctx.send(f"You purchased {quantity}x {item['name']} for {total_price} credits!")
        
        # Register commands in bot mock
        profile_command = MagicMock()
        profile_command.name = "profile"
        profile_command._invoke = AsyncMock(side_effect=mock_profile_command)
        
        daily_command = MagicMock()
        daily_command.name = "daily"
        daily_command._invoke = AsyncMock(side_effect=mock_daily_command)
        
        inventory_command = MagicMock()
        inventory_command.name = "inventory"
        inventory_command._invoke = AsyncMock(side_effect=mock_inventory_command)
        
        buy_command = MagicMock()
        buy_command.name = "buy"
        buy_command._invoke = AsyncMock(side_effect=mock_buy_command)
        
        # Add to bot's application commands
        bot.application_commands.extend([
            profile_command,
            daily_command,
            inventory_command,
            buy_command
        ])
    
    suite.add_setup(setup)
    
    # Add teardown function
    async def teardown(bot, db):
        """Clean up test environment"""
        await db.guilds.delete_many({})
        await db.users.delete_many({})
    
    suite.add_teardown(teardown)
    
    # Test cases
    
    # 1. Test daily command and verify credits
    suite.add_test(create_slash_command_test(
        command_name="daily",
        guild_id="100000000000000000",
        user_id="200000000000000000",
        validators=[
            ResponseValidator(
                content_contains=["Daily claimed", "100 credits", "streak bonus", "streak: 3"]
            ),
            # Verify user received credits and streak increased
            DatabaseValidator(
                collection="users",
                query={"user_id": "200000000000000000"},
                field_validators={
                    "inventory.credits": lambda credits: credits == 250 + 100 + 30,  # Initial + daily + streak bonus
                    "stats.daily_streak": lambda streak: streak == 3,
                    "inventory.last_daily": lambda date: isinstance(date, datetime.datetime)
                }
            )
        ]
    ))
    
    # 2. Test claiming daily twice (should fail)
    suite.add_test(create_slash_command_test(
        command_name="daily",
        guild_id="100000000000000000",
        user_id="200000000000000000",
        validators=[
            ResponseValidator(
                content_contains=["already claimed", "Next daily"]
            ),
            # Verify credits didn't change
            DatabaseValidator(
                collection="users",
                query={"user_id": "200000000000000000"},
                field_validators={
                    "inventory.credits": lambda credits: credits == 250 + 100 + 30,  # Should be unchanged
                    "stats.daily_streak": lambda streak: streak == 3  # Should be unchanged
                }
            )
        ]
    ))
    
    # 3. Test buying an item
    suite.add_test(create_slash_command_test(
        command_name="buy",
        guild_id="100000000000000000",
        user_id="200000000000000000",
        options={"item": "color_blue", "quantity": 1},
        validators=[
            ResponseValidator(
                content_contains=["purchased", "Blue Color", "100 credits"]
            ),
            # Verify credits deducted and item added
            DatabaseValidator(
                collection="users",
                query={"user_id": "200000000000000000"},
                field_validators={
                    "inventory.credits": lambda credits: credits == 250 + 100 + 30 - 100,  # Credits deducted
                    "inventory.colors": lambda colors: "#0000FF" in colors  # New color added
                }
            )
        ]
    ))
    
    # 4. Test buying same color again (should fail)
    suite.add_test(create_slash_command_test(
        command_name="buy",
        guild_id="100000000000000000",
        user_id="200000000000000000",
        options={"item": "color_blue", "quantity": 1},
        validators=[
            ResponseValidator(
                content_contains=["already own this color"]
            ),
            # Verify credits didn't change
            DatabaseValidator(
                collection="users",
                query={"user_id": "200000000000000000"},
                field_validators={
                    "inventory.credits": lambda credits: credits == 250 + 100 + 30 - 100  # Should be unchanged
                }
            )
        ]
    ))
    
    # 5. Test buying multiple items
    suite.add_test(create_slash_command_test(
        command_name="buy",
        guild_id="100000000000000000",
        user_id="200000000000000000",
        options={"item": "boost", "quantity": 2},
        validators=[
            ResponseValidator(
                content_contains=["purchased", "2x XP Boost", "400 credits"]
            ),
            # Verify credits deducted and item added
            DatabaseValidator(
                collection="users",
                query={"user_id": "200000000000000000"},
                field_validators={
                    "inventory.credits": lambda credits: credits == 250 + 100 + 30 - 100 - 400,  # More credits deducted
                    "inventory.items": lambda items: any(item["id"] == "boost" and item["quantity"] == 2 for item in items)
                }
            )
        ]
    ))
    
    # 6. Test inventory command
    suite.add_test(create_slash_command_test(
        command_name="inventory",
        guild_id="100000000000000000",
        user_id="200000000000000000",
        validators=[
            ResponseValidator(
                embed_title="Inventory",
                embed_field_names=["Credits", "Colors", "Items"]
            )
        ]
    ))
    
    return suite

# Run tests
async def run_integration_tests():
    """Run all integration tests"""
    logger.info("Setting up test environment")
    
    # Set up database
    client, db = await setup_test_database()
    
    # Create mock bot
    bot = MagicMock()
    bot.db = db
    bot.application_commands = []
    
    # Create test suites
    canvas_suite = build_canvas_integration_test_suite()
    profile_suite = build_profile_integration_test_suite()
    
    # Run the suites
    logger.info("Running integration tests")
    results = await run_tests([canvas_suite, profile_suite], bot, db)
    
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
    asyncio.run(run_integration_tests())