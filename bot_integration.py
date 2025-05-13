"""
Bot Integration Module

This module provides a central integration point for all compatibility layers,
creating a unified interface for the Tower of Temptation Discord bot.
"""

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional, Union

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    # Import Discord compatibility layers
    from utils.discord_compat import discord, commands, app_commands
    from utils.attribute_access import (
        safe_server_getattr,
        safe_member_getattr,
        safe_channel_getattr,
        safe_role_getattr,
        safe_message_getattr
    )
    from utils.interaction_handlers import (
        safely_respond_to_interaction,
        hybrid_send,
        is_interaction,
        is_context,
        get_user,
        get_guild,
        get_guild_id
    )
    from utils.command_handlers import (
        EnhancedSlashCommand,
        text_option,
        number_option,
        integer_option,
        boolean_option,
        user_option,
        channel_option,
        role_option,
        enhanced_slash_command,
        is_pycord_261_or_later
    )
    from utils.command_parameter_builder import (
        CommandParameter,
        CommandBuilder
    )
    
    # Import MongoDB compatibility layers
    from utils.safe_mongodb import (
        SafeMongoDBResult,
        SafeDocument,
        get_collection,
        safe_find_one,
        safe_find,
        safe_insert_one,
        safe_update_one,
        safe_delete_one,
        safe_count
    )
    from utils.mongo_compat import (
        serialize_document,
        deserialize_document,
        is_objectid,
        to_object_id,
        handle_datetime
    )
    
    # Import async and type safety helpers
    from utils.async_helpers import (
        is_coroutine_function,
        ensure_async,
        ensure_sync,
        safe_gather,
        safe_wait,
        AsyncCache,
        cached_async
    )
    from utils.type_safety import (
        safe_cast,
        safe_str,
        safe_int,
        safe_float,
        safe_bool,
        safe_list,
        safe_dict,
        safe_function_call,
        validate_type,
        validate_func_args
    )
    
    # Import event and intent helpers
    from utils.event_helpers import (
        EventDispatcher,
        CompatibleBot,
        register_cog_events
    )
    from utils.intent_helpers import (
        get_default_intents,
        get_all_intents,
        get_minimal_intents,
        create_intents,
        merge_intents
    )
    from utils.permission_helpers import (
        get_channel_permissions,
        has_permission,
        has_channel_permission,
        format_permissions,
        create_permissions,
        merge_permissions,
        is_admin,
        has_role,
        has_any_role,
        has_all_roles
    )
    
    # Import MongoDB client libraries
    import motor.motor_asyncio
    import pymongo
    
    # Flag that imports succeeded
    IMPORTS_SUCCEEDED = True
    
except ImportError as e:
    logger.error(f"Failed to import required modules: {e}")
    IMPORTS_SUCCEEDED = False


class CompatibleMongoClient:
    """MongoDB client with compatibility layers."""
    
    def __init__(self, uri: Optional[str] = None):
        """
        Initialize the MongoDB client.
        
        Args:
            uri: MongoDB connection URI, or None to use environment variable
        """
        if uri is None:
            uri = os.environ.get("MONGODB_URI")
            
        if not uri:
            raise ValueError("MongoDB URI is required")
            
        # Create the client
        self.motor_client = motor.motor_asyncio.AsyncIOMotorClient(uri)
        
    def get_database(self, db_name: str) -> motor.motor_asyncio.AsyncIOMotorDatabase:
        """
        Get a MongoDB database.
        
        Args:
            db_name: Database name
            
        Returns:
            AsyncIOMotorDatabase instance
        """
        return self.motor_client[db_name]
        
    def get_collection(self, db_name: str, collection_name: str) -> motor.motor_asyncio.AsyncIOMotorCollection:
        """
        Get a MongoDB collection with compatibility.
        
        Args:
            db_name: Database name
            collection_name: Collection name
            
        Returns:
            AsyncIOMotorCollection instance
        """
        db = self.get_database(db_name)
        return get_collection(db, collection_name)
        
    async def find_one(self, db_name: str, collection_name: str, query: Dict[str, Any], **kwargs) -> Optional[SafeDocument]:
        """
        Find a single document with compatibility.
        
        Args:
            db_name: Database name
            collection_name: Collection name
            query: Query document
            **kwargs: Additional arguments to pass to find_one
            
        Returns:
            SafeDocument instance or None
        """
        collection = self.get_collection(db_name, collection_name)
        result = await safe_find_one(collection, query, **kwargs)
        
        if result:
            return SafeDocument(result)
            
        return None
        
    async def find(self, db_name: str, collection_name: str, query: Dict[str, Any], **kwargs) -> List[SafeDocument]:
        """
        Find documents with compatibility.
        
        Args:
            db_name: Database name
            collection_name: Collection name
            query: Query document
            **kwargs: Additional arguments to pass to find
            
        Returns:
            List of SafeDocument instances
        """
        collection = self.get_collection(db_name, collection_name)
        cursor = await safe_find(collection, query, **kwargs)
        
        results = []
        async for doc in cursor:
            results.append(SafeDocument(doc))
            
        return results
        
    async def insert_one(self, db_name: str, collection_name: str, document: Dict[str, Any], **kwargs) -> SafeMongoDBResult:
        """
        Insert a single document with compatibility.
        
        Args:
            db_name: Database name
            collection_name: Collection name
            document: Document to insert
            **kwargs: Additional arguments to pass to insert_one
            
        Returns:
            SafeMongoDBResult instance
        """
        collection = self.get_collection(db_name, collection_name)
        return await safe_insert_one(collection, document, **kwargs)
        
    async def update_one(self, db_name: str, collection_name: str, query: Dict[str, Any], update: Dict[str, Any], **kwargs) -> SafeMongoDBResult:
        """
        Update a single document with compatibility.
        
        Args:
            db_name: Database name
            collection_name: Collection name
            query: Query document
            update: Update document
            **kwargs: Additional arguments to pass to update_one
            
        Returns:
            SafeMongoDBResult instance
        """
        collection = self.get_collection(db_name, collection_name)
        return await safe_update_one(collection, query, update, **kwargs)
        
    async def delete_one(self, db_name: str, collection_name: str, query: Dict[str, Any], **kwargs) -> SafeMongoDBResult:
        """
        Delete a single document with compatibility.
        
        Args:
            db_name: Database name
            collection_name: Collection name
            query: Query document
            **kwargs: Additional arguments to pass to delete_one
            
        Returns:
            SafeMongoDBResult instance
        """
        collection = self.get_collection(db_name, collection_name)
        return await safe_delete_one(collection, query, **kwargs)
        
    async def count(self, db_name: str, collection_name: str, query: Dict[str, Any], **kwargs) -> int:
        """
        Count documents with compatibility.
        
        Args:
            db_name: Database name
            collection_name: Collection name
            query: Query document
            **kwargs: Additional arguments to pass to count_documents
            
        Returns:
            Document count
        """
        collection = self.get_collection(db_name, collection_name)
        return await safe_count(collection, query, **kwargs)


class DiscordBot(CompatibleBot):
    """
    Discord bot with compatibility layers.
    
    This class extends CompatibleBot to provide a unified interface for
    the Tower of Temptation Discord bot, incorporating all compatibility
    layers.
    """
    
    def __init__(
        self,
        command_prefix: str = "!",
        intents: Optional[discord.Intents] = None,
        mongodb_uri: Optional[str] = None,
        db_name: str = "tower_of_temptation",
        **kwargs
    ):
        """
        Initialize the bot with compatibility layers.
        
        Args:
            command_prefix: Command prefix for text commands
            intents: Discord intents, or None for default intents
            mongodb_uri: MongoDB URI, or None to use environment variable
            db_name: MongoDB database name
            **kwargs: Additional arguments to pass to CompatibleBot
        """
        # Set up default intents if not provided
        if intents is None:
            intents = get_default_intents()
            
        # Initialize the bot
        super().__init__(command_prefix=command_prefix, intents=intents, **kwargs)
        
        # Set up MongoDB client
        self.db_client = CompatibleMongoClient(mongodb_uri)
        self.db_name = db_name
        
        # Set up AsyncCache
        self.cache = AsyncCache(ttl=300.0)  # 5 minutes TTL
        
        # Register event handlers
        self.setup_events()
        
    def setup_events(self):
        """Set up event handlers."""
        
        @self.event
        async def on_ready():
            """Event handler for when the bot is ready."""
            logger.info(f"Logged in as {self.user.name} ({self.user.id})")
            logger.info(f"Using Discord API version {discord.__version__}")
            logger.info(f"Using PyMongo version {pymongo.__version__}")
            logger.info(f"Using Motor version {motor.__version__}")
            
        @self.event
        async def on_command_error(ctx, error):
            """Event handler for command errors."""
            # Get the original error
            error = getattr(error, "original", error)
            
            # Log the error
            logger.error(f"Command error: {error}")
            logger.error("".join(traceback.format_exception(type(error), error, error.__traceback__)))
            
            # Send an error message
            await hybrid_send(
                ctx,
                content=f"An error occurred: {safe_str(error)}",
                ephemeral=True
            )
            
    def add_cog(self, cog, **kwargs):
        """
        Add a cog with compatibility.
        
        Args:
            cog: Cog to add
            **kwargs: Additional arguments to pass to add_cog
        """
        # Add the cog
        super().add_cog(cog, **kwargs)
        
        # Register cog events
        register_cog_events(self, cog)
        
    async def get_document(self, collection_name: str, query: Dict[str, Any], **kwargs) -> Optional[SafeDocument]:
        """
        Get a document from the database.
        
        Args:
            collection_name: Collection name
            query: Query document
            **kwargs: Additional arguments to pass to find_one
            
        Returns:
            SafeDocument instance or None
        """
        return await self.db_client.find_one(self.db_name, collection_name, query, **kwargs)
        
    async def get_documents(self, collection_name: str, query: Dict[str, Any], **kwargs) -> List[SafeDocument]:
        """
        Get documents from the database.
        
        Args:
            collection_name: Collection name
            query: Query document
            **kwargs: Additional arguments to pass to find
            
        Returns:
            List of SafeDocument instances
        """
        return await self.db_client.find(self.db_name, collection_name, query, **kwargs)
        
    async def save_document(self, collection_name: str, document: Dict[str, Any], **kwargs) -> SafeMongoDBResult:
        """
        Save a document to the database.
        
        Args:
            collection_name: Collection name
            document: Document to save
            **kwargs: Additional arguments to pass to insert_one
            
        Returns:
            SafeMongoDBResult instance
        """
        return await self.db_client.insert_one(self.db_name, collection_name, document, **kwargs)
        
    async def update_document(self, collection_name: str, query: Dict[str, Any], update: Dict[str, Any], **kwargs) -> SafeMongoDBResult:
        """
        Update a document in the database.
        
        Args:
            collection_name: Collection name
            query: Query document
            update: Update document
            **kwargs: Additional arguments to pass to update_one
            
        Returns:
            SafeMongoDBResult instance
        """
        return await self.db_client.update_one(self.db_name, collection_name, query, update, **kwargs)
        
    async def delete_document(self, collection_name: str, query: Dict[str, Any], **kwargs) -> SafeMongoDBResult:
        """
        Delete a document from the database.
        
        Args:
            collection_name: Collection name
            query: Query document
            **kwargs: Additional arguments to pass to delete_one
            
        Returns:
            SafeMongoDBResult instance
        """
        return await self.db_client.delete_one(self.db_name, collection_name, query, **kwargs)
        
    async def count_documents(self, collection_name: str, query: Dict[str, Any], **kwargs) -> int:
        """
        Count documents in the database.
        
        Args:
            collection_name: Collection name
            query: Query document
            **kwargs: Additional arguments to pass to count_documents
            
        Returns:
            Document count
        """
        return await self.db_client.count(self.db_name, collection_name, query, **kwargs)
        
    async def cached_get_document(self, collection_name: str, query: Dict[str, Any], **kwargs) -> Optional[SafeDocument]:
        """
        Get a document from the database with caching.
        
        Args:
            collection_name: Collection name
            query: Query document
            **kwargs: Additional arguments to pass to find_one
            
        Returns:
            SafeDocument instance or None
        """
        # Create a cache key
        cache_key = f"doc:{collection_name}:{serialize_document(query)}"
        
        # Get from cache or fetch
        return await self.cache.get_or_set_async(
            cache_key,
            lambda: self.get_document(collection_name, query, **kwargs)
        )


def create_bot(**kwargs) -> DiscordBot:
    """
    Create a Discord bot with all compatibility layers.
    
    Args:
        **kwargs: Arguments to pass to DiscordBot
        
    Returns:
        DiscordBot instance
    """
    return DiscordBot(**kwargs)


# Example usage
if __name__ == "__main__":
    # Check if imports succeeded
    if not IMPORTS_SUCCEEDED:
        print("Failed to import required modules. Please run verify_compatibility.py first.")
        import sys
        sys.exit(1)
        
    # Load environment variables from .env file if present
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        print("python-dotenv not installed. Environment variables must be set manually.")
        
    # Create the bot
    bot = create_bot()
    
    # Run the bot
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        print("DISCORD_TOKEN environment variable is required")
        import sys
        sys.exit(1)
        
    bot.run(token)