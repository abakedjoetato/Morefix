"""
Bot Integration Module

This module provides integration between the Discord bot and all compatibility layers,
ensuring a consistent interface for bot operation regardless of Discord library version.
"""

import os
import sys
import logging
import asyncio
import importlib
from typing import Any, Dict, List, Optional, Union, Callable, TypeVar, cast

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Import compatibility modules
from utils.discord_compat import discord, commands, app_commands
from utils.interaction_handlers import (
    hybrid_send, hybrid_defer, hybrid_edit,
    is_interaction, is_context, get_user, get_guild, get_channel
)
from utils.safe_mongodb import (
    setup_mongodb, get_client, get_database, get_collection,
    find_one_document, find_documents, insert_document,
    update_document, delete_document, count_documents,
    SafeMongoDBResult, SafeDocument, success_result, error_result
)

# Type variables
T = TypeVar('T')
BotT = TypeVar('BotT', bound='Bot')

class Bot:
    """
    Integrated Bot class with compatibility across Discord library versions.
    
    This class wraps a Discord bot instance with compatibility layers for
    commands, interactions, and database operations.
    
    Attributes:
        bot: The underlying Discord bot instance
        db: The MongoDB database instance
        client: The MongoDB client instance
    """
    
    def __init__(self, token: Optional[str] = None, **kwargs):
        """
        Initialize the Bot integration.
        
        Args:
            token: Discord bot token
            **kwargs: Additional arguments for the Discord bot
        """
        self.token = token or os.environ.get('DISCORD_TOKEN')
        
        # Set default intents if not provided
        if 'intents' not in kwargs:
            kwargs['intents'] = discord.Intents.default()
            kwargs['intents'].message_content = True
        
        # Create the Discord bot
        self.bot = commands.Bot(**kwargs)
        self.db = None
        self.client = None
        
        # Add helper methods to the bot
        self._add_helper_methods()
    
    def _add_helper_methods(self):
        """Add helper methods to the bot instance."""
        # Add interaction handlers
        self.bot.hybrid_send = hybrid_send
        self.bot.hybrid_defer = hybrid_defer
        self.bot.hybrid_edit = hybrid_edit
        self.bot.is_interaction = is_interaction
        self.bot.is_context = is_context
        self.bot.get_user_from_ctx = get_user
        self.bot.get_guild_from_ctx = get_guild
        self.bot.get_channel_from_ctx = get_channel
        
    async def setup_mongodb(self, connection_string: Optional[str] = None, database_name: Optional[str] = None, **kwargs) -> bool:
        """
        Set up MongoDB integration.
        
        Args:
            connection_string: MongoDB connection string
            database_name: MongoDB database name
            **kwargs: Additional arguments for the MongoDB client
            
        Returns:
            Whether the setup was successful
        """
        # Get connection string and database name from environment if not provided
        connection_string = connection_string or os.environ.get('MONGODB_URI')
        database_name = database_name or os.environ.get('MONGODB_DATABASE', 'tower')
        
        if not connection_string:
            logger.error("MongoDB connection string not provided. MongoDB integration will not be available.")
            return False
        
        # Set up MongoDB
        success = setup_mongodb(connection_string, database_name, **kwargs)
        if success:
            self.client = get_client()
            self.db = get_database()
            logger.info(f"MongoDB integration set up successfully with database '{database_name}'")
        return success
    
    def get_collection(self, collection_name: str) -> Any:
        """
        Get a MongoDB collection.
        
        Args:
            collection_name: Name of the collection
            
        Returns:
            The MongoDB collection or None if not set up
        """
        return get_collection(collection_name)
    
    async def find_one(self, collection_name: str, filter: Dict[str, Any], **kwargs) -> SafeMongoDBResult:
        """
        Find a single document in a collection.
        
        Args:
            collection_name: Name of the collection
            filter: Filter to apply
            **kwargs: Additional arguments for find_one
            
        Returns:
            SafeMongoDBResult with the found document or error
        """
        return await find_one_document(collection_name, filter, **kwargs)
    
    async def find(self, collection_name: str, filter: Dict[str, Any], **kwargs) -> SafeMongoDBResult:
        """
        Find documents in a collection.
        
        Args:
            collection_name: Name of the collection
            filter: Filter to apply
            **kwargs: Additional arguments for find
            
        Returns:
            SafeMongoDBResult with the found documents or error
        """
        return await find_documents(collection_name, filter, **kwargs)
    
    async def insert_one(self, collection_name: str, document: Dict[str, Any], **kwargs) -> SafeMongoDBResult:
        """
        Insert a document into a collection.
        
        Args:
            collection_name: Name of the collection
            document: Document to insert
            **kwargs: Additional arguments for insert_one
            
        Returns:
            SafeMongoDBResult with the inserted ID or error
        """
        return await insert_document(collection_name, document, **kwargs)
    
    async def update_one(self, collection_name: str, filter: Dict[str, Any], update: Dict[str, Any], **kwargs) -> SafeMongoDBResult:
        """
        Update a document in a collection.
        
        Args:
            collection_name: Name of the collection
            filter: Filter to apply
            update: Update to apply
            **kwargs: Additional arguments for update_one
            
        Returns:
            SafeMongoDBResult with the update result or error
        """
        return await update_document(collection_name, filter, update, **kwargs)
    
    async def delete_one(self, collection_name: str, filter: Dict[str, Any], **kwargs) -> SafeMongoDBResult:
        """
        Delete a document from a collection.
        
        Args:
            collection_name: Name of the collection
            filter: Filter to apply
            **kwargs: Additional arguments for delete_one
            
        Returns:
            SafeMongoDBResult with the delete result or error
        """
        return await delete_document(collection_name, filter, **kwargs)
    
    async def count(self, collection_name: str, filter: Optional[Dict[str, Any]] = None, **kwargs) -> SafeMongoDBResult:
        """
        Count documents in a collection.
        
        Args:
            collection_name: Name of the collection
            filter: Filter to apply
            **kwargs: Additional arguments for count_documents
            
        Returns:
            SafeMongoDBResult with the count or error
        """
        return await count_documents(collection_name, filter, **kwargs)
    
    def add_cog(self, cog: Any) -> None:
        """
        Add a cog to the bot.
        
        Args:
            cog: The cog to add
        """
        self.bot.add_cog(cog)
        logger.info(f"Added cog: {cog.__class__.__name__}")
    
    def load_cogs(self, cog_dir: str = 'cogs') -> None:
        """
        Load all cogs from a directory.
        
        Args:
            cog_dir: Directory containing cogs
        """
        logger.info(f"Loading cogs from '{cog_dir}'")
        try:
            # Ensure the directory is in the Python path
            if cog_dir not in sys.path:
                sys.path.insert(0, cog_dir)
            
            # Get all Python files in the directory
            import glob
            import os
            cog_files = glob.glob(os.path.join(cog_dir, "*.py"))
            
            # Load each cog
            for file in cog_files:
                try:
                    # Convert file path to module name
                    if file.endswith('.py'):
                        file = file[:-3]
                    module_name = os.path.basename(file)
                    
                    # Skip __init__.py and other special files
                    if module_name.startswith('__'):
                        continue
                    
                    # If the directory is in the Python path, use the basename
                    # Otherwise, use the relative path
                    if cog_dir in sys.path:
                        import_path = module_name
                    else:
                        import_path = os.path.join(cog_dir, module_name).replace('/', '.').replace('\\', '.')
                    
                    # Import the module
                    module = importlib.import_module(import_path)
                    
                    # Reload if already loaded
                    if module.__name__ in sys.modules:
                        module = importlib.reload(module)
                    
                    # Look for a setup function
                    if hasattr(module, 'setup'):
                        module.setup(self)
                    # Look for a cog class
                    else:
                        # Find all cog classes in the module
                        cog_classes = []
                        for attr_name in dir(module):
                            attr = getattr(module, attr_name)
                            if isinstance(attr, type) and issubclass(attr, commands.Cog) and attr != commands.Cog:
                                cog_classes.append(attr)
                        
                        # Add each cog
                        for cog_class in cog_classes:
                            cog = cog_class(self)
                            self.add_cog(cog)
                    
                    logger.info(f"Loaded cog module: {module.__name__}")
                except Exception as e:
                    logger.error(f"Error loading cog {file}: {e}")
        except Exception as e:
            logger.error(f"Error loading cogs: {e}")
    
    async def start(self) -> None:
        """Start the bot."""
        if not self.token:
            logger.error("Discord token not provided. Bot will not start.")
            return
        
        logger.info("Starting bot...")
        try:
            await self.bot.start(self.token)
        except Exception as e:
            logger.error(f"Error starting bot: {e}")
    
    async def close(self) -> None:
        """Close the bot and database connections."""
        logger.info("Closing bot...")
        try:
            await self.bot.close()
        except Exception as e:
            logger.error(f"Error closing bot: {e}")
        
        if self.client:
            logger.info("Closing MongoDB connection...")
            try:
                self.client.close()
            except Exception as e:
                logger.error(f"Error closing MongoDB connection: {e}")
    
    def run(self) -> None:
        """Run the bot."""
        try:
            asyncio.run(self.start())
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
        except Exception as e:
            logger.error(f"Error running bot: {e}")
        finally:
            # Ensure event loop is closed properly
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.close()
            except Exception:
                pass

def create_bot(token: Optional[str] = None, **kwargs) -> Bot:
    """
    Create a new integrated bot instance.
    
    Args:
        token: Discord bot token
        **kwargs: Additional arguments for the Discord bot
        
    Returns:
        Integrated bot instance
    """
    return Bot(token, **kwargs)

async def setup_bot(bot: Bot) -> None:
    """
    Set up a bot with standard configurations.
    
    Args:
        bot: Bot instance to set up
    """
    # Add event handlers
    @bot.bot.event
    async def on_ready():
        logger.info(f"Bot connected as {bot.bot.user.name} (ID: {bot.bot.user.id})")
        logger.info(f"Connected to {len(bot.bot.guilds)} guilds")
        
        # Log Discord library version info
        try:
            discord_ver = discord.__version__
            motor_ver = "Unknown"
            try:
                import motor
                motor_ver = getattr(motor, '__version__', 'Unknown')
            except ImportError:
                pass
            
            logger.info(f"Using Discord library version: {discord_ver}")
            logger.info(f"Using Motor library version: {motor_ver}")
        except Exception as e:
            logger.error(f"Error getting version info: {e}")
    
    @bot.bot.event
    async def on_message(message):
        # Ignore messages from bots
        if message.author.bot:
            return
        
        # Process commands
        await bot.bot.process_commands(message)
    
    # Set up MongoDB if environment variable is present
    mongo_uri = os.environ.get('MONGODB_URI')
    if mongo_uri:
        await bot.setup_mongodb(mongo_uri)
    
    # Load cogs
    bot.load_cogs()

# Custom decorator to add command with better error handling
def better_command(name: Optional[str] = None, **kwargs):
    """
    Custom command decorator with better error handling.
    
    Args:
        name: Command name
        **kwargs: Additional arguments for the command
        
    Returns:
        Command decorator
    """
    def decorator(func):
        # Create the command
        cmd = commands.command(name=name, **kwargs)(func)
        
        # Add error handling
        async def error_handler(ctx, error):
            logger.error(f"Error in command {cmd.name}: {error}")
            await ctx.send(f"An error occurred: {error}")
        
        # Add the error handler to the command
        cmd.error(error_handler)
        
        return cmd
    
    return decorator

# Export for easy importing
__all__ = [
    'Bot', 'create_bot', 'setup_bot', 'better_command'
]

if __name__ == "__main__":
    # Create and run the bot if this module is run directly
    bot = create_bot()
    bot.run()