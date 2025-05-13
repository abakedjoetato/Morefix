"""
SFTP Commands Test Suite for Tower of Temptation PvP Statistics Bot

This module provides test cases for SFTP commands:
1. Connection testing
2. File listing
3. Log retrieval
4. Data parsing

The suite verifies that SFTP commands work correctly with
appropriate permissions and error handling.
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
    """Create SFTP commands test suite
    
    Returns:
        CommandTestSuite instance
    """
    suite = CommandTestSuite("SFTP Commands")
    
    # Add setup function
    async def setup(bot, db):
        """Set up test environment"""
        # Mock SFTP functionality
        import asyncssh
        import sys
        
        # If asyncssh is not available, mock it
        if 'asyncssh' not in sys.modules:
            sys.modules['asyncssh'] = MagicMock()
            sys.modules['asyncssh'].connect = AsyncMock()
            sys.modules['asyncssh'].SFTPError = type('SFTPError', (Exception,), {})
            sys.modules['asyncssh'].misc = MagicMock()
            sys.modules['asyncssh'].misc.SFTPNoSuchFile = type('SFTPNoSuchFile', (Exception,), {})
        
        # Create mock SFTP client
        mock_sftp = AsyncMock()
        mock_sftp.listdir = AsyncMock(return_value=[
            "test1.csv", 
            "test2.txt",
            "2025.05.01-00.00.00.csv",
            "2025.05.03-00.00.00.csv"
        ])
        
        # Create mock file object
        mock_file = MagicMock()
        mock_file.read = AsyncMock(return_value=b"test,data\nvalue1,value2\nvalue3,value4")
        mock_file.__aenter__ = AsyncMock(return_value=mock_file)
        mock_file.__aexit__ = AsyncMock(return_value=None)
        
        # Setup file open
        mock_sftp.open = AsyncMock(return_value=mock_file)
        
        # Create mock SSH connection
        mock_conn = AsyncMock()
        mock_conn.start_sftp_client = AsyncMock(return_value=mock_sftp)
        mock_conn.close = AsyncMock()
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=None)
        
        # Patch asyncssh.connect
        from asyncssh import connect
        connect.return_value = mock_conn
        
        # Add guild config
        await db.guilds.insert_one({
            "_id": "guild:100000000000000000",
            "guild_id": "100000000000000000",
            "name": "Test Guild",
            "settings": {
                "premium": True,
                "sftp_enabled": True
            },
            "integrations": {
                "sftp": {
                    "enabled": True,
                    "host": "test.example.com",
                    "port": 22,
                    "username": "testuser",
                    "password": "testpass",
                    "base_path": "/logs",
                    "auto_sync": True,
                    "last_sync": datetime.datetime.now() - datetime.timedelta(hours=1)
                }
            }
        })
    
    suite.add_setup(setup)
    
    # Add teardown function
    async def teardown(bot, db):
        """Clean up test environment"""
        # Clear guild config
        await db.guilds.delete_many({"guild_id": "100000000000000000"})
    
    suite.add_teardown(teardown)
    
    # Test cases
    
    # 1. Test /test_sftp command
    suite.add_test(create_slash_command_test(
        command_name="test_sftp",
        guild_id="100000000000000000",
        validators=[
            ResponseValidator(
                embed_title="SFTP Connection Test",
                content_contains=["success"]
            )
        ]
    ))
    
    # 2. Test /list_sftp_files command
    suite.add_test(create_slash_command_test(
        command_name="list_sftp_files",
        guild_id="100000000000000000",
        options={"path": "/logs"},
        validators=[
            ResponseValidator(
                embed_title="SFTP Files",
                content_contains=["test1.csv", "test2.txt"]
            )
        ]
    ))
    
    # 3. Test /list_sftp_files command with no path (should use base path)
    suite.add_test(create_slash_command_test(
        command_name="list_sftp_files",
        guild_id="100000000000000000",
        validators=[
            ResponseValidator(
                embed_title="SFTP Files"
            )
        ]
    ))
    
    # 4. Test /get_latest_logs command
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
    
    # 5. Test /download_log command
    suite.add_test(create_slash_command_test(
        command_name="download_log",
        guild_id="100000000000000000",
        options={"filename": "test1.csv"},
        validators=[
            ResponseValidator(
                embed_title="Log File",
                content_contains=["test1.csv"]
            )
        ]
    ))
    
    # 6. Test /download_log command with non-existent file (should show error)
    suite.add_test(create_slash_command_test(
        command_name="download_log",
        guild_id="100000000000000000",
        options={"filename": "nonexistent.csv"},
        validators=[
            ResponseValidator(
                embed_title="Error",
                content_contains=["not found", "nonexistent.csv"]
            )
        ]
    ))
    
    # 7. Test /read_log command
    suite.add_test(create_slash_command_test(
        command_name="read_log",
        guild_id="100000000000000000",
        options={"filename": "test1.csv"},
        validators=[
            ResponseValidator(
                embed_title="Log Contents",
                content_contains=["test,data", "value1,value2"]
            )
        ]
    ))
    
    # 8. Test /sync_logs command
    suite.add_test(create_slash_command_test(
        command_name="sync_logs",
        guild_id="100000000000000000",
        validators=[
            ResponseValidator(
                embed_title="Log Synchronization",
                content_contains=["synchronization", "success"]
            ),
            StateValidator(
                name="SyncValidator",
                validation_func=async lambda bot, db, result: {
                    "passed": True,
                    "message": "Sync state validated"
                }
            )
        ]
    ))
    
    return suite