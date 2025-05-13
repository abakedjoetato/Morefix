"""
Error Handling Test Suite for Tower of Temptation PvP Statistics Bot

This module provides test cases for error handling:
1. Command error capturing
2. Error telemetry
3. User feedback
4. Debug commands

The suite verifies that error handling works correctly
and provides useful information to users and administrators.
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
    """Create error handling test suite
    
    Returns:
        CommandTestSuite instance
    """
    suite = CommandTestSuite("Error Handling")
    
    # Add setup function
    async def setup(bot, db):
        """Set up test environment"""
        # Create error records
        await db.errors.insert_many([
            {
                "_id": "error:1",
                "id": "error1",
                "timestamp": datetime.datetime.now() - datetime.timedelta(hours=1),
                "category": "command",
                "error_type": "CommandInvokeError",
                "error_message": "Test error message",
                "fingerprint": "command:test:1",
                "occurrence_count": 5,
                "normalized_message": "Test error message",
                "traceback": "Traceback (most recent call last):\n  File \"test.py\", line 1\n    raise Exception(\"Test error message\")",
                "context": {
                    "guild_id": "100000000000000000",
                    "user_id": "200000000000000000",
                    "command": "test_command"
                },
                "first_seen": datetime.datetime.now() - datetime.timedelta(days=1),
                "last_seen": datetime.datetime.now() - datetime.timedelta(hours=1)
            },
            {
                "_id": "error:2",
                "id": "error2",
                "timestamp": datetime.datetime.now() - datetime.timedelta(hours=2),
                "category": "sftp",
                "error_type": "SFTPError",
                "error_message": "Connection failed",
                "fingerprint": "sftp:connection:1",
                "occurrence_count": 3,
                "normalized_message": "Connection failed",
                "traceback": "Traceback (most recent call last):\n  File \"sftp.py\", line 1\n    raise SFTPError(\"Connection failed\")",
                "context": {
                    "guild_id": "100000000000000000",
                    "sftp_host": "test.example.com"
                },
                "first_seen": datetime.datetime.now() - datetime.timedelta(days=2),
                "last_seen": datetime.datetime.now() - datetime.timedelta(hours=2)
            }
        ])
        
        # Create admin user
        await db.guilds.insert_one({
            "_id": "guild:100000000000000000",
            "guild_id": "100000000000000000",
            "settings": {
                "admin_users": ["200000000000000000"]
            }
        })
        
        # Mock error telemetry
        class MockErrorTelemetry:
            @classmethod
            async def track_error(cls, error, context=None, category=None, flush=False):
                return "error_id_123"
            
            @classmethod
            async def get_error_id(cls, error):
                return "error_id_123"
            
            @classmethod
            async def get_error_stats(cls, days=7):
                return {
                    "total_errors": 10,
                    "categories": [
                        {"category": "command", "count": 5},
                        {"category": "sftp", "count": 3},
                        {"category": "database", "count": 2}
                    ],
                    "most_frequent": [
                        {"error_type": "CommandInvokeError", "count": 5, "message": "Test error message", "fingerprint": "command:test:1"},
                        {"error_type": "SFTPError", "count": 3, "message": "Connection failed", "fingerprint": "sftp:connection:1"}
                    ]
                }
            
            @classmethod
            def is_enabled(cls):
                return True
            
            @classmethod
            async def get_error_by_id(cls, error_id):
                if error_id == "error1":
                    return {
                        "id": "error1",
                        "category": "command",
                        "error_type": "CommandInvokeError",
                        "error_message": "Test error message",
                        "traceback": "Traceback (most recent call last):\n  File \"test.py\", line 1\n    raise Exception(\"Test error message\")",
                        "occurrence_count": 5
                    }
                return None
        
        # Add to bot
        bot.ErrorTelemetry = MockErrorTelemetry
    
    suite.add_setup(setup)
    
    # Add teardown function
    async def teardown(bot, db):
        """Clean up test environment"""
        # Clear error records
        await db.errors.delete_many({})
        await db.guilds.delete_many({"guild_id": "100000000000000000"})
    
    suite.add_teardown(teardown)
    
    # Test cases
    
    # 1. Test /debug command
    suite.add_test(create_slash_command_test(
        command_name="debug",
        guild_id="100000000000000000",
        user_id="200000000000000000",  # Admin user
        options={"show_recent": True},
        validators=[
            ResponseValidator(
                embed_title="Error Debug Information",
                content_contains=["command", "sftp"]
            )
        ]
    ))
    
    # 2. Test /debug command with specific error ID
    suite.add_test(create_slash_command_test(
        command_name="debug",
        guild_id="100000000000000000",
        user_id="200000000000000000",  # Admin user
        options={"error_id": "error1"},
        validators=[
            ResponseValidator(
                embed_title="Error Details",
                content_contains=["CommandInvokeError", "Test error message"]
            )
        ]
    ))
    
    # 3. Test /debug command as non-admin (should fail)
    suite.add_test(create_slash_command_test(
        command_name="debug",
        guild_id="100000000000000000",
        user_id="300000000000000000",  # Non-admin user
        options={"show_recent": True},
        validators=[
            ResponseValidator(
                embed_title="Error",
                content_contains=["permission", "administrator"]
            )
        ]
    ))
    
    # 4. Test /error_guide command for SFTP errors
    suite.add_test(create_slash_command_test(
        command_name="error_guide",
        guild_id="100000000000000000",
        options={"error_type": "sftp"},
        validators=[
            ResponseValidator(
                embed_title="SFTP Error Resolution Guide",
                content_contains=["connection", "credentials"]
            )
        ]
    ))
    
    # 5. Test /error_guide command for command errors
    suite.add_test(create_slash_command_test(
        command_name="error_guide",
        guild_id="100000000000000000",
        options={"error_type": "command"},
        validators=[
            ResponseValidator(
                embed_title="Command Error Resolution Guide",
                content_contains=["command", "syntax"]
            )
        ]
    ))
    
    # 6. Test /telemetry command to enable telemetry
    suite.add_test(create_slash_command_test(
        command_name="telemetry",
        guild_id="100000000000000000",
        user_id="200000000000000000",  # Admin user
        options={"enable": True},
        validators=[
            ResponseValidator(
                embed_title="Error Telemetry",
                content_contains=["enabled", "tracking"]
            )
        ]
    ))
    
    # 7. Test /telemetry command to disable telemetry
    suite.add_test(create_slash_command_test(
        command_name="telemetry",
        guild_id="100000000000000000",
        user_id="200000000000000000",  # Admin user
        options={"enable": False},
        validators=[
            ResponseValidator(
                embed_title="Error Telemetry",
                content_contains=["disabled", "no longer"]
            )
        ]
    ))
    
    return suite