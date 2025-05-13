#!/usr/bin/env python3
"""
Test Runner for Tower of Temptation PvP Statistics Bot

This module provides a command-line interface for running tests:
1. Command tests
2. Unit tests
3. Integration tests

Run with: python -m tests.run_tests [OPTIONS]
"""
import os
import sys
import argparse
import asyncio
import logging
import datetime
import importlib
import json
from typing import Dict, List, Any, Optional, Union

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import test modules
from tests.command_tester import (
    CommandTestSuite, CommandValidator, ResponseValidator, ExceptionValidator,
    create_slash_command_test, create_prefix_command_test
)
from tests.test_fixtures import setup_test_database

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("test_runner")

# Import test suites
def import_test_suite(suite_name):
    """Dynamically import a test suite module
    
    Args:
        suite_name: Name of the test suite module
    
    Returns:
        Imported module or None
    """
    try:
        module_path = f"tests.test_suites.{suite_name}"
        return importlib.import_module(module_path)
    except (ImportError, ModuleNotFoundError) as e:
        logger.error(f"Failed to import test suite {suite_name}: {e}")
        return None

# Define test suites
def build_sftp_test_suite():
    """Build SFTP command test suite
    
    Returns:
        CommandTestSuite
    """
    suite = CommandTestSuite("SFTP Commands")
    
    # Add setup function
    async def setup_sftp_mocks(bot, db):
        """Set up SFTP mocks for testing"""
        from unittest.mock import AsyncMock, patch, MagicMock
        import asyncssh
        
        # Mock SFTP connection
        mock_sftp = AsyncMock()
        mock_sftp.listdir = AsyncMock(return_value=[
            "test.csv", 
            "logs.txt", 
            "2025.05.01-00.00.00.csv",
            "2025.05.03-00.00.00.csv"
        ])
        mock_sftp.open = AsyncMock()
        mock_sftp.getfo = AsyncMock()
        mock_sftp.get = AsyncMock()
        
        # Mock SSH connection
        mock_conn = AsyncMock()
        mock_conn.start_sftp_client = AsyncMock(return_value=mock_sftp)
        mock_conn.close = AsyncMock()
        
        # Patch asyncssh.connect
        patcher = patch('asyncssh.connect', AsyncMock(return_value=mock_conn))
        patcher.start()
        
        # Save references for teardown
        bot._test_patchers = getattr(bot, '_test_patchers', []) + [patcher]
        
        # Add test guild config with SFTP settings
        await db.guilds.insert_one({
            "_id": f"guild:100000000000000000",
            "guild_id": "100000000000000000",
            "name": "Test Guild",
            "settings": {
                "premium": True
            },
            "integrations": {
                "sftp": {
                    "enabled": True,
                    "host": "test.example.com",
                    "port": 22,
                    "username": "testuser",
                    "password": "testpass",
                    "base_path": "/logs",
                    "auto_sync": True
                }
            }
        })
    
    suite.add_setup(setup_sftp_mocks)
    
    # Add teardown function
    async def teardown_sftp_mocks(bot, db):
        """Remove SFTP mocks"""
        # Remove patchers
        for patcher in getattr(bot, '_test_patchers', []):
            patcher.stop()
        
        # Clear test data
        await db.guilds.delete_many({"guild_id": "100000000000000000"})
    
    suite.add_teardown(teardown_sftp_mocks)
    
    # Test /test_sftp command
    suite.add_test(create_slash_command_test(
        command_name="test_sftp",
        guild_id="100000000000000000",
        validators=[
            ResponseValidator(
                embed_title="SFTP Connection Test",
                content_contains=["Successfully connected"]
            )
        ]
    ))
    
    # Test /list_sftp_files command
    suite.add_test(create_slash_command_test(
        command_name="list_sftp_files",
        guild_id="100000000000000000",
        options={"path": "/logs"},
        validators=[
            ResponseValidator(
                embed_title="SFTP Files",
                content_contains=["test.csv", "logs.txt"]
            )
        ]
    ))
    
    # Test /get_latest_logs command
    suite.add_test(create_slash_command_test(
        command_name="get_latest_logs",
        guild_id="100000000000000000",
        validators=[
            ResponseValidator(
                embed_title="Latest Logs",
                content_contains=["2025.05.03-00.00.00.csv"]
            )
        ]
    ))
    
    return suite

def build_error_handling_test_suite():
    """Build error handling test suite
    
    Returns:
        CommandTestSuite
    """
    suite = CommandTestSuite("Error Handling")
    
    # Add setup function
    async def setup_error_mocks(bot, db):
        """Set up error handling mocks for testing"""
        from unittest.mock import AsyncMock, patch, MagicMock
        
        # Create mock errors collection
        await db.errors.insert_many([
            {
                "_id": f"error:1",
                "id": "error1",
                "timestamp": datetime.datetime.now() - datetime.timedelta(hours=1),
                "category": "command",
                "error_type": "CommandInvokeError",
                "error_message": "Test error message",
                "fingerprint": "command:test:1",
                "occurrence_count": 5,
                "guild_id": "100000000000000000"
            },
            {
                "_id": f"error:2",
                "id": "error2",
                "timestamp": datetime.datetime.now() - datetime.timedelta(hours=2),
                "category": "sftp",
                "error_type": "SFTPError",
                "error_message": "Connection failed",
                "fingerprint": "sftp:connection:1",
                "occurrence_count": 3,
                "guild_id": "100000000000000000"
            }
        ])
    
    suite.add_setup(setup_error_mocks)
    
    # Add teardown function
    async def teardown_error_mocks(bot, db):
        """Clean up error mocks"""
        await db.errors.delete_many({})
    
    suite.add_teardown(teardown_error_mocks)
    
    # Test /debug command
    suite.add_test(create_slash_command_test(
        command_name="debug",
        guild_id="100000000000000000",
        options={"show_recent": True},
        validators=[
            ResponseValidator(
                embed_title="Error Debug Information",
                content_contains=["errors found"]
            )
        ]
    ))
    
    # Test /error_guide command
    suite.add_test(create_slash_command_test(
        command_name="error_guide",
        guild_id="100000000000000000",
        options={"error_type": "sftp"},
        validators=[
            ResponseValidator(
                embed_title="SFTP Error Resolution Guide",
                content_contains=["troubleshoot"]
            )
        ]
    ))
    
    return suite

def build_canvas_test_suite():
    """Build canvas command test suite
    
    Returns:
        CommandTestSuite
    """
    suite = CommandTestSuite("Canvas Commands")
    
    # Add setup function
    async def setup_canvas_mocks(bot, db):
        """Set up canvas mocks for testing"""
        # Create test canvas data
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
                    "user_id": "200000000000000000",
                    "timestamp": datetime.datetime.now() - datetime.timedelta(hours=2)
                }
            }
        })
        
        # Create test guild with canvas enabled
        await db.guilds.insert_one({
            "_id": "guild:100000000000000000",
            "guild_id": "100000000000000000",
            "settings": {
                "canvas_enabled": True,
                "canvas_size": 32
            }
        })
    
    suite.add_setup(setup_canvas_mocks)
    
    # Add teardown function
    async def teardown_canvas_mocks(bot, db):
        """Clean up canvas mocks"""
        await db.canvas.delete_many({})
        await db.guilds.delete_many({"guild_id": "100000000000000000"})
    
    suite.add_teardown(teardown_canvas_mocks)
    
    # Test /pixel command
    suite.add_test(create_slash_command_test(
        command_name="pixel",
        guild_id="100000000000000000",
        options={"x": 15, "y": 15, "color": "#0000FF"},
        validators=[
            ResponseValidator(
                content_contains=["placed", "pixel"]
            )
        ]
    ))
    
    # Test /canvas command
    suite.add_test(create_slash_command_test(
        command_name="canvas",
        guild_id="100000000000000000",
        validators=[
            ResponseValidator(
                content_contains=["canvas"]
            )
        ]
    ))
    
    return suite

# Run tests
async def run_all_tests(args):
    """Run all test suites
    
    Args:
        args: Command-line arguments
    """
    # Set up test environment
    client, db = await setup_test_database()
    
    # Create dummy bot instance for testing
    from unittest.mock import MagicMock, AsyncMock
    bot = MagicMock()
    bot.application_commands = []
    bot.cogs = {}
    bot.get_command = MagicMock(return_value=None)
    bot.invoke = AsyncMock()
    bot.process_component = AsyncMock()
    bot.db = db
    
    # Build test suites
    suites = []
    
    if args.all or args.sftp:
        suites.append(build_sftp_test_suite())
    
    if args.all or args.error:
        suites.append(build_error_handling_test_suite())
    
    if args.all or args.canvas:
        suites.append(build_canvas_test_suite())
    
    # Run dynamic test suites
    if args.suite:
        for suite_name in args.suite:
            module = import_test_suite(suite_name)
            if module and hasattr(module, 'create_test_suite'):
                suite = module.create_test_suite()
                suites.append(suite)
    
    # Run the suites
    from tests.command_tester import run_tests
    results = await run_tests(suites, bot, db)
    
    # Save results if requested
    if args.output:
        output_dir = os.path.dirname(args.output)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        with open(args.output, 'w') as f:
            json.dump({
                "timestamp": datetime.datetime.now().isoformat(),
                "suites": {
                    name: [r.to_dict() for r in results]
                    for name, results in results.items()
                }
            }, f, indent=2)
        
        logger.info(f"Test results saved to {args.output}")
    
    return results

# Command-line interface
def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Run bot tests")
    parser.add_argument('--all', action='store_true', help='Run all tests')
    parser.add_argument('--sftp', action='store_true', help='Run SFTP tests')
    parser.add_argument('--error', action='store_true', help='Run error handling tests')
    parser.add_argument('--canvas', action='store_true', help='Run canvas tests')
    parser.add_argument('--suite', nargs='+', help='Run specific test suite modules')
    parser.add_argument('--output', help='Save test results to file')
    
    args = parser.parse_args()
    
    # Run tests
    asyncio.run(run_all_tests(args))

if __name__ == '__main__':
    main()