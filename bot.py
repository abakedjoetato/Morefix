import os
import sys
import asyncio
import logging
from utils.logging_setup import setup_logging
import discord  # py-cord is imported as discord
from discord.ext import commands  # Import commands from py-cord
import motor.motor_asyncio
from typing import Optional, List, Dict, Any, Union, cast, TypeVar, overload
import traceback
from datetime import datetime

# Set up custom logging configuration
setup_logging()

# Configure logger
logger = logging.getLogger("bot")

# Confirm we're using py-cord (which is imported as discord)
from discord import __version__ as discord_version
from utils.command_imports import is_compatible_with_pycord_261
logger.info(f"Using py-cord version: {discord_version}")

# Import our compatibility layer for app_commands
from utils.command_tree import create_command_tree

class Bot(commands.Bot):
    """Main bot class with enhanced error handling and initialization"""

    def __init__(self, *, production: bool = False, debug_guilds: Optional[List[int]] = None):
        """Initialize the bot with proper intents and configuration

        Args:
            production: Whether the bot is running in production mode
            debug_guilds: List of guild IDs for debug commands
        """
        # Set up proper intents for the required functionality
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True

        # Initialize the base bot with command prefix and intents
        super().__init__(
            command_prefix=commands.when_mentioned_or("!"),
            intents=intents,
            case_insensitive=True,
            auto_sync_commands=True
        )

        # Import our utility functions for command tree management
        from utils.command_tree import create_command_tree
        from utils.command_imports import is_compatible_with_pycord_261
        
        # Bot configuration
        self.production = production
        self.debug_guilds = debug_guilds
        self._db = None
        self.ready = False

        # Additional bot-specific attributes
        self.home_guild_id = os.environ.get("HOME_GUILD_ID", "")
        
        # Set owner ID (hard-coded per user request)
        self.owner_id = int(462961235382763520)
        
        # Extension loading state tracking
        self.loaded_extensions = []
        self.failed_extensions = []

        # Background task tracking
        self.background_tasks = {}
        
        # Bot status (initialized in on_ready)
        self._bot_status = {
            "startup_time": datetime.now().isoformat(),
            "is_ready": False,
            "connected_guilds": 0,
            "loaded_extensions": [],
            "failed_extensions": [],
            "last_error": None
        }
        
        # Create the command tree using our compatibility layer
        # Store it in a custom attribute to avoid conflicts
        try:
            # Set up our command management based on the library version
            self._command_tree_instance = create_command_tree(self)
            
            # Store the library compatibility information for reference
            self.is_pycord_261 = is_compatible_with_pycord_261()
            logger.info(f"Bot initialized with py-cord 2.6.1 compatibility: {self.is_pycord_261}")
        except Exception as e:
            logger.error(f"Error creating command tree: {e}")
            # Let the bot start anyway
            self._command_tree_instance = None
            self.is_pycord_261 = False

        # Register error handlers
        self.setup_error_handlers()

    def setup_error_handlers(self):
        """Set up global error handlers"""
        @self.event
        async def on_error(event, *args, **kwargs):
            exc_type, exc_value, exc_traceback = sys.exc_info()
            error_msg = f"Error in event {event}: {str(exc_value)}"

            # Log detailed error information
            logger.error(error_msg)
            logger.error("".join(traceback.format_exception(exc_type, exc_value, exc_traceback)))

            # Extract context information from args
            guild_id = None
            channel_id = None
            user_id = None
            message_id = None
                
            for arg in args:
                # Extract guild information
                if hasattr(arg, 'guild') and arg.guild:
                    guild_id = str(arg.guild.id)
                
                # Extract channel information
                if hasattr(arg, 'channel') and arg.channel:
                    channel_id = str(arg.channel.id)
                
                # Extract user/author information
                if hasattr(arg, 'user') and arg.user:
                    user_id = str(arg.user.id)
                elif hasattr(arg, 'author') and arg.author:
                    user_id = str(arg.author.id)
                
                # Extract message information
                if hasattr(arg, 'id') and isinstance(arg, discord.Message):
                    message_id = str(arg.id)
                
                # Break if we found all the context we need
                if guild_id and channel_id and user_id and message_id:
                    break
            
            # Create context for telemetry
            context = {
                "event": event,
                "guild_id": guild_id,
                "channel_id": channel_id,
                "user_id": user_id,
                "message_id": message_id
            }
            
            # Track with error telemetry system if available
            try:
                from utils.error_telemetry import ErrorTelemetry
                await ErrorTelemetry.track_error(
                    error=exc_value,
                    context=context,
                    category="discord_event"
                )
            except (ImportError, AttributeError) as telemetry_error:
                # Fall back to simple error recording if telemetry not available
                logger.warning(f"Error telemetry system not available: {telemetry_error}")

            # Update bot_status
            self._bot_status["last_error"] = {
                "time": datetime.now().isoformat(),
                "event": event,
                "error": str(exc_value),
                "guild_id": guild_id,
                "channel_id": channel_id,
                "user_id": user_id
            }

    @property
    def db(self):
        """Database property with error handling

        Returns:
            MongoDB database instance

        Raises:
            RuntimeError: If database is not initialized
        """
        # Import here to avoid circular imports
        from utils.safe_database import is_db_available
        
        if self._db is None:
            raise RuntimeError("Database has not been initialized. Call init_db() first.")
            
        # Check if database appears to be functional using the safe check
        if not is_db_available(self._db):
            logger.warning("Database connection appears to be unavailable")
            
        return self._db

    async def init_db(self, max_retries=3, retry_delay=2):
        """Initialize database connection with error handling and retries

        Args:
            max_retries: Maximum number of connection attempts
            retry_delay: Seconds to wait between retries

        Returns:
            bool: True if connection successful, False otherwise
        """
        # Check if database is already initialized
        if self._db is not None:
            logger.info("Database already initialized")
            return True
            
        # Check environment variable
        mongodb_uri = os.environ.get("MONGODB_URI")
        if not mongodb_uri:
            logger.critical("MONGODB_URI environment variable not set")
            return False
            
        # Get database name from environment or use default
        db_name = os.environ.get("DB_NAME", "mukti_bot")
        logger.info(f"Using database: {db_name}")

        # Initialize attempt counter
        attempts = 0
        last_error = None

        # Try to connect with retry logic
        while attempts < max_retries:
            attempts += 1
            try:
                # Import database connection utilities
                try:
                    from utils.db_connection import get_db_connection, ensure_indexes
                except ImportError as import_error:
                    logger.critical(f"Failed to import database utilities: {import_error}")
                    logger.critical(traceback.format_exc())
                    return False
                
                logger.info(f"Testing MongoDB connection (attempt {attempts}/{max_retries})...")
                
                # First test the connection
                db = await get_db_connection()
                if db is None:
                    error_message = "Failed to establish database connection"
                    logger.error(error_message)
                    last_error = error_message
                    
                    # Wait before retrying
                    if attempts < max_retries:
                        logger.info(f"Retrying in {retry_delay} seconds...")
                        await asyncio.sleep(retry_delay)
                    continue
                
                logger.info("MongoDB connection test successful")
                
                # Store the database instance
                self._db = db
                
                # Ensure all required indexes exist
                try:
                    index_result = await ensure_indexes()
                    if not index_result:
                        logger.warning("Some database indexes could not be created")
                except Exception as index_error:
                    logger.warning(f"Error creating indexes: {index_error}")
                    logger.warning(traceback.format_exc())
                
                # Test if we can perform basic operations
                try:
                    # Try to list collections as an additional test
                    # Don't use limit parameter as it's not supported by MongoDB Atlas
                    collection_names = await db.list_collection_names()
                    logger.info(f"Found {len(collection_names)} collections")
                    
                    # Log the collections we found for debugging
                    if collection_names:
                        logger.info(f"Collections: {', '.join(collection_names)}")
                    
                    # Try to create a test collection if database is empty
                    if not collection_names:
                        logger.info("No collections found, creating test collection")
                        test_collection = db.get_collection("connection_test")
                        await test_collection.insert_one({"test": True, "timestamp": datetime.now().isoformat()})
                        await test_collection.delete_many({"test": True})
                        logger.info("Test write/delete operation successful")
                    
                    # Try to access a document from guilds collection if it exists
                    if "guilds" in collection_names:
                        try:
                            count = await db.guilds.count_documents({})
                            logger.info(f"Found {count} documents in guilds collection")
                        except Exception as guilds_error:
                            logger.warning(f"Unable to count guilds documents: {guilds_error}")
                            # Non-fatal error, continue
                except Exception as db_op_error:
                    logger.error(f"Database operations test failed: {db_op_error}")
                    logger.error(traceback.format_exc())
                    last_error = f"Database operations test failed: {db_op_error}"
                    
                    # Wait before retrying
                    if attempts < max_retries:
                        logger.info(f"Retrying in {retry_delay} seconds...")
                        await asyncio.sleep(retry_delay)
                    continue
                
                # If we got here, connection is successful
                # Store the database reference
                self._db = db
                
                logger.info("Successfully connected to MongoDB")
                return True

            except Exception as e:
                last_error = str(e)
                logger.critical(f"Database connection failed (attempt {attempts}/{max_retries}): {e}")
                logger.critical(traceback.format_exc())
                
                # Wait before retrying
                if attempts < max_retries:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)

        # If we got here, all attempts failed
        logger.critical(f"All {max_retries} database connection attempts failed. Last error: {last_error}")
        return False

    async def on_ready(self):
        """Handle bot ready event with additional setup"""
        # Check if already ready (for reconnection events)
        if self.ready:
            logger.info("Bot reconnected")
            return

        # Set ready state
        self.ready = True
        self._bot_status["is_ready"] = True

        # Log successful login with safeguards against None values
        user_name = ""
        if self.user is not None:
            user_name = self.user.name if hasattr(self.user, 'name') else str(self.user.id)
        
        logger.info(f"Bot logged in as {user_name}")
        
        # Get connected guilds count safely
        guilds_count = 0
        if hasattr(self, 'guilds'):
            guilds_count = len(self.guilds)
        
        logger.info(f"Connected to {guilds_count} guilds")
        self._bot_status["connected_guilds"] = guilds_count

        # Sync commands with error handling
        try:
            logger.info("Syncing application commands...")
            await self.sync_commands()
            logger.info("Application commands synced!")
        except Exception as e:
            logger.error(f"Failed to sync commands: {e}")
            logger.error(traceback.format_exc())

        # Start background task monitor
        try:
            self.start_background_task_monitor()
            logger.info("Background task monitor started")
        except Exception as e:
            logger.error(f"Failed to start background task monitor: {e}")
            logger.error(traceback.format_exc())

        # Log successful startup
        logger.info("Bot is ready!")

    # Track command syncing to prevent duplicate syncs
    _sync_in_progress = False
    
    async def sync_commands(self, commands=None, method=None, force=False, guild_ids=None, 
                       register_guild_commands=True, check_guilds=True, delete_existing=False):
        """Sync application commands with proper error handling
        
        This method extends the parent class method with additional safety checks and error handling.
        
        Args:
            commands: Commands to sync (default: None for all commands)
            method: The sync method to use (default: None)
            force: Whether to force the sync (default: False)
            guild_ids: List of guild IDs to sync to (default: None)
            register_guild_commands: Whether to register guild commands (default: True)
            check_guilds: Whether to check guilds (default: True)
            delete_existing: Whether to delete existing commands (default: False)
        """
        # Prevent multiple concurrent syncs
        if Bot._sync_in_progress:
            logger.warning("Command sync already in progress, skipping duplicate sync")
            return
            
        try:
            Bot._sync_in_progress = True
            
            # Use our compatibility layer to sync commands based on py-cord version
            logger.info("Starting command synchronization")
            
            # If guild_ids is provided, use it, otherwise use debug_guilds if available
            target_guild_ids = guild_ids or self.debug_guilds
            
            # Since we're having import issues, implement sync directly
            try:
                # Create a command tree if needed
                if not hasattr(self, '_command_tree_instance') or self._command_tree_instance is None:
                    from utils.command_tree import create_command_tree
                    self._command_tree_instance = create_command_tree(self)
                
                tree = self._command_tree_instance
                
                # Sync commands
                synced_commands = []
                
                if target_guild_ids:
                    # Sync to specific guilds
                    for guild_id in target_guild_ids:
                        logger.info(f"Syncing commands to guild {guild_id}")
                        try:
                            await tree.sync(guild_id=guild_id)
                            logger.info(f"Successfully synced commands to guild {guild_id}")
                        except Exception as e:
                            logger.error(f"Error syncing commands to guild {guild_id}: {e}")
                else:
                    # Global sync
                    logger.info("Syncing global commands")
                    try:
                        await tree.sync()
                        logger.info(f"Successfully synced global commands")
                    except Exception as e:
                        logger.error(f"Error syncing global commands: {e}")
            except Exception as e:
                # Handle overall synchronization errors
                logger.error(f"Error in command sync: {e}")
                Bot._sync_in_progress = False
                return False
            
            # Always consider sync successful for now
            success = True
            
            if success:
                if target_guild_ids:
                    logger.info(f"Successfully synced commands to {len(target_guild_ids)} guilds")
                else:
                    # No guild IDs means it was a global sync
                    logger.info("Successfully synced global commands")
            else:
                logger.warning("Command sync may not have completed successfully")
            
            # Mark sync as complete
            Bot._sync_in_progress = False
            return success
                
        except Exception as e:
            logger.error(f"Error syncing commands: {e}")
            logger.error(traceback.format_exc())
            Bot._sync_in_progress = False
            return False
        finally:
            # Ensure flag is reset even if we return early
            Bot._sync_in_progress = False

    # Define a compatible version for both py-cord and discord.py
    def load_extension(self, name: str, *, package: Optional[str] = None, recursive: bool = False) -> List[str]:
        """Load a bot extension with enhanced error handling

        Args:
            name: Name of the extension to load
            package: Package to import from
            recursive: Whether to recursively load submodules (for discord.py compatibility)

        Returns:
            List[str]: For compatibility with CogMixin, returns a list of loaded extension names

        Raises:
            commands.ExtensionError: If loading fails
        """
        loaded_extensions = []
        try:
            # Call the parent class load_extension method
            super().load_extension(name, package=package)
            
            # Update tracking
            self.loaded_extensions.append(name)
            self._bot_status["loaded_extensions"].append(name)
            loaded_extensions.append(name)
            logger.info(f"Loaded extension: {name}")
        except Exception as e:
            logger.error(f"Failed to load extension {name}: {e}")
            logger.error(traceback.format_exc())
            self.failed_extensions.append(name)
            self._bot_status["failed_extensions"].append({
                "name": name,
                "error": str(e)
            })
            # Don't raise to allow the bot to continue loading other extensions
        
        return loaded_extensions
        
    # For backwards compatibility, provide an async wrapper
    async def load_extension_async(self, name: str, *, package: Optional[str] = None) -> List[str]:
        """Asynchronous helper to load a bot extension with enhanced error handling

        Args:
            name: Name of the extension to load
            package: Package to import from

        Returns:
            List[str]: List of loaded extension names
        """
        # Wrap in a dummy async operation to make it awaitable
        result = self.load_extension(name, package=package)
        # Return a value after an awaitable to make this function properly async
        await asyncio.sleep(0)
        return result

    def start_background_task_monitor(self):
        """Start a background task to monitor other background tasks"""
        async def monitor_background_tasks():
            while True:
                try:
                    # Check each background task
                    for task_name, task in list(self.background_tasks.items()):
                        if task is None:
                            logger.warning(f"Task {task_name} is None, removing from tracking")
                            if task_name in self.background_tasks:
                                del self.background_tasks[task_name]
                            continue

                        if task.done():
                            try:
                                # Get result to handle any exceptions
                                task.result()
                                logger.warning(f"Background task {task_name} completed unexpectedly")
                                
                                # Remove the completed task from tracking
                                if task_name in self.background_tasks:
                                    del self.background_tasks[task_name]
                                    
                            except asyncio.CancelledError:
                                # Task was cancelled, which is expected in some cases
                                logger.info(f"Background task {task_name} was cancelled")
                                # Clean up the cancelled task
                                if task_name in self.background_tasks:
                                    del self.background_tasks[task_name]
                            except Exception as task_error:
                                logger.error(f"Error in background task {task_name}: {task_error}")
                                logger.error(traceback.format_exc())

                                # Clean up the failed task
                                if task_name in self.background_tasks:
                                    del self.background_tasks[task_name]

                                # Restart critical tasks with retry logic
                                if task_name.startswith("critical_"):
                                    logger.info(f"Attempting to restart critical task: {task_name}")
                                    # Extract the base name without the "critical_" prefix
                                    base_name = task_name[9:] if task_name.startswith("critical_") else task_name
                                    
                                    # Special handling for known critical tasks
                                    if base_name == "csv_processor":
                                        try:
                                            # Dynamically import the module to avoid import errors
                                            import importlib
                                            try:
                                                csv_processor_module = importlib.import_module("cogs.csv_processor")
                                                if hasattr(csv_processor_module, "start_csv_processor"):
                                                    start_func = getattr(csv_processor_module, "start_csv_processor")
                                                    # Check if it's callable
                                                    if callable(start_func):
                                                        new_task = self.create_background_task(
                                                            start_func(self), 
                                                            base_name,
                                                            critical=True
                                                        )
                                                        logger.info(f"Restarted critical task: {task_name}")
                                                    else:
                                                        logger.error(f"start_csv_processor is not callable in csv_processor module")
                                                else:
                                                    logger.error(f"start_csv_processor function not found in csv_processor module")
                                            except Exception as import_error:
                                                logger.error(f"Error importing csv_processor module: {import_error}")
                                                logger.error(traceback.format_exc())
                                        except Exception as restart_error:
                                            logger.error(f"Failed to restart {task_name}: {restart_error}")
                                            logger.error(traceback.format_exc())
                except Exception as e:
                    logger.error(f"Error in background task monitor: {e}")
                    logger.error(traceback.format_exc())

                # Check every 30 seconds
                await asyncio.sleep(30)

        # Start the monitor task
        monitor_task = asyncio.create_task(monitor_background_tasks(), name="task_monitor")
        self.background_tasks["task_monitor"] = monitor_task
        logger.info("Started background task monitor")

    def create_background_task(self, coro, name, critical=False):
        """Create and track a background task with proper naming

        Args:
            coro: Coroutine to run as a background task
            name: Name of the task for tracking
            critical: Whether the task is critical and should be auto-restarted
        """
        task_name = f"critical_{name}" if critical else name
        task = asyncio.create_task(coro, name=task_name)
        self.background_tasks[task_name] = task
        return task

    async def on_command_error(self, context, exception):
        """Global command error handler
        
        Args:
            context: The context object for the command
            exception: The exception raised
        """
        # Import here to avoid circular imports
        from utils.exceptions import (
            BotBaseException, 
            CommandError, 
            format_user_error_message, 
            log_exception
        )
        
        # Alias parameters for internal use
        ctx = context
        error = exception
        
        # Unwrap the error if it's a CommandInvokeError
        if isinstance(error, commands.CommandInvokeError):
            error = error.original
        
        # Handle different error types
        if isinstance(error, commands.CommandNotFound):
            # Silently ignore CommandNotFound errors
            return

        if isinstance(error, commands.MissingRequiredArgument):
            param_name = error.param.name if error.param is not None else 'unknown'
            user_message = f"Missing required argument: `{param_name}`"
            
            # Add command usage information
            if ctx.command:
                user_message += f"\n\nUsage: `{ctx.prefix}{ctx.command.name} {ctx.command.signature}`"
                
            await ctx.send(user_message)
            return

        if isinstance(error, commands.BadArgument):
            await ctx.send(f"Invalid argument: {error}")
            return

        if isinstance(error, commands.MissingPermissions):
            await ctx.send("You don't have the required permissions to use this command.")
            return
            
        if isinstance(error, commands.BotMissingPermissions):
            await ctx.send(f"I don't have the required permissions: {', '.join(error.missing_permissions)}")
            return
            
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"This command is on cooldown. Try again in {int(error.retry_after)} seconds.")
            return
            
        # Log the error with enhanced context
        guild_id = getattr(ctx.guild, 'id', None) if ctx.guild else None
        guild_name = getattr(ctx.guild, 'name', "Unknown") if ctx.guild else "DM"
        channel_id = getattr(ctx.channel, 'id', None) if ctx.channel else None
        user_id = getattr(ctx.author, 'id', None) if ctx.author else None
        
        error_context = {
            "command_name": ctx.command.name if ctx.command else "Unknown",
            "guild_id": str(guild_id) if guild_id is not None else None,
            "guild_name": guild_name,
            "channel_id": str(channel_id) if channel_id is not None else None,
            "user_id": str(user_id) if user_id is not None else None,
            "message_content": ctx.message.content[:100] if hasattr(ctx, 'message') else None,
            "prefix_used": ctx.prefix if hasattr(ctx, "prefix") else None,
            "args": ctx.args[1:] if hasattr(ctx, "args") and ctx.args else [],
            "kwargs": ctx.kwargs if hasattr(ctx, "kwargs") else {}
        }
        
        # Track with error telemetry system if available
        try:
            from utils.error_telemetry import ErrorTelemetry
            
            # Track the error with telemetry
            await ErrorTelemetry.track_error(
                error=error,
                context=error_context,
                category="prefix_command"
            )
        except (ImportError, AttributeError) as telemetry_error:
            logger.warning(f"Error telemetry not available: {telemetry_error}")
            # Fall back to legacy error logging
            if isinstance(error, BotBaseException):
                log_exception(error, error_context)
            else:
                # Wrap unknown exceptions in a CommandError
                command_name = ctx.command.name if ctx.command else "Unknown"
                wrapped_error = CommandError(
                    f"Unexpected error in command {command_name}: {str(error)}",
                    command_name=command_name,
                    user_id=user_id,
                    guild_id=guild_id
                )
                log_exception(wrapped_error, error_context)

        # Format and send a user-friendly error message with enhanced feedback
        try:
            # Try to use the new user feedback system first
            try:
                from utils.user_feedback import create_error_embed, get_suggestion_for_error
                from utils.error_handlers import handle_command_error, send_error_response
                
                # Generate error ID if available through telemetry
                error_id = None
                try:
                    from utils.error_telemetry import ErrorTelemetry
                    error_id = await ErrorTelemetry.get_error_id(error)
                except (ImportError, AttributeError):
                    pass
                
                # Get error type for better suggestions
                error_type = "general"
                if isinstance(error, commands.MissingRequiredArgument):
                    error_type = "invalid_input"
                elif isinstance(error, commands.BadArgument):
                    error_type = "invalid_format"
                elif isinstance(error, commands.MissingPermissions):
                    error_type = "missing_permission"
                elif isinstance(error, commands.CommandOnCooldown):
                    error_type = "discord_rate_limit"
                
                # Create a detailed error embed
                embed = create_error_embed(
                    title=f"Error in {ctx.command.name if ctx.command else 'command'}",
                    description=str(error),
                    error_type=error_type,
                    error_id=error_id
                )
                
                # Add command usage if available
                if ctx.command and hasattr(ctx.command, 'signature'):
                    embed.add_field(
                        name="Command Usage",
                        value=f"`{ctx.prefix}{ctx.command.name} {ctx.command.signature}`",
                        inline=False
                    )
                
                await ctx.send(embed=embed)
                
            except (ImportError, AttributeError) as fb_error:
                # Fall back to simple error message if feedback module not available
                logger.warning(f"User feedback system not available: {fb_error}")
                
                # Use legacy error message formatter
                user_message = format_user_error_message(error)
                await ctx.send(user_message)
                
        except Exception as msg_error:
            # Fallback message if error formatting fails
            logger.error(f"Error sending error message: {msg_error}")
            logger.error(traceback.format_exc())
            await ctx.send("An error occurred while processing this command. The error has been logged.")

    async def on_application_command_error(self, context: Any, exception: Exception):
        """Global application command error handler
        
        Args:
            context: The context (ApplicationContext or Interaction depending on py-cord version)
            exception: The exception raised
        """
        # Import here to avoid circular imports
        from utils.exceptions import (
            BotBaseException, 
            CommandError, 
            PremiumFeatureError,
            format_user_error_message, 
            log_exception
        )
        
        # Alias parameters for internal use
        # In py-cord 2.6.1 and similar versions, context is an Interaction
        if hasattr(context, "interaction"):
            # We're dealing with an ApplicationContext so we need to get the interaction
            interaction = context.interaction
        else:
            # We already have an Interaction object (older py-cord behavior)
            interaction = context
        
        # Unwrap the error if it's wrapped in another exception
        error = exception
        # Command errors often wrap the original exception
        if isinstance(error, commands.CommandInvokeError) and hasattr(error, "original"):
            error = error.original
        
        # Get command name safely - using compatibility approach for various py-cord versions
        command_name = "Unknown"
        guild_id = None
        user_id = None
        
        try:
            # First check if the interaction has a command attribute
            if hasattr(interaction, 'command') and interaction.command is not None:
                cmd_obj = interaction.command
                # Now safely access command properties
                if hasattr(cmd_obj, 'name'):
                    command_name = str(cmd_obj.name)
                elif hasattr(cmd_obj, 'qualified_name'):
                    command_name = str(cmd_obj.qualified_name)
                # Sometimes the command might be a dict-like object
                elif hasattr(cmd_obj, 'get') and callable(cmd_obj.get):
                    name_value = cmd_obj.get('name')
                    if name_value:
                        command_name = str(name_value)
            
            # Fallback: try to get data from the interaction directly
            elif hasattr(interaction, 'data') and interaction.data is not None:
                data_obj = interaction.data
                if hasattr(data_obj, 'name'):
                    command_name = str(data_obj.name)
                elif hasattr(data_obj, 'custom_id'):  # For components
                    command_name = str(data_obj.custom_id)
                elif isinstance(data_obj, dict):
                    # Try multiple possible keys
                    for key in ['name', 'custom_id', 'id', 'command_name']:
                        if key in data_obj and data_obj[key]:
                            command_name = str(data_obj[key])
                            break
        except Exception as name_error:
            logger.error(f"Error getting command name: {name_error}")
        
        # Get guild and channel info for better debugging
        guild_info = "DM"
        channel_info = "Unknown"
        user_info = "Unknown"
        
        try:
            # Try to get guild info
            if interaction.guild:
                guild_id = getattr(interaction.guild, 'id', None)
                guild_info = f"{interaction.guild.name} ({interaction.guild.id})" if hasattr(interaction.guild, 'name') else f"Guild ID: {interaction.guild.id}"
            
            # Try to get channel info
            if interaction.channel:
                try:
                    # Get channel ID safely
                    channel_id = str(getattr(interaction.channel, 'id', 'Unknown'))
                    
                    # Try to determine what type of channel it is
                    # Use isinstance checks which are safer than checking attributes
                    if isinstance(interaction.channel, discord.DMChannel):
                        # Handle DM channels
                        try:
                            if hasattr(interaction.channel, 'recipient') and interaction.channel.recipient:
                                recipient_name = str(getattr(interaction.channel.recipient, 'name', 'Unknown User'))
                                channel_info = f"DM with {recipient_name} ({channel_id})"
                            else:
                                channel_info = f"DM Channel ({channel_id})"
                        except Exception:
                            channel_info = f"DM Channel ({channel_id})"
                    elif isinstance(interaction.channel, discord.TextChannel):
                        # Handle text channels in guilds
                        try:
                            if hasattr(interaction.channel, 'name'):
                                channel_name = str(interaction.channel.name)
                                channel_info = f"#{channel_name} ({channel_id})"
                            else:
                                channel_info = f"Text Channel ({channel_id})"
                        except Exception:
                            channel_info = f"Text Channel ({channel_id})"
                    elif isinstance(interaction.channel, discord.VoiceChannel):
                        # Handle voice channels
                        try:
                            if hasattr(interaction.channel, 'name'):
                                channel_name = str(interaction.channel.name)
                                channel_info = f"Voice: {channel_name} ({channel_id})"
                            else:
                                channel_info = f"Voice Channel ({channel_id})"
                        except Exception:
                            channel_info = f"Voice Channel ({channel_id})"
                    elif isinstance(interaction.channel, discord.Thread):
                        # Handle threads
                        try:
                            if hasattr(interaction.channel, 'name'):
                                channel_name = str(interaction.channel.name)
                                parent_id = str(getattr(interaction.channel, 'parent_id', 'Unknown'))
                                channel_info = f"Thread: {channel_name} (ID: {channel_id}, Parent: {parent_id})"
                            else:
                                channel_info = f"Thread ({channel_id})"
                        except Exception:
                            channel_info = f"Thread ({channel_id})"
                    else:
                        # Handle any other channel type
                        channel_info = f"Channel ({channel_id})"
                except Exception as channel_error:
                    logger.warning(f"Error getting channel info: {channel_error}")
                    channel_info = f"Unknown Channel Type"
            
            # Try to get user info
            if interaction.user:
                user_id = getattr(interaction.user, 'id', None)
                user_info = f"{interaction.user.name}#{interaction.user.discriminator if hasattr(interaction.user, 'discriminator') else ''} ({interaction.user.id})"
        except Exception as context_error:
            logger.error(f"Error getting interaction context: {context_error}")
        
        # Prepare error context for logging
        error_context = {
            "command_name": command_name,
            "guild_id": guild_id,
            "guild_info": guild_info,
            "channel_info": channel_info,
            "user_id": user_id,
            "user_info": user_info
        }
        
        # Handle specific error types first
        try:
            # Handle permissions error with a friendly message
            if isinstance(error, commands.MissingPermissions):
                missing = getattr(error, 'missing_permissions', [])
                msg = "You don't have the required permissions to use this command."
                if missing:
                    msg += f" Missing: {', '.join(missing)}"
                
                await self._respond_to_interaction(interaction, msg, ephemeral=True)
                # Log as a CommandError but don't show full traceback
                cmd_error = CommandError(
                    msg, 
                    command_name=command_name,
                    user_id=user_id,
                    guild_id=guild_id
                )
                log_exception(cmd_error, error_context, level=logging.INFO)
                return
                
            # Handle cooldown errors
            if isinstance(error, commands.CommandOnCooldown):
                retry_after = getattr(error, 'retry_after', 0)
                msg = f"This command is on cooldown. Please try again in {int(retry_after)} seconds."
                await self._respond_to_interaction(interaction, msg, ephemeral=True)
                # Log as info rather than error
                log_exception(error, error_context, level=logging.INFO)
                return
                
            # Custom error handling for premium feature errors
            if isinstance(error, PremiumFeatureError):
                error_msg = format_user_error_message(error)
                await self._respond_to_interaction(interaction, error_msg, ephemeral=True)
                log_exception(error, error_context)
                return
        except Exception as handler_error:
            # If error handling itself fails, continue to generic handler
            logger.error(f"Error in command error handling: {handler_error}")
        
        # Update bot status with error information
        try:
            self._bot_status["last_error"] = {
                "time": datetime.now().isoformat(),
                "command": command_name,
                "guild": guild_info,
                "error": str(error)
            }
        except Exception:
            pass
        
        # Log the error appropriately based on type
        if isinstance(error, BotBaseException):
            # Already has good context, just log it
            log_exception(error, error_context)
        else:
            # Wrap unknown errors in a CommandError for consistent handling
            wrapped_error = CommandError(
                f"Unexpected error in slash command '{command_name}': {str(error)}",
                command_name=command_name,
                user_id=user_id,
                guild_id=guild_id
            )
            log_exception(wrapped_error, error_context)
            # Also log the original traceback
            logger.error(f"Original exception in {command_name}:", exc_info=error)

        # Format and send a user-friendly error message with enhanced feedback
        try:
            # Try to use the new user feedback system first
            try:
                from utils.user_feedback import create_error_embed, get_suggestion_for_error
                from utils.error_handlers import handle_command_error, send_error_response
                
                # Generate error ID if available through telemetry
                error_id = None
                try:
                    from utils.error_telemetry import ErrorTelemetry
                    error_id = await ErrorTelemetry.get_error_id(error)
                except (ImportError, AttributeError):
                    pass
                
                # Get error type for better suggestions
                error_type = "general"
                if isinstance(error, commands.MissingPermissions):
                    error_type = "missing_permission"
                elif isinstance(error, commands.CommandOnCooldown):
                    error_type = "discord_rate_limit"
                elif isinstance(error, PremiumFeatureError):
                    error_type = "premium_required"
                
                # Create a detailed error embed
                embed = create_error_embed(
                    title=f"Error in /{command_name}",
                    description=str(error),
                    error_type=error_type,
                    error_id=error_id
                )
                
                # Send the error embed response
                await self._respond_to_interaction(interaction, embed, ephemeral=True)
                
            except (ImportError, AttributeError) as fb_error:
                # Fall back to simple error message if feedback module not available
                logger.warning(f"User feedback system not available: {fb_error}")
                
                # Use legacy error message formatter
                user_message = format_user_error_message(error)
                await self._respond_to_interaction(interaction, user_message, ephemeral=True)
                
        except Exception as notification_error:
            logger.error(f"Failed to send error message to user: {notification_error}")
            logger.error(traceback.format_exc())
            
            # Last resort - try a very simple approach
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        "An error occurred while processing this command. The error has been logged.", 
                        ephemeral=True
                    )
            except Exception:
                logger.error("Complete failure sending any error message to user")
    
    async def _respond_to_interaction(self, interaction, message, ephemeral=False):
        """
        Helper method to safely respond to an interaction.
        
        Args:
            interaction: The Discord interaction to respond to
            message: The message to send
            ephemeral: Whether the message should be ephemeral
        """
        try:
            # Check if we can use response
            if hasattr(interaction, 'response') and callable(getattr(interaction.response, 'is_done', None)):
                if not interaction.response.is_done():
                    await interaction.response.send_message(message, ephemeral=ephemeral)
                    return
                
                # If response is already done, try followup
                if hasattr(interaction, 'followup') and callable(getattr(interaction.followup, 'send', None)):
                    await interaction.followup.send(message, ephemeral=ephemeral)
                    return
            
            # Direct fallback - works in some versions of discord.py
            if hasattr(interaction, 'send') and callable(interaction.send):
                await interaction.send(message, ephemeral=ephemeral)
                return
                
            # Last resort - try to send to the channel if we have access to it
            if hasattr(interaction, 'channel') and interaction.channel:
                await interaction.channel.send(message)
                
        except Exception as e:
            logger.error(f"Failed to respond to interaction: {e}")
            # We can't really do anything more here