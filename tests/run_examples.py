#!/usr/bin/env python3
"""
Example Test Runner for Tower of Temptation PvP Statistics Bot

This script demonstrates how to use the test infrastructure
by running a few example tests.
"""
import os
import sys
import asyncio
import logging
from unittest.mock import MagicMock, AsyncMock

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import test modules
from tests.command_tester import (
    CommandTestSuite, CommandValidator, ResponseValidator, ExceptionValidator,
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
logger = logging.getLogger("example_test_runner")

# Create a simple test suite
def build_example_test_suite():
    """Build an example test suite
    
    Returns:
        CommandTestSuite
    """
    suite = CommandTestSuite("Example Tests")
    
    # Add setup function
    async def setup(bot, db):
        """Set up test environment"""
        logger.info("Setting up example test environment")
        
        # Create a mock command to test
        async def mock_ping_command(ctx):
            await ctx.send("Pong!")
        
        # Add command to bot
        bot.get_command.return_value = MagicMock(callback=mock_ping_command)
        
        # For slash commands
        mock_slash_command = MagicMock()
        mock_slash_command.name = "ping"
        mock_slash_command._invoke = AsyncMock(side_effect=mock_ping_command)
        bot.application_commands = [mock_slash_command]
        
        # Add guild and user to database
        await db.guilds.insert_one({
            "_id": "guild:100000000000000000",
            "guild_id": "100000000000000000",
            "name": "Test Guild",
            "settings": {
                "prefix": "!"
            }
        })
        
        await db.users.insert_one({
            "_id": "user:200000000000000000",
            "user_id": "200000000000000000",
            "username": "TestUser",
            "guilds": ["100000000000000000"]
        })
        
        logger.info("Example test environment setup complete")
    
    suite.add_setup(setup)
    
    # Add teardown function
    async def teardown(bot, db):
        """Clean up test environment"""
        logger.info("Cleaning up example test environment")
        await db.guilds.delete_many({})
        await db.users.delete_many({})
    
    suite.add_teardown(teardown)
    
    # Test a simple prefix command
    suite.add_test(create_prefix_command_test(
        command_name="ping",
        guild_id="100000000000000000",
        user_id="200000000000000000",
        validators=[
            ResponseValidator(
                expected_content="Pong!"
            )
        ]
    ))
    
    # Test the same command as a slash command
    suite.add_test(create_slash_command_test(
        command_name="ping",
        guild_id="100000000000000000",
        user_id="200000000000000000",
        validators=[
            ResponseValidator(
                expected_content="Pong!"
            )
        ]
    ))
    
    return suite

# Create an example test with expected failure
def build_failure_test_suite():
    """Build a test suite with expected failures
    
    Returns:
        CommandTestSuite
    """
    suite = CommandTestSuite("Failure Examples")
    
    # Add setup function
    async def setup(bot, db):
        """Set up test environment"""
        logger.info("Setting up failure test environment")
        
        # Create a mock command that raises an exception
        async def mock_failing_command(ctx):
            raise ValueError("This command always fails")
        
        # Add command to bot
        mock_command = MagicMock(callback=mock_failing_command)
        bot.get_command.return_value = mock_command
        
        # For slash commands
        mock_slash_command = MagicMock()
        mock_slash_command.name = "fail"
        mock_slash_command._invoke = AsyncMock(side_effect=mock_failing_command)
        bot.application_commands = [mock_slash_command]
    
    suite.add_setup(setup)
    
    # Test a command that fails
    suite.add_test(create_prefix_command_test(
        command_name="fail",
        validators=[
            # This validator expects the ValueError
            ExceptionValidator(
                expected_exception=ValueError,
                expected_message="always fails"
            )
        ]
    ))
    
    # Test a slash command that fails
    suite.add_test(create_slash_command_test(
        command_name="fail",
        validators=[
            # This validator expects the ValueError
            ExceptionValidator(
                expected_exception=ValueError,
                expected_message="always fails"
            )
        ]
    ))
    
    # Test with incorrect validation (this should fail)
    suite.add_test(create_prefix_command_test(
        command_name="fail",
        validators=[
            # This validator incorrectly expects a successful response
            ResponseValidator(
                expected_content="This should never be seen"
            )
        ]
    ))
    
    return suite

# Run the example tests
async def run_example_tests():
    """Run the example test suites"""
    logger.info("Setting up test environment")
    
    # Set up database
    client, db = await setup_test_database()
    
    # Create mock bot
    bot = MagicMock()
    bot.db = db
    
    # Create test suites
    example_suite = build_example_test_suite()
    failure_suite = build_failure_test_suite()
    
    # Run the suites
    logger.info("Running example tests")
    results = await run_tests([example_suite, failure_suite], bot, db)
    
    logger.info("Tests complete")
    
    # Print detailed results
    for suite_name, suite_results in results.items():
        print(f"\n=== {suite_name} ===")
        for result in suite_results:
            print(f"Test: {result.command_name}")
            print(f"Success: {result.success}")
            print(f"Time: {result.execution_time:.4f}s")
            
            if result.exception:
                print(f"Exception: {type(result.exception).__name__}: {result.exception}")
            
            if result.validation_results:
                print("Validation Results:")
                for vr in result.validation_results:
                    status = "PASSED" if vr["passed"] else "FAILED"
                    print(f" - {vr['validator']}: {status}")
                    if vr["message"]:
                        print(f"   Message: {vr['message']}")
            
            print()

# Main entry point
def main():
    """Main entry point"""
    logger.info("Starting example test runner")
    asyncio.run(run_example_tests())
    logger.info("Example test runner complete")

if __name__ == "__main__":
    main()