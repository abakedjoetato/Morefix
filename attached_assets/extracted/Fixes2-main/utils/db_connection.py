"""
Database connection utilities for MongoDB

This module provides connection functions for MongoDB,
using Motor for async operations.
"""

import os
import asyncio
import logging
import motor.motor_asyncio
from typing import Optional, Any, Dict, TypeVar, Type, cast, List

logger = logging.getLogger(__name__)

# MongoDB connection string from environment variables
MONGODB_URI = os.environ.get("MONGODB_URI", "mongodb://localhost:27017/discordbot")
DB_NAME = os.environ.get("DB_NAME", "discordbot")

# Connection and DB instances
_mongo_client = None
_db = None

# Type for database
T = TypeVar('T')


async def get_db_connection():
    """
    Get the MongoDB database connection asynchronously
    
    Returns:
        MongoDB database object or None if connection fails
    """
    global _mongo_client, _db
    
    if _db is not None:
        return _db
        
    try:
        # Create client if not exists
        if _mongo_client is None:
            logger.debug("Creating new MongoDB client")
            _mongo_client = motor.motor_asyncio.AsyncIOMotorClient(
                MONGODB_URI,
                serverSelectionTimeoutMS=5000
            )
        
        # Get database
        _db = _mongo_client[DB_NAME]
        
        # Verify connection with a ping
        await _mongo_client.admin.command('ping')
        logger.debug("MongoDB connection successful")
        
        return _db
        
    except Exception as e:
        logger.error(f"Error connecting to MongoDB: {e}")
        _mongo_client = None
        _db = None
        return None


async def close_db_connection():
    """
    Close the MongoDB database connection
    """
    global _mongo_client, _db
    
    if _mongo_client is not None:
        logger.debug("Closing MongoDB client")
        _mongo_client.close()
        _mongo_client = None
        _db = None
        return True
    
    return False


async def ensure_indexes():
    """
    Ensure all required indexes exist in the database
    
    Creates indexes if they don't exist for optimized queries
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        db = await get_db_connection()
        if db is None:
            logger.error("Failed to get database connection for index creation")
            return False
            
        # Create indexes for guilds collection
        await db.guilds.create_index("guild_id")
        
        # Create indexes for users collection
        await db.users.create_index("user_id")
        await db.users.create_index("guild_id")
        
        # Create indexes for player stats collection
        await db.player_stats.create_index([
            ("guild_id", 1),
            ("server_id", 1),
            ("player_name", 1)
        ])
        
        # Create indexes for bounties collection
        await db.bounties.create_index([
            ("guild_id", 1),
            ("server_id", 1),
            ("status", 1)
        ])
        
        logger.info("Database indexes created successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error creating database indexes: {e}")
        return False