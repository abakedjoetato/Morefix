"""
Bot Integration Module

This module integrates all compatibility layers together for the Discord bot,
providing seamless operation across different Discord library versions.
"""

import os
import sys
import logging
import traceback
from typing import Any, Dict, List, Optional, Tuple, Union, Callable, TypeVar, cast, Generic

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

# Global instances
_mongodb_client = None
_mongodb_db = None
_discord_bot = None

# Type variables
T = TypeVar('T')
R = TypeVar('R')

def setup_mongodb(
    connection_string: Optional[str] = None, 
    database_name: Optional[str] = None,
    **kwargs) -> bool:
    """
    Set up MongoDB with appropriate compatibility layers.
    
    Args:
        connection_string: The MongoDB connection string
        database_name: The name of the database to use
        **kwargs: Additional arguments to pass to the MongoDB client
        
    Returns:
        Whether the setup was successful
    """
    global _mongodb_client, _mongodb_db
    
    if not connection_string:
        connection_string = os.environ.get('MONGODB_URI')
        
    if not database_name:
        database_name = os.environ.get('MONGODB_DATABASE', 'toweroftemptation')
        
    if not connection_string:
        logger.error("MongoDB connection string is required")
        return False
        
    try:
        # Import the compatibility layer
        try:
            from utils.safe_mongodb import setup_mongodb as safe_setup_mongodb
            result = safe_setup_mongodb(connection_string, database_name, **kwargs)
            if not result:
                logger.error("Failed to set up MongoDB using safe_mongodb")
                return False
                
            from utils.safe_mongodb import get_client, get_database
            _mongodb_client = get_client()
            _mongodb_db = get_database()
            
            logger.info(f"MongoDB set up successfully with database: {database_name}")
            return True
        except ImportError:
            # Fall back to direct MongoDB imports
            try:
                import motor.motor_asyncio
                _mongodb_client = motor.motor_asyncio.AsyncIOMotorClient(connection_string, **kwargs)
                _mongodb_db = _mongodb_client[database_name]
                
                logger.info(f"MongoDB set up successfully with direct imports, database: {database_name}")
                return True
            except Exception as mongo_error:
                logger.error(f"Failed to set up MongoDB with direct imports: {mongo_error}")
                return False
    except Exception as e:
        logger.error(f"Failed to set up MongoDB: {e}")
        return False

def get_collection(collection_name: str) -> Any:
    """
    Get a MongoDB collection with compatibility layer.
    
    Args:
        collection_name: The name of the collection
        
    Returns:
        The collection or None
    """
    global _mongodb_db
    
    if not _mongodb_db:
        logger.error("MongoDB not set up. Call setup_mongodb first.")
        return None
        
    try:
        # Try using the safe MongoDB layer
        try:
            from utils.safe_mongodb import get_collection as safe_get_collection
            return safe_get_collection(collection_name)
        except ImportError:
            # Fall back to direct access
            return _mongodb_db[collection_name]
    except Exception as e:
        logger.error(f"Failed to get collection {collection_name}: {e}")
        return None

def create_document_model(collection_name: str, **attrs) -> type:
    """
    Create a document model class with the compatibility layer.
    
    Args:
        collection_name: The name of the collection
        **attrs: Additional attributes for the model class
        
    Returns:
        The model class
    """
    try:
        # Try using the compatibility layer
        try:
            from utils.mongo_compat import create_document_model as compat_create_model
            return compat_create_model(collection_name, **attrs)
        except ImportError:
            # Create a simple model class as fallback
            class DocumentModel:
                def __init__(self, **data):
                    self.collection_name = collection_name
                    for key, value in data.items():
                        setattr(self, key, value)
                        
                async def save(self):
                    doc_data = {k: v for k, v in self.__dict__.items() if not k.startswith('_')}
                    collection = get_collection(collection_name)
                    if '_id' in doc_data:
                        await collection.update_one({'_id': doc_data['_id']}, {'$set': doc_data})
                    else:
                        result = await collection.insert_one(doc_data)
                        self._id = result.inserted_id
                        
                @classmethod
                async def find_one(cls, filter_dict):
                    collection = get_collection(collection_name)
                    doc = await collection.find_one(filter_dict)
                    if doc:
                        return cls(**doc)
                    return None
                    
            # Add any additional attributes
            for key, value in attrs.items():
                setattr(DocumentModel, key, value)
                
            return DocumentModel
    except Exception as e:
        logger.error(f"Failed to create document model for {collection_name}: {e}")
        return None

async def find_one_document(collection_name: str, filter: Dict, 
                           projection: Optional[Dict] = None, **kwargs) -> Any:
    """
    Find a single document with compatibility layer.
    
    Args:
        collection_name: The name of the collection
        filter: The filter to apply
        projection: The projection to apply
        **kwargs: Additional arguments to pass to find_one
        
    Returns:
        The found document or None
    """
    try:
        # Try using the safe MongoDB layer
        try:
            from utils.safe_mongodb import find_one_document as safe_find_one
            result = await safe_find_one(collection_name, filter, projection, **kwargs)
            return result
        except ImportError:
            # Fall back to direct access
            collection = get_collection(collection_name)
            if not collection:
                return None
                
            return await collection.find_one(filter, projection, **kwargs)
    except Exception as e:
        logger.error(f"Failed to find document in {collection_name}: {e}")
        return None

async def find_documents(collection_name: str, filter: Dict, 
                        projection: Optional[Dict] = None, **kwargs) -> List[Any]:
    """
    Find documents with compatibility layer.
    
    Args:
        collection_name: The name of the collection
        filter: The filter to apply
        projection: The projection to apply
        **kwargs: Additional arguments to pass to find
        
    Returns:
        The found documents or empty list
    """
    try:
        # Try using the safe MongoDB layer
        try:
            from utils.safe_mongodb import find_documents as safe_find
            result = await safe_find(collection_name, filter, projection, **kwargs)
            return result
        except ImportError:
            # Fall back to direct access
            collection = get_collection(collection_name)
            if not collection:
                return []
                
            cursor = collection.find(filter, projection, **kwargs)
            return await cursor.to_list(length=None)
    except Exception as e:
        logger.error(f"Failed to find documents in {collection_name}: {e}")
        return []

async def insert_document(collection_name: str, document: Dict, **kwargs) -> Any:
    """
    Insert a document with compatibility layer.
    
    Args:
        collection_name: The name of the collection
        document: The document to insert
        **kwargs: Additional arguments to pass to insert_one
        
    Returns:
        The inserted document ID or None
    """
    try:
        # Try using the safe MongoDB layer
        try:
            from utils.safe_mongodb import insert_document as safe_insert
            result = await safe_insert(collection_name, document, **kwargs)
            return result
        except ImportError:
            # Fall back to direct access
            collection = get_collection(collection_name)
            if not collection:
                return None
                
            # Serialize document if needed
            try:
                from utils.mongo_compat import serialize_document
                document = serialize_document(document)
            except ImportError:
                pass
                
            result = await collection.insert_one(document, **kwargs)
            return result.inserted_id
    except Exception as e:
        logger.error(f"Failed to insert document in {collection_name}: {e}")
        return None

async def update_document(collection_name: str, filter: Dict, 
                         update: Dict, **kwargs) -> bool:
    """
    Update a document with compatibility layer.
    
    Args:
        collection_name: The name of the collection
        filter: The filter to apply
        update: The update to apply
        **kwargs: Additional arguments to pass to update_one
        
    Returns:
        Whether the update was successful
    """
    try:
        # Try using the safe MongoDB layer
        try:
            from utils.safe_mongodb import update_document as safe_update
            result = await safe_update(collection_name, filter, update, **kwargs)
            return result
        except ImportError:
            # Fall back to direct access
            collection = get_collection(collection_name)
            if not collection:
                return False
                
            # Ensure update has operators
            if not any(key.startswith('$') for key in update):
                update = {'$set': update}
                
            # Serialize document if needed
            try:
                from utils.mongo_compat import serialize_document
                filter = serialize_document(filter)
                update = serialize_document(update)
            except ImportError:
                pass
                
            result = await collection.update_one(filter, update, **kwargs)
            return result.modified_count > 0
    except Exception as e:
        logger.error(f"Failed to update document in {collection_name}: {e}")
        return False

async def delete_document(collection_name: str, filter: Dict, **kwargs) -> bool:
    """
    Delete a document with compatibility layer.
    
    Args:
        collection_name: The name of the collection
        filter: The filter to apply
        **kwargs: Additional arguments to pass to delete_one
        
    Returns:
        Whether the deletion was successful
    """
    try:
        # Try using the safe MongoDB layer
        try:
            from utils.safe_mongodb import delete_document as safe_delete
            result = await safe_delete(collection_name, filter, **kwargs)
            return result
        except ImportError:
            # Fall back to direct access
            collection = get_collection(collection_name)
            if not collection:
                return False
                
            # Serialize document if needed
            try:
                from utils.mongo_compat import serialize_document
                filter = serialize_document(filter)
            except ImportError:
                pass
                
            result = await collection.delete_one(filter, **kwargs)
            return result.deleted_count > 0
    except Exception as e:
        logger.error(f"Failed to delete document in {collection_name}: {e}")
        return False

async def count_documents(collection_name: str, filter: Optional[Dict] = None, **kwargs) -> int:
    """
    Count documents with compatibility layer.
    
    Args:
        collection_name: The name of the collection
        filter: The filter to apply
        **kwargs: Additional arguments to pass to count_documents
        
    Returns:
        The count
    """
    try:
        # Try using the safe MongoDB layer
        try:
            from utils.safe_mongodb import count_documents as safe_count
            result = await safe_count(collection_name, filter, **kwargs)
            return result
        except ImportError:
            # Fall back to direct access
            collection = get_collection(collection_name)
            if not collection:
                return 0
                
            filter = filter or {}
            
            # Serialize document if needed
            try:
                from utils.mongo_compat import serialize_document
                filter = serialize_document(filter)
            except ImportError:
                pass
                
            return await collection.count_documents(filter, **kwargs)
    except Exception as e:
        logger.error(f"Failed to count documents in {collection_name}: {e}")
        return 0

def setup_discord(token: Optional[str] = None, intents: Optional[Any] = None, **kwargs) -> bool:
    """
    Set up Discord with appropriate compatibility layers.
    
    Args:
        token: The Discord bot token
        intents: The Discord intents to use
        **kwargs: Additional arguments to pass to the Discord client
        
    Returns:
        Whether the setup was successful
    """
    global _discord_bot
    
    if not token:
        token = os.environ.get('DISCORD_TOKEN')
        
    if not token:
        logger.error("Discord token is required")
        return False
        
    try:
        # Try importing Discord
        try:
            import discord
            from discord.ext import commands
            
            # Get intents if not provided
            if intents is None:
                try:
                    from utils.intent_helpers import get_default_intents
                    intents = get_default_intents()
                except ImportError:
                    intents = discord.Intents.default()
                    intents.message_content = True
                    intents.members = True
                    
            # Create the bot
            _discord_bot = commands.Bot(command_prefix='!', intents=intents, **kwargs)
            
            # Set the token for later use
            _discord_bot.token = token
            
            @_discord_bot.event
            async def on_ready():
                logger.info(f'Bot is ready! Logged in as {_discord_bot.user}')
                
            return True
        except ImportError as ie:
            logger.error(f"Failed to import Discord: {ie}")
            return False
    except Exception as e:
        logger.error(f"Failed to set up Discord: {e}")
        traceback.print_exc()
        return False

def get_bot_info() -> Dict[str, Any]:
    """
    Get information about the bot and its dependencies.
    
    Returns:
        A dictionary of information
    """
    info = {
        'bot_ready': _discord_bot is not None,
        'mongodb_ready': _mongodb_client is not None,
        'dependencies': {}
    }
    
    # Check Discord version
    try:
        import discord
        info['dependencies']['discord'] = discord.__version__
    except (ImportError, AttributeError):
        info['dependencies']['discord'] = 'Not installed'
        
    # Check PyMongo version
    try:
        import pymongo
        info['dependencies']['pymongo'] = pymongo.__version__
    except (ImportError, AttributeError):
        info['dependencies']['pymongo'] = 'Not installed'
        
    # Check Motor version
    try:
        import motor
        info['dependencies']['motor'] = motor.__version__
    except (ImportError, AttributeError):
        info['dependencies']['motor'] = 'Not installed'
        
    return info

async def send_message(ctx_or_interaction: Any, content: Optional[str] = None, 
                      **kwargs) -> Any:
    """
    Send a message with compatibility layer.
    
    Args:
        ctx_or_interaction: The context or interaction to send to
        content: The content to send
        **kwargs: Additional arguments to pass to the send method
        
    Returns:
        The message sent or None
    """
    try:
        # Try to determine if it's a context or interaction
        if hasattr(ctx_or_interaction, 'send'):
            # It's a context
            return await ctx_or_interaction.send(content, **kwargs)
        elif hasattr(ctx_or_interaction, 'response') and hasattr(ctx_or_interaction.response, 'send_message'):
            # It's an interaction
            return await ctx_or_interaction.response.send_message(content, **kwargs)
        elif hasattr(ctx_or_interaction, 'followup') and hasattr(ctx_or_interaction.followup, 'send'):
            # It's an interaction that has already responded
            return await ctx_or_interaction.followup.send(content, **kwargs)
        else:
            logger.error(f"Unknown context or interaction type: {type(ctx_or_interaction)}")
            return None
    except Exception as e:
        logger.error(f"Failed to send message: {e}")
        traceback.print_exc()
        return None

def register_command(name: str, callback: Callable, **kwargs) -> Any:
    """
    Register a command with compatibility layer.
    
    Args:
        name: The name of the command
        callback: The callback function
        **kwargs: Additional arguments to pass to the command decorator
        
    Returns:
        The command object
    """
    global _discord_bot
    
    if not _discord_bot:
        logger.error("Discord bot not set up. Call setup_discord first.")
        return None
        
    try:
        # Get the command decorator
        command = _discord_bot.command(**kwargs)
        
        # Apply the decorator to the callback
        decorated_callback = command(callback)
        
        # Set the name if it's different
        if decorated_callback.name != name:
            decorated_callback.name = name
            
        return decorated_callback
    except Exception as e:
        logger.error(f"Failed to register command {name}: {e}")
        return None

def register_cog(cog_class: type) -> bool:
    """
    Register a cog with compatibility layer.
    
    Args:
        cog_class: The cog class to register
        
    Returns:
        Whether the registration was successful
    """
    global _discord_bot
    
    if not _discord_bot:
        logger.error("Discord bot not set up. Call setup_discord first.")
        return False
        
    try:
        # Create an instance of the cog
        cog_instance = cog_class(_discord_bot)
        
        # Add the cog to the bot
        _discord_bot.add_cog(cog_instance)
        logger.info(f"Registered cog: {cog_class.__name__}")
        return True
    except Exception as e:
        logger.error(f"Failed to register cog {cog_class.__name__}: {e}")
        return False

def create_bot(**kwargs) -> Any:
    """
    Create a Discord bot with compatibility layer.
    
    Args:
        **kwargs: Additional arguments to pass to the Bot constructor
        
    Returns:
        The bot object
    """
    try:
        import discord
        from discord.ext import commands
        
        # Get intents if not provided
        if 'intents' not in kwargs:
            try:
                from utils.intent_helpers import get_default_intents
                kwargs['intents'] = get_default_intents()
            except ImportError:
                kwargs['intents'] = discord.Intents.default()
                kwargs['intents'].message_content = True
                kwargs['intents'].members = True
                
        # Set default command prefix if not provided
        if 'command_prefix' not in kwargs:
            kwargs['command_prefix'] = '!'
            
        # Create the bot
        bot = commands.Bot(**kwargs)
        
        # Create a wrapper for commands with better error handling
        def command_wrapper(name=None, cls=None, **cmd_kwargs):
            def decorator(func):
                # Create the command
                command = bot.command(name=name, cls=cls, **cmd_kwargs)
                
                # Apply the decorator
                decorated = command(func)
                
                # Add error handling
                async def command_error_handler(ctx, error):
                    logger.error(f"Error in command {ctx.command}: {error}")
                    await ctx.send(f"Error: {error}")
                    
                # Set the error handler for the command
                decorated.error(command_error_handler)
                
                return decorated
            return decorator
            
        # Add the wrapper to the bot
        bot.better_command = command_wrapper
        
        return bot
    except Exception as e:
        logger.error(f"Failed to create bot: {e}")
        return None

async def run_bot(**kwargs) -> None:
    """
    Run the Discord bot.
    
    Args:
        **kwargs: Additional arguments to pass to the bot.run method
    """
    global _discord_bot
    
    if not _discord_bot:
        logger.error("Discord bot not set up. Call setup_discord first.")
        return
        
    token = getattr(_discord_bot, 'token', os.environ.get('DISCORD_TOKEN'))
    
    if not token:
        logger.error("Discord token is required")
        return
        
    try:
        await _discord_bot.start(token, **kwargs)
    except KeyboardInterrupt:
        logger.info("Bot stopped by keyboard interrupt")
        await _discord_bot.close()
    except Exception as e:
        logger.error(f"Error running bot: {e}")
        await _discord_bot.close()

def serialize_document(document: Dict[str, Any]) -> Dict[str, Any]:
    """
    Serialize a document with compatibility layer.
    
    Args:
        document: The document to serialize
        
    Returns:
        The serialized document
    """
    try:
        from utils.mongo_compat import serialize_document as compat_serialize
        return compat_serialize(document)
    except ImportError:
        # Basic serialization as fallback
        result = {}
        for key, value in document.items():
            if hasattr(value, '__dict__'):
                result[key] = value.__dict__
            elif isinstance(value, dict):
                result[key] = serialize_document(value)
            elif isinstance(value, list):
                result[key] = [serialize_document(item) if isinstance(item, dict) else item for item in value]
            else:
                result[key] = value
        return result
        
def deserialize_document(document: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deserialize a document with compatibility layer.
    
    Args:
        document: The document to deserialize
        
    Returns:
        The deserialized document
    """
    try:
        from utils.mongo_compat import deserialize_document as compat_deserialize
        return compat_deserialize(document)
    except ImportError:
        # No special deserialization needed for the fallback
        return document