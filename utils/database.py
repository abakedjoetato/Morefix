import os
import logging
import pymongo
import asyncio
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from config import Config
from typing import Dict, Any, Optional, Union, List

# Import safe database utilities
from utils.safe_database import (
    get_document_safely as safe_find_one,
    safely_update_document as safe_update_one,
    safe_insert_one,
    count_documents_safely as safe_count_documents,
    safe_get as safe_get_document_field,
    safe_document_to_dict,
    has_field, 
    is_db_available,
    SafeDocument
)

# Create local versions of functions that don't exist in safe_database yet
async def safe_get_db(db_instance, db_name=None):
    """Safely get a database instance"""
    if db_instance is None:
        logger.error("No database instance provided")
        return None
    
    try:
        if db_name:
            return db_instance[db_name]
        return db_instance
    except Exception as e:
        logger.error(f"Error getting database: {e}")
        return None

async def safe_get_collection(db, collection_name):
    """Safely get a collection from a database"""
    if db is None:
        logger.error("No database instance provided")
        return None
    
    try:
        return db[collection_name]
    except Exception as e:
        logger.error(f"Error getting collection {collection_name}: {e}")
        return None

logger = logging.getLogger("discord_bot")

# Global database instance 
_db_instance = None

def get_db():
    """Get the global database instance
    
    Returns:
        Database: The singleton database instance
    """
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance

class Database:
    """MongoDB database connector for the Discord bot"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
            cls._instance.initialized = False
        return cls._instance
    
    def __init__(self):
        if self.initialized:
            return
        
        self.initialized = True
        self.client = None
        self.db = None
        
        # Initialize the database connection
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize the MongoDB connection"""
        try:
            uri = Config.MONGODB_URI
            if not uri:
                logger.critical("MongoDB URI is not set in environment variables!")
                raise ValueError("MONGODB_URI environment variable is required")
            
            # Create the async MongoDB client
            self.client = AsyncIOMotorClient(uri)
            self.db = self.client[Config.DB_NAME]
            
            # Log successful connection
            logger.info(f"Connected to MongoDB database: {Config.DB_NAME}")
            
            # Create indexes for collections (async)
            asyncio.create_task(self._create_indexes())
            
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}", exc_info=True)
            raise
    
    async def _create_indexes(self):
        """Create necessary indexes for the database collections"""
        try:
            # Safely create indexes - handling the case where they already exist
            await self._safe_create_index(self.db.users, "user_id", unique=True)
            
            # Message logs indexes
            await self._safe_create_index(self.db.message_logs, "timestamp")
            await self._safe_create_index(self.db.message_logs, "user_id")
            
            # Servers collection indexes
            await self._safe_create_index(self.db.servers, "server_id", unique=True)
            
            # Config collection indexes
            await self._safe_create_index(self.db.config, "key", unique=True)
            
            logger.info("Database indexes created successfully")
        except Exception as e:
            logger.error(f"Failed to create database indexes: {e}", exc_info=True)
    
    async def _safe_create_index(self, collection, key, **kwargs):
        """Safely create an index, catching and handling duplicate index errors
        
        Args:
            collection: MongoDB collection
            key: Index key
            **kwargs: Additional index options
        """
        try:
            # Try to create the index
            await collection.create_index(key, **kwargs)
        except pymongo.errors.OperationFailure as e:
            # Check if it's just a duplicate index error (code 86)
            if hasattr(e, 'code') and e.code == 86:
                logger.debug(f"Index for {key} already exists in collection {collection.name}")
            else:
                # It's another error, re-raise it
                logger.error(f"Failed to create index on {collection.name}.{key}: {e}")
                raise
    
    async def get_user(self, user_id):
        """Get a user's data from the database
        
        Args:
            user_id: Discord user ID
            
        Returns:
            SafeDocument: User document wrapped in SafeDocument for safe access
        """
        try:
            # Use safe_find_one utility to handle None database, error cases
            # and return a SafeDocument that can be safely accessed
            return await safe_find_one(self.db, "users", {"user_id": user_id})
        except Exception as e:
            logger.error(f"Error retrieving user {user_id}: {e}", exc_info=True)
            return SafeDocument(None)  # Return empty SafeDocument for consistent API
    
    async def create_user(self, user_id, username):
        """Create a new user in the database
        
        Args:
            user_id: Discord user ID
            username: Discord username
            
        Returns:
            SafeDocument: Created or existing user document
        """
        try:
            user_data = {
                "user_id": user_id,
                "username": username,
                "created_at": datetime.utcnow(),
                "command_count": 0,
                "message_count": 0
            }
            
            # Use safe insert method
            result = await safe_insert_one(self.db, "users", user_data)
            
            if result.get("success", False):
                logger.info(f"Created new user in database: {username} ({user_id})")
                return SafeDocument(user_data)
            elif "duplicate key" in str(result.get("error", "")).lower():
                # User already exists, just return the existing data
                logger.debug(f"User {username} ({user_id}) already exists, returning existing data")
                return await self.get_user(user_id)
            else:
                # Other error occurred
                logger.error(f"Error creating user {user_id}: {result.get('error')}")
                return SafeDocument(None)
                
        except pymongo.errors.DuplicateKeyError:
            # User already exists, just return the existing data
            return await self.get_user(user_id)
        except Exception as e:
            logger.error(f"Error creating user {user_id}: {e}", exc_info=True)
            return SafeDocument(None)
    
    async def increment_command_count(self, user_id):
        """Increment a user's command usage count
        
        Args:
            user_id: Discord user ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Use safe update method that handles None database and other errors
            result = await safe_update_one(
                self.db, 
                "users",
                {"user_id": user_id},
                {
                    "$inc": {"command_count": 1},
                    "$set": {"last_command": datetime.utcnow()}
                },
                upsert=True
            )
            
            # Check success from result dictionary
            return result.get("success", False)
        except Exception as e:
            logger.error(f"Error incrementing command count for user {user_id}: {e}", exc_info=True)
            return False
    
    async def log_message_activity(self, user_id, server_id, channel_id, message_length):
        """Log a message to the database for analytics
        
        Args:
            user_id: Discord user ID
            server_id: Discord server ID
            channel_id: Discord channel ID
            message_length: Length of the message
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            log_entry = {
                "user_id": user_id,
                "server_id": server_id,
                "channel_id": channel_id,
                "message_length": message_length,
                "timestamp": datetime.utcnow()
            }
            
            # Use safe insert method
            insert_result = await safe_insert_one(self.db, "message_logs", log_entry)
            
            if not insert_result.get("success", False):
                logger.error(f"Failed to insert message log: {insert_result.get('error')}")
                return False
            
            # Also increment the user's message count using safe update
            update_result = await safe_update_one(
                self.db, 
                "users",
                {"user_id": user_id},
                {"$inc": {"message_count": 1}},
                upsert=True
            )
            
            if not update_result.get("success", False):
                logger.warning(f"Failed to increment message count: {update_result.get('error')}")
                # We still return True because the main logging succeeded
            
            return True
        except Exception as e:
            logger.error(f"Error logging message activity for user {user_id}: {e}", exc_info=True)
            return False
    
    async def update_server_stats(self, server_id, server_data):
        """Update server statistics in the database
        
        Args:
            server_id: Server ID to update
            server_data: Dictionary of server data to update
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Create a copy to avoid modifying the original
            data_to_update = dict(server_data)
            data_to_update["server_id"] = server_id
            data_to_update["last_updated"] = datetime.utcnow()
            
            # Use safe update method
            result = await safe_update_one(
                self.db,
                "servers",
                {"server_id": server_id},
                {"$set": data_to_update},
                upsert=True
            )
            
            return result.get("success", False)
        except Exception as e:
            logger.error(f"Error updating server stats for server {server_id}: {e}", exc_info=True)
            return False
    
    async def get_bot_stats(self):
        """Get overall statistics for the bot
        
        Returns:
            Dict[str, int]: Dictionary containing bot statistics
        """
        default_stats = {
            "user_count": 0,
            "server_count": 0,
            "message_count": 0,
            "total_commands": 0
        }
        
        try:
            # Make sure database is available using the safe check
            if not is_db_available(self.db):
                logger.warning("Database not available for getting bot stats")
                return default_stats
                
            # Use safe database operations with proper error handling
            try:
                user_count = await safe_count_documents(self.db, "users", {})
                server_count = await safe_count_documents(self.db, "servers", {})
                message_count = await safe_count_documents(self.db, "message_logs", {})
                
                stats = {
                    "user_count": user_count.get("count", 0) if user_count.get("success", False) else 0,
                    "server_count": server_count.get("count", 0) if server_count.get("success", False) else 0,
                    "message_count": message_count.get("count", 0) if message_count.get("success", False) else 0,
                    "total_commands": 0
                }
                
                # Calculate total commands used
                try:
                    pipeline = [
                        {"$group": {"_id": None, "total": {"$sum": "$command_count"}}}
                    ]
                    
                    # Safe aggregation
                    if self.db and hasattr(self.db, "users"):
                        result = await self.db.users.aggregate(pipeline).to_list(length=1)
                        
                        if result and len(result) > 0:
                            stats["total_commands"] = result[0].get("total", 0)
                except Exception as agg_error:
                    logger.warning(f"Error calculating command totals: {agg_error}")
                    # Continue with zeros for this stat
                
                return stats
                
            except Exception as db_error:
                logger.error(f"Database operation error getting stats: {db_error}")
                return default_stats
                
        except Exception as e:
            logger.error(f"Error retrieving bot stats: {e}", exc_info=True)
            return default_stats
    
    async def clear_old_logs(self, days=30):
        """Clear message logs older than the specified number of days
        
        Args:
            days: Number of days to keep logs for (default: 30)
            
        Returns:
            int: Number of deleted records, or 0 if operation failed
        """
        try:
            # Make sure database is available using safe check
            if not is_db_available(self.db):
                logger.warning("Database not available for clearing old logs")
                return 0
                
            collection = safe_get_collection(self.db, "message_logs")
            if collection is None:
                logger.warning("message_logs collection not available")
                return 0
                
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            try:
                result = await collection.delete_many(
                    {"timestamp": {"$lt": cutoff_date}}
                )
                
                deleted_count = result.deleted_count if hasattr(result, 'deleted_count') else 0
                logger.info(f"Cleared {deleted_count} message logs older than {days} days")
                return deleted_count
                
            except Exception as db_error:
                logger.error(f"Database operation error clearing logs: {db_error}")
                return 0
                
        except Exception as e:
            logger.error(f"Error clearing old logs: {e}", exc_info=True)
            return 0
    
    async def set_config(self, key, value):
        """Set a configuration value in the database
        
        Args:
            key: Configuration key
            value: Configuration value to set
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Use safe update method
            result = await safe_update_one(
                self.db,
                "config",
                {"key": key},
                {"$set": {"value": value, "updated_at": datetime.utcnow()}},
                upsert=True
            )
            
            if result.get("success", False):
                logger.debug(f"Set config {key} to {value}")
                return True
            else:
                logger.warning(f"Failed to set config {key}: {result.get('error')}")
                return False
                
        except Exception as e:
            logger.error(f"Error setting config value for key {key}: {e}", exc_info=True)
            return False
    
    async def get_config(self, key, default=None):
        """Get a configuration value from the database
        
        Args:
            key: Configuration key
            default: Default value if not found (default: None)
            
        Returns:
            Any: Configuration value or default
        """
        try:
            # Use safe find method
            safe_doc = await safe_find_one(self.db, "config", {"key": key})
            
            # SafeDocument's get method handles None case automatically
            return safe_doc.get("value", default)
            
        except Exception as e:
            logger.error(f"Error getting config value for key {key}: {e}", exc_info=True)
            return default
