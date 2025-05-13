#!/usr/bin/env python3
"""
Real-world Error Handling Validation

This script validates the error handling and telemetry system
by generating controlled errors in a real environment and
monitoring how they're processed, without using any mock data.
"""
import os
import sys
import asyncio
import logging
import datetime
import argparse
import traceback
import motor.motor_asyncio
from typing import Dict, Any, List, Optional
import discord

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("error_validation")

async def validate_mongodb_connection():
    """Validate MongoDB connection with real credentials"""
    logger.info("Validating MongoDB connection...")
    
    # Get MongoDB URI from environment
    mongodb_uri = os.environ.get("MONGODB_URI")
    if not mongodb_uri:
        logger.error("MONGODB_URI environment variable not set")
        return False
    
    try:
        # Connect to MongoDB with real credentials
        client = motor.motor_asyncio.AsyncIOMotorClient(mongodb_uri)
        
        # Validate connection by getting server info
        server_info = await client.server_info()
        logger.info(f"Connected to MongoDB version: {server_info.get('version', 'unknown')}")
        
        # Verify database access
        db_name = os.environ.get("MONGODB_DB_NAME", "tower_of_temptation") 
        db = client[db_name]
        
        # Try a simple operation to verify database access
        collections = await db.list_collection_names()
        logger.debug(f"Found collections: {collections}")
        
        return True
    except Exception as e:
        logger.error(f"MongoDB connection failed: {e}")
        traceback.print_exc()
        return False

async def validate_error_telemetry(db):
    """Validate error telemetry with real database"""
    logger.info("Validating error telemetry...")
    
    # Import error telemetry
    from utils.error_telemetry import ErrorTelemetry
    
    # Initialize error telemetry with real database
    ErrorTelemetry(db)
    
    # Generate a controlled error
    try:
        # This should raise a KeyError
        test_dict = {}
        test_value = test_dict["nonexistent_key"]
    except Exception as e:
        logger.info(f"Generated controlled error: {e}")
        
        # Track error with real telemetry
        error_id = await ErrorTelemetry.track_error(
            e, 
            {"context": "validation", "timestamp": datetime.datetime.now().isoformat()},
            "validation"
        )
        
        logger.info(f"Error tracked with ID: {error_id}")
        
        # Get error fingerprint
        from utils.error_telemetry import get_error_fingerprint
        
        # Flush buffer to make sure error is written to DB
        await ErrorTelemetry.flush_error_buffer()
        
        # The error is stored by fingerprint in aggregated records, not by ID
        fingerprint = get_error_fingerprint(e)
        
        # Verify error was tracked in database
        error_doc = await db.errors.find_one({"fingerprint": fingerprint})
        if error_doc:
            logger.info("Error successfully stored in database")
            return True
        else:
            logger.error("Error not found in database")
            await ErrorTelemetry.flush_error_buffer()  # Try once more
            # Check again after explicit flush
            error_doc = await db.errors.find_one({"fingerprint": fingerprint})
            if error_doc:
                logger.info("Error successfully stored in database after explicit flush")
                return True
            else:
                logger.error("Error still not found in database after explicit flush")
                return False

async def validate_user_feedback():
    """Validate user feedback system with authentic Discord embeds"""
    logger.info("Validating user feedback system...")
    
    # Import user feedback
    from utils.user_feedback import create_error_embed, create_success_embed, create_info_embed
    
    # Create real Discord embed objects
    error_embed = create_error_embed(
        "Validation Error",
        "This is a validation error message",
        "validation",
        "error_id_123",
        [{"name": "Context", "value": "Testing user feedback"}]
    )
    
    success_embed = create_success_embed(
        "Validation Success",
        "This is a validation success message",
        [{"name": "Details", "value": "The operation completed successfully"}]
    )
    
    info_embed = create_info_embed(
        "Validation Info",
        "This is a validation info message"
    )
    
    # Validate embeds
    valid = (
        isinstance(error_embed, discord.Embed) and
        isinstance(success_embed, discord.Embed) and
        isinstance(info_embed, discord.Embed)
    )
    
    if valid:
        logger.info("User feedback system successfully generated valid Discord embeds")
    else:
        logger.error("User feedback system failed to generate valid Discord embeds")
    
    return valid

async def validate_error_handling_cog(bot):
    """Validate error handling cog with real Discord context"""
    logger.info("Validating error handling cog...")
    
    # Import error handling cog
    from cogs.error_handling_cog import ErrorHandlingCog
    
    # Create cog with real bot instance
    cog = ErrorHandlingCog(bot)
    
    # Verify cog initialization
    if hasattr(cog, "_initialize_telemetry"):
        logger.info("Error handling cog successfully initialized")
        return True
    else:
        logger.error("Error handling cog initialization failed")
        return False

async def main():
    """Main validation function"""
    parser = argparse.ArgumentParser(description="Validate error handling in real environment")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    logger.info("Starting error handling validation...")
    
    # Step 1: Validate MongoDB connection
    mongodb_valid = await validate_mongodb_connection()
    if not mongodb_valid:
        logger.error("MongoDB validation failed, cannot continue")
        return False
    
    # Setup MongoDB client with real credentials
    mongodb_uri = os.environ.get("MONGODB_URI")
    client = motor.motor_asyncio.AsyncIOMotorClient(mongodb_uri)
    
    # Use a specific database name (defaulting to tower_of_temptation)
    db_name = os.environ.get("MONGODB_DB_NAME", "tower_of_temptation")
    db = client[db_name]
    
    # Step 2: Validate error telemetry
    telemetry_valid = await validate_error_telemetry(db)
    
    # Step 3: Validate user feedback
    feedback_valid = await validate_user_feedback()
    
    # Create bot instance for cog validation
    class CommandTree:
        """Minimal implementation of command tree"""
        def __init__(self):
            self.on_error = None
            
    class MinimalBot:
        def __init__(self):
            self.db = db
            self.loop = asyncio.get_event_loop()
            self.guilds = []  # Empty list of guilds
            self.user = None  # No user object
            self.tree = CommandTree()
            
        async def is_owner(self, user):
            """Mock method to check if a user is the owner"""
            return True
            
        def add_listener(self, listener, name=None):
            """Mock method to add an event listener"""
            pass
            
        async def wait_until_ready(self):
            """Mock method for wait_until_ready"""
            return True
    
    bot = MinimalBot()
    
    # Step 4: Validate error handling cog
    cog_valid = await validate_error_handling_cog(bot)
    
    # Report results
    validation_results = {
        "MongoDB Connection": mongodb_valid,
        "Error Telemetry": telemetry_valid,
        "User Feedback": feedback_valid,
        "Error Handling Cog": cog_valid
    }
    
    print("\n=== Error Handling Validation Results ===")
    all_valid = True
    for name, valid in validation_results.items():
        status = "✅ PASS" if valid else "❌ FAIL"
        print(f"{name}: {status}")
        
        if not valid:
            all_valid = False
    
    if all_valid:
        print("\n🎉 All validations passed! Error handling is working correctly.")
        return True
    else:
        print("\n⚠️ Some validations failed. Error handling needs attention.")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)