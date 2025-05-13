#!/usr/bin/env python3
"""
Integration Test Script for Tower of Temptation Discord Bot

This script performs comprehensive system integration testing:
1. Database connection and schema verification
2. SFTP system components
3. Command system registration
4. Error telemetry and handling
5. Backward compatibility layers

Run with: python integration_test.py
"""
import os
import sys
import asyncio
import logging
import datetime
import traceback
from typing import Dict, List, Any, Optional, Union, Set

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("integration_test.log")
    ]
)
logger = logging.getLogger("integration_test")

# Result tracking
TEST_RESULTS = {
    "passed": 0,
    "failed": 0,
    "skipped": 0,
    "errors": []
}

# Helper functions
async def run_test(test_name, test_func, *args, **kwargs):
    """Run a test function and log results
    
    Args:
        test_name: Name of the test
        test_func: Async function to run
        *args, **kwargs: Arguments to pass to test_func
    """
    logger.info(f"Running test: {test_name}")
    try:
        result = await test_func(*args, **kwargs)
        if result is True:
            logger.info(f"PASSED: {test_name}")
            TEST_RESULTS["passed"] += 1
        else:
            logger.error(f"FAILED: {test_name} - {result}")
            TEST_RESULTS["failed"] += 1
            TEST_RESULTS["errors"].append({
                "test": test_name,
                "error": result
            })
    except Exception as e:
        logger.error(f"ERROR: {test_name} - {e}")
        logger.error(traceback.format_exc())
        TEST_RESULTS["failed"] += 1
        TEST_RESULTS["errors"].append({
            "test": test_name,
            "error": str(e),
            "traceback": traceback.format_exc()
        })

# Database Tests
async def test_database_connection(db):
    """Test database connection
    
    Args:
        db: Database instance
        
    Returns:
        True if successful, error message otherwise
    """
    try:
        # Test basic connection
        result = await db.command("ping")
        if result.get("ok") != 1:
            return f"Database ping failed: {result}"
        
        # Test collections
        collections = await db.list_collection_names()
        required_collections = ["guilds", "users", "canvas", "errors", "settings"]
        
        for collection in required_collections:
            if collection not in collections:
                return f"Missing required collection: {collection}"
        
        # Check settings collection for version documents
        settings_count = await db.settings.count_documents({"_id": {"$regex": "^version:"}})
        if settings_count == 0:
            return "No version documents found in settings collection"
        
        return True
    except Exception as e:
        return f"Database connection error: {str(e)}"

async def test_data_migration(db):
    """Test data migration system
    
    Args:
        db: Database instance
        
    Returns:
        True if successful, error message otherwise
    """
    try:
        # Import migration system
        from utils.data_migration import get_migration_manager
        
        # Initialize migration manager
        migration_manager = await get_migration_manager(db)
        
        # Check migration needs
        analysis = await migration_manager.analyze_migration_needs()
        
        # Check that analysis contains expected collections
        expected_collections = ["guild_config", "user_profiles", "canvas_data", "stats", "errors"]
        for collection in expected_collections:
            if collection not in analysis:
                return f"Missing collection in migration analysis: {collection}"
        
        # Get a migration report
        report = await migration_manager.generate_migration_report()
        if not report or not isinstance(report, str) or len(report) < 100:
            return f"Invalid migration report: {report}"
        
        return True
    except Exception as e:
        return f"Data migration error: {str(e)}"

# SFTP Tests
async def test_sftp_connection_pool():
    """Test SFTP connection pool
    
    Returns:
        True if successful, error message otherwise
    """
    try:
        # Import SFTP modules
        from utils.sftp_connection_pool import SFTPConnectionPool
        from utils.sftp_exceptions import SFTPConnectionError
        
        # Mock guild config
        guild_id = "integration_test_guild"
        guild_config = {
            "host": "test.example.com",
            "port": 22,
            "username": "test",
            "password": "test",
            "base_path": "/test"
        }
        
        # Register mock connection
        SFTPConnectionPool.register_connection_config(guild_id, guild_config)
        
        # Check configuration retrieval
        config = SFTPConnectionPool.get_connection_config(guild_id)
        if not config or config.get("host") != "test.example.com":
            return f"Failed to retrieve connection config: {config}"
        
        # Test pool statistics
        stats = SFTPConnectionPool.get_pool_stats()
        if not isinstance(stats, dict):
            return f"Invalid pool stats: {stats}"
        
        # We're not testing actual connection since that would require real credentials
        # But we can test that the pool interface works properly
        
        return True
    except Exception as e:
        return f"SFTP connection pool error: {str(e)}"

async def test_sftp_helpers():
    """Test SFTP helper functions
    
    Returns:
        True if successful, error message otherwise
    """
    try:
        # Import SFTP helpers
        from utils.sftp_helpers import (
            parse_csv_content, format_datetime, 
            filter_csv_files, sort_csv_files_by_date
        )
        
        # Test datetime formatting
        now = datetime.datetime.now()
        formatted = format_datetime(now)
        if not formatted or not isinstance(formatted, str):
            return f"Invalid datetime formatting: {formatted}"
        
        # Test CSV parsing
        csv_content = "header1,header2\nvalue1,value2\nvalue3,value4"
        parsed = parse_csv_content(csv_content)
        if len(parsed) != 2 or parsed[0].get('header1') != 'value1':
            return f"Invalid CSV parsing: {parsed}"
        
        # Test CSV file filtering
        files = ["test.csv", "2025.05.01-00.00.00.csv", "2025.05.03-00.00.00.csv", "notes.txt"]
        filtered = filter_csv_files(files)
        if len(filtered) != 2 or "test.csv" in filtered:
            return f"Invalid CSV file filtering: {filtered}"
        
        # Test CSV file sorting
        sorted_files = sort_csv_files_by_date(filtered)
        if sorted_files[0] != "2025.05.03-00.00.00.csv":
            return f"Invalid CSV file sorting: {sorted_files}"
        
        return True
    except Exception as e:
        return f"SFTP helpers error: {str(e)}"

# Error Handling Tests
async def test_error_telemetry(db):
    """Test error telemetry system
    
    Args:
        db: Database instance
        
    Returns:
        True if successful, error message otherwise
    """
    try:
        # Import error telemetry
        from utils.error_telemetry import ErrorTelemetry
        
        # Initialize with database
        ErrorTelemetry(db)
        
        # Track a test error
        test_error = ValueError("Integration test error")
        error_id = await ErrorTelemetry.track_error(
            test_error,
            context={
                "test": "integration_test",
                "source": "test_error_telemetry"
            },
            category="test"
        )
        
        if not error_id:
            return "Error tracking failed to return an error ID"
        
        # Get error stats
        stats = await ErrorTelemetry.get_error_stats(days=1)
        if not isinstance(stats, dict):
            return f"Invalid error stats: {stats}"
        
        return True
    except Exception as e:
        return f"Error telemetry error: {str(e)}"

async def test_user_feedback():
    """Test user feedback system
    
    Returns:
        True if successful, error message otherwise
    """
    try:
        # Import user feedback module
        from utils.user_feedback import (
            create_error_embed, create_success_embed,
            create_info_embed, create_warning_embed,
            get_suggestion_for_error
        )
        
        # Test error embed creation
        error_embed = create_error_embed(
            title="Test Error",
            description="This is a test error",
            error_type="test"
        )
        if not error_embed or not hasattr(error_embed, "title") or error_embed.title != "Test Error":
            return f"Invalid error embed: {error_embed}"
        
        # Test success embed creation
        success_embed = create_success_embed(
            title="Test Success",
            description="This is a test success"
        )
        if not success_embed or not hasattr(success_embed, "title") or success_embed.title != "Test Success":
            return f"Invalid success embed: {success_embed}"
        
        # Test suggestion generation
        suggestion = get_suggestion_for_error(ValueError("Test error"))
        if not suggestion or not isinstance(suggestion, str):
            return f"Invalid suggestion: {suggestion}"
        
        return True
    except Exception as e:
        return f"User feedback error: {str(e)}"

# Backward Compatibility Tests
async def test_command_compatibility_layer():
    """Test command compatibility layer
    
    Returns:
        True if successful, error message otherwise
    """
    try:
        # Import compatibility layer
        from utils.command_compatibility_layer import (
            normalize_context, get_command_signature,
            compatible_command, compatible_slash_command
        )
        
        # Test command signature generation
        class MockCommand:
            name = "test_command"
            qualified_name = "test_command"
            
            async def callback(self, ctx, param1: str, param2: int = 5):
                pass
        
        signature = get_command_signature(MockCommand())
        if not signature or "test_command" not in signature:
            return f"Invalid command signature: {signature}"
        
        # Test context normalization with different context types
        mock_ctx = type('MockContext', (), {
            'bot': None,
            'guild': type('MockGuild', (), {'id': '123'}),
            'channel': type('MockChannel', (), {'id': '456'}),
            'author': type('MockUser', (), {'id': '789'}),
            'command': type('MockCommand', (), {'name': 'test'})
        })()
        
        normalized = normalize_context(mock_ctx)
        if not normalized or normalized["context_type"] != "context":
            return f"Invalid context normalization: {normalized}"
        
        return True
    except Exception as e:
        return f"Command compatibility error: {str(e)}"

async def test_data_migration_compatibility():
    """Test data migration compatibility
    
    Returns:
        True if successful, error message otherwise
    """
    try:
        # Import data version modules
        from utils.data_version import (
            compare_versions, version_greater_or_equal,
            parse_version, CURRENT_VERSIONS
        )
        
        # Test version comparison
        if compare_versions("1.0.0", "2.0.0") != -1:
            return "Version comparison failed: 1.0.0 should be less than 2.0.0"
        
        if compare_versions("2.0.0", "1.0.0") != 1:
            return "Version comparison failed: 2.0.0 should be greater than 1.0.0"
        
        if compare_versions("1.0.0", "1.0.0") != 0:
            return "Version comparison failed: 1.0.0 should be equal to 1.0.0"
        
        # Test version parsing
        v = parse_version("1.2.3")
        if v != (1, 2, 3):
            return f"Version parsing failed: expected (1, 2, 3), got {v}"
        
        # Test current versions
        if not CURRENT_VERSIONS or not isinstance(CURRENT_VERSIONS, dict):
            return f"Invalid current versions: {CURRENT_VERSIONS}"
        
        return True
    except Exception as e:
        return f"Data version error: {str(e)}"

# Main Integration Test
async def run_integration_tests():
    """Run all integration tests"""
    logger.info("Starting integration tests")
    start_time = datetime.datetime.now()
    
    try:
        # Initialize database connection
        import motor.motor_asyncio
        from config import Config
        
        # Connect to database
        client = motor.motor_asyncio.AsyncIOMotorClient(Config.MONGODB_URI)
        db = client[Config.DB_NAME]
        
        # Run database tests
        await run_test("Database Connection", test_database_connection, db)
        await run_test("Data Migration", test_data_migration, db)
        
        # Run SFTP tests
        await run_test("SFTP Connection Pool", test_sftp_connection_pool)
        await run_test("SFTP Helpers", test_sftp_helpers)
        
        # Run error handling tests
        await run_test("Error Telemetry", test_error_telemetry, db)
        await run_test("User Feedback", test_user_feedback)
        
        # Run backward compatibility tests
        await run_test("Command Compatibility Layer", test_command_compatibility_layer)
        await run_test("Data Migration Compatibility", test_data_migration_compatibility)
        
    except Exception as e:
        logger.error(f"Integration test error: {e}")
        logger.error(traceback.format_exc())
    
    # Calculate test duration
    duration = (datetime.datetime.now() - start_time).total_seconds()
    
    # Print summary
    logger.info(f"Integration tests completed in {duration:.2f} seconds")
    logger.info(f"Passed: {TEST_RESULTS['passed']}")
    logger.info(f"Failed: {TEST_RESULTS['failed']}")
    logger.info(f"Skipped: {TEST_RESULTS['skipped']}")
    
    if TEST_RESULTS["errors"]:
        logger.info("Test errors:")
        for i, error in enumerate(TEST_RESULTS["errors"], 1):
            logger.info(f"{i}. {error['test']}: {error['error']}")
    
    return TEST_RESULTS

if __name__ == "__main__":
    # Run integration tests
    asyncio.run(run_integration_tests())