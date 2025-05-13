"""
Error Telemetry for Tower of Temptation PvP Statistics Bot

This module provides centralized error tracking and analysis:
1. Error aggregation and categorization
2. Frequency tracking and pattern detection
3. Context collection for debugging
4. Error reporting for administrators

The system helps identify common issues and improve user experience.
"""
import os
import sys
import logging
import traceback
import asyncio
import re
import json
import datetime
import uuid
import hashlib
from typing import Dict, List, Any, Optional, Union, Set, Tuple, Callable
from collections import defaultdict, Counter
from datetime import datetime, timedelta
import inspect
import functools

# Configure module-specific logger
logger = logging.getLogger(__name__)

# Initialize global state
_error_telemetry_enabled = True
_telemetry_initialized = False
_error_categories = set()
_category_patterns = {}
_db = None  # Will be set during initialization
_background_task = None
_error_buffer = []
_buffer_lock = asyncio.Lock()
_stats = {
    "errors_tracked": 0,
    "errors_aggregated": 0,
    "flush_count": 0,
    "last_flush": None
}

# Constants
MAX_BUFFER_SIZE = 100
FLUSH_INTERVAL = 60  # seconds
MAX_CONTEXT_SIZE = 10240  # bytes
MAX_ERROR_HISTORY = 1000  # per category
ERROR_RECORD_TTL = 30  # days to keep error records

# Define standard error categories
STANDARD_CATEGORIES = {
    "discord_api": [
        r"(?i)discord\..*error",
        r"(?i)discord.*rate.?limit",
        r"(?i)interaction.*failed",
        r"(?i)webhook.*failed",
        r"(?i)discord\..*exception"
    ],
    "database": [
        r"(?i)mongo.*error",
        r"(?i)database.*error",
        r"(?i)connection.*refused",
        r"(?i)mongodb.*exception"
    ],
    "sftp": [
        r"(?i)sftp.*error",
        r"(?i)sftp.*timeout",
        r"(?i)sftp.*connection.*failed",
        r"(?i)sftp.*authentication"
    ],
    "permission": [
        r"(?i)permission.*denied",
        r"(?i)missing.*permission",
        r"(?i)not.*authorized"
    ],
    "validation": [
        r"(?i)invalid.*format",
        r"(?i)validation.*failed",
        r"(?i)invalid.*parameter"
    ],
    "file_system": [
        r"(?i)file.*not.*found",
        r"(?i)directory.*not.*found",
        r"(?i)permission.*denied"
    ],
    "timeout": [
        r"(?i)timeout",
        r"(?i)timed.*out",
        r"(?i)took.*too.*long"
    ],
    "rate_limit": [
        r"(?i)rate.*limited",
        r"(?i)too.*many.*requests",
        r"(?i)slow.*down"
    ],
    "api_error": [
        r"(?i)api.*error",
        r"(?i)request.*failed",
        r"(?i)status.*code.*(4|5)\d{2}"
    ],
    "uncategorized": [
        r".*"  # Match anything that wasn't caught by other categories
    ]
}

# Error Context Extractor Functions
def extract_discord_context(error, context):
    """Extract Discord-specific information for context"""
    discord_context = {}
    
    # Try to extract interaction information if available
    if 'interaction' in context:
        interaction = context['interaction']
        try:
            discord_context['guild_id'] = str(interaction.guild.id) if interaction.guild else None
            discord_context['channel_id'] = str(interaction.channel.id) if interaction.channel else None
            discord_context['user_id'] = str(interaction.user.id) if interaction.user else None
            discord_context['command'] = interaction.command.name if hasattr(interaction, 'command') and interaction.command else None
        except Exception:
            pass
    
    # Try to extract message information if available
    if 'message' in context:
        message = context['message']
        try:
            discord_context['guild_id'] = str(message.guild.id) if message.guild else None
            discord_context['channel_id'] = str(message.channel.id) if message.channel else None
            discord_context['author_id'] = str(message.author.id) if message.author else None
            discord_context['message_content'] = message.content[:100] if message.content else None
        except Exception:
            pass
    
    return discord_context

def extract_database_context(error, context):
    """Extract database-specific information for context"""
    db_context = {}
    
    # Try to extract collection information
    if 'collection' in context:
        db_context['collection'] = context['collection']
    
    # Try to extract operation information
    if 'operation' in context:
        db_context['operation'] = context['operation']
    
    # Check for MongoDB error codes
    error_str = str(error)
    code_match = re.search(r'code\s*:\s*(\d+)', error_str)
    if code_match:
        db_context['error_code'] = int(code_match.group(1))
    
    return db_context

def extract_sftp_context(error, context):
    """Extract SFTP-specific information for context"""
    sftp_context = {}
    
    # Check if the error has sftp-related details
    if 'sftp_host' in context:
        sftp_context['host'] = context['sftp_host']
    if 'sftp_operation' in context:
        sftp_context['operation'] = context['sftp_operation']
    if 'sftp_path' in context:
        sftp_context['path'] = context['sftp_path']
    
    return sftp_context

# Dictionary of context extractors by category
CONTEXT_EXTRACTORS = {
    "discord_api": extract_discord_context,
    "database": extract_database_context,
    "sftp": extract_sftp_context,
}

# Error fingerprinting functions
def get_error_fingerprint(error, error_type=None, error_message=None):
    """Generate a unique fingerprint for an error
    
    This creates a hash that can be used to identify similar errors.
    
    Args:
        error: The exception object
        error_type: Optional explicit error type
        error_message: Optional explicit error message
    
    Returns:
        A string hash that identifies this error pattern
    """
    # Get the error type and message if not provided
    if error_type is None:
        error_type = type(error).__name__
    
    if error_message is None:
        error_message = str(error)
    
    # Get the traceback info
    tb = traceback.extract_tb(error.__traceback__) if hasattr(error, '__traceback__') and error.__traceback__ else []
    
    # Create a simplified traceback representation for fingerprinting
    # We only include filenames and line numbers, not the full paths
    tb_simplified = []
    for frame in tb:
        # Include only the filename, not the full path
        filename = os.path.basename(frame.filename) if frame.filename else "unknown"
        tb_simplified.append(f"{filename}:{frame.lineno}")
    
    # Create a string to hash by combining error type and simplified traceback
    if tb_simplified:
        fingerprint_base = f"{error_type}:{':'.join(tb_simplified[-3:])}"  # Last 3 frames
    else:
        # If no traceback, just use the error type and a normalized message
        # Normalize the message by removing specific values like IDs, timestamps
        normalized_message = re.sub(r'\b\d{6,}\b', 'ID', error_message)  # Replace numeric IDs
        normalized_message = re.sub(r'\d{4}-\d{2}-\d{2}', 'DATE', normalized_message)  # Replace dates
        fingerprint_base = f"{error_type}:{normalized_message[:100]}"
    
    # Create a stable hash for the fingerprint
    fingerprint = hashlib.md5(fingerprint_base.encode()).hexdigest()
    
    return fingerprint

def normalize_error_message(error_message):
    """Normalize an error message by removing variable data
    
    Args:
        error_message: The error message to normalize
    
    Returns:
        A normalized error message with specific IDs, dates, etc. replaced
    """
    if not error_message:
        return "Unknown error"
    
    # Limit length
    error_message = error_message[:200]
    
    # Replace specific IDs with placeholders
    normalized = re.sub(r'\b\d{6,}\b', '<ID>', error_message)
    
    # Replace dates
    normalized = re.sub(r'\d{4}-\d{2}-\d{2}', '<DATE>', normalized)
    
    # Replace times
    normalized = re.sub(r'\d{2}:\d{2}:\d{2}', '<TIME>', normalized)
    
    # Replace file paths
    normalized = re.sub(r'(\/[\w\.]+)+\/?', '<PATH>', normalized)
    
    # Replace URLs
    normalized = re.sub(r'https?:\/\/[^\s]+', '<URL>', normalized)
    
    # Replace IP addresses
    normalized = re.sub(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', '<IP>', normalized)
    
    return normalized

def categorize_error(error, context=None):
    """Determine the category of an error
    
    Args:
        error: The error object or string
        context: Optional context dictionary
    
    Returns:
        The error category string
    """
    global _category_patterns
    
    # Get the error message
    if isinstance(error, Exception):
        error_type = type(error).__name__
        error_message = str(error)
    else:
        error_type = "Unknown"
        error_message = str(error)
    
    # Combine for pattern matching
    error_string = f"{error_type}: {error_message}"
    
    # Check for explicit category in context
    if context and 'category' in context:
        return context['category']
    
    # Try to match against patterns
    for category, patterns in _category_patterns.items():
        for pattern in patterns:
            if re.search(pattern, error_string):
                return category
    
    # Default to uncategorized
    return "uncategorized"

class ErrorTelemetry:
    """Error telemetry manager for tracking and analyzing errors"""
    
    def __init__(self, db=None):
        """Initialize error telemetry
        
        Args:
            db: Database instance for storing error data
        """
        global _db, _telemetry_initialized, _category_patterns
        
        if _telemetry_initialized:
            logger.debug("Error telemetry already initialized")
            return
        
        logger.info("Initializing error telemetry")
        
        # Store database reference
        _db = db
        
        # Initialize category patterns
        _category_patterns = STANDARD_CATEGORIES.copy()
        
        # Mark as initialized
        _telemetry_initialized = True
    
    @classmethod
    async def get_error_id(cls, error):
        """Get a unique identifier for an error
        
        Args:
            error: The error object
            
        Returns:
            String identifier for the error
        """
        if isinstance(error, Exception):
            # Use error fingerprinting to generate ID
            return get_error_fingerprint(error)
        
        # For non-exception errors, generate a simple hash
        return hashlib.md5(str(error).encode()).hexdigest()
    
    @staticmethod
    async def track_error(error, context=None, category=None, flush=False):
        """Track an error with context
        
        Args:
            error: The error object or string
            context: Optional dictionary with additional context
            category: Optional explicit category for this error
            flush: Whether to flush the buffer immediately
            
        Returns:
            Error record ID
        """
        global _error_buffer, _stats
        
        if not _error_telemetry_enabled:
            return None
        
        # Ensure context is a dictionary
        if context is None:
            context = {}
        
        # Determine error details
        if isinstance(error, Exception):
            error_type = type(error).__name__
            error_message = str(error)
            error_traceback = traceback.format_exception(type(error), error, error.__traceback__)
            error_traceback_str = ''.join(error_traceback)
        else:
            error_type = "Unknown"
            error_message = str(error)
            error_traceback_str = ''.join(traceback.format_stack())
        
        # Determine category
        if category is None:
            category = categorize_error(error, context)
        
        # Generate fingerprint
        fingerprint = get_error_fingerprint(error, error_type, error_message)
        
        # Create error record
        timestamp = datetime.utcnow()
        record_id = str(uuid.uuid4())
        
        # Extract additional context based on category
        extracted_context = {}
        if category in CONTEXT_EXTRACTORS:
            try:
                extracted_context = CONTEXT_EXTRACTORS[category](error, context)
            except Exception as e:
                logger.warning(f"Failed to extract context for {category}: {e}")
        
        # Merge contexts, with explicit context taking precedence
        merged_context = {**extracted_context, **context}
        
        # Ensure context is serializable and limit size
        safe_context = {}
        context_size = 0
        for k, v in merged_context.items():
            try:
                # Skip complex objects that can't be easily serialized
                if callable(v) or inspect.isclass(v) or inspect.ismodule(v):
                    continue
                    
                # Convert to string and limit size
                v_str = str(v)
                if len(v_str) > 1000:
                    v_str = v_str[:1000] + "..."
                    
                safe_context[k] = v_str
                context_size += len(k) + len(v_str)
                
                # Stop if context gets too large
                if context_size > MAX_CONTEXT_SIZE:
                    safe_context["_truncated"] = True
                    break
            except Exception:
                continue
        
        # Create the error record
        error_record = {
            "id": record_id,
            "timestamp": timestamp,
            "category": category,
            "error_type": error_type,
            "error_message": error_message,
            "fingerprint": fingerprint,
            "traceback": error_traceback_str[:10000] if len(error_traceback_str) > 10000 else error_traceback_str,
            "context": safe_context,
            "normalized_message": normalize_error_message(error_message)
        }
        
        # Add to buffer
        async with _buffer_lock:
            _error_buffer.append(error_record)
            _stats["errors_tracked"] += 1
            
            # Flush if buffer is full or explicitly requested
            if flush or len(_error_buffer) >= MAX_BUFFER_SIZE:
                await ErrorTelemetry.flush_error_buffer()
        
        return record_id
    
    @staticmethod
    async def flush_error_buffer():
        """Flush the error buffer to the database"""
        global _error_buffer, _db, _stats
        
        if _db is None:
            logger.warning("Cannot flush error buffer: database not initialized")
            return False
        
        async with _buffer_lock:
            if not _error_buffer:
                return True
            
            buffer_copy = _error_buffer.copy()
            _error_buffer = []
        
        # Skip further processing if no buffer
        if not buffer_copy:
            return True
        
        try:
            # Try to store errors in the database
            errors_collection = _db.errors
            
            # First aggregate errors by fingerprint
            errors_by_fingerprint = defaultdict(list)
            for error in buffer_copy:
                errors_by_fingerprint[error["fingerprint"]].append(error)
            
            # Process each fingerprint
            for fingerprint, errors in errors_by_fingerprint.items():
                # Get the first error as a reference
                reference_error = errors[0]
                
                # Check if this fingerprint already exists in the database
                existing = await errors_collection.find_one({"fingerprint": fingerprint})
                
                if existing:
                    # Update the existing record
                    update = {
                        "$inc": {"occurrence_count": len(errors)},
                        "$set": {
                            "last_seen": reference_error["timestamp"],
                            "last_error_id": reference_error["id"],
                            "last_message": reference_error["error_message"],
                            "last_traceback": reference_error["traceback"],
                            "last_context": reference_error["context"]
                        },
                        "$push": {
                            "recent_occurrences": {
                                "$each": [
                                    {
                                        "timestamp": e["timestamp"],
                                        "error_id": e["id"],
                                        "context": e["context"]
                                    } for e in errors
                                ],
                                "$slice": -MAX_ERROR_HISTORY
                            }
                        }
                    }
                    
                    await errors_collection.update_one(
                        {"fingerprint": fingerprint},
                        update
                    )
                else:
                    # Create a new aggregated record
                    aggregated_record = {
                        "fingerprint": fingerprint,
                        "category": reference_error["category"],
                        "error_type": reference_error["error_type"],
                        "first_seen": reference_error["timestamp"],
                        "last_seen": reference_error["timestamp"],
                        "occurrence_count": len(errors),
                        "error_message": reference_error["error_message"],
                        "normalized_message": reference_error["normalized_message"],
                        "last_error_id": reference_error["id"],
                        "last_message": reference_error["error_message"],
                        "last_traceback": reference_error["traceback"],
                        "last_context": reference_error["context"],
                        "recent_occurrences": [
                            {
                                "timestamp": e["timestamp"],
                                "error_id": e["id"],
                                "context": e["context"]
                            } for e in errors
                        ]
                    }
                    
                    await errors_collection.insert_one(aggregated_record)
            
            # Update stats
            _stats["errors_aggregated"] += len(buffer_copy)
            _stats["flush_count"] += 1
            _stats["last_flush"] = datetime.utcnow()
            
            logger.debug(f"Flushed {len(buffer_copy)} errors to database")
            return True
            
        except Exception as e:
            logger.error(f"Error flushing telemetry buffer: {e}")
            
            # Re-add errors to buffer if they couldn't be stored
            async with _buffer_lock:
                # Only keep up to the maximum size to prevent infinite growth
                combined = buffer_copy + _error_buffer
                if len(combined) > MAX_BUFFER_SIZE * 2:
                    combined = combined[-MAX_BUFFER_SIZE * 2:]
                _error_buffer = combined
            
            return False
    
    @staticmethod
    async def get_error_stats(category=None, days=7):
        """Get error statistics
        
        Args:
            category: Optional category to filter by
            days: Number of days to look back
        
        Returns:
            Dictionary with error statistics
        """
        if _db is None:
            return {"error": "Database not initialized"}
        
        stats = {}
        
        try:
            errors_collection = _db.errors
            
            # Build query
            query = {}
            if category:
                query["category"] = category
            
            if days:
                cutoff_date = datetime.utcnow() - timedelta(days=days)
                query["last_seen"] = {"$gte": cutoff_date}
            
            # Get total count
            stats["total_errors"] = await errors_collection.count_documents(query)
            
            # Get count by category
            category_counts = []
            pipeline = [
                {"$match": query},
                {"$group": {"_id": "$category", "count": {"$sum": 1}}}
            ]
            
            async for doc in errors_collection.aggregate(pipeline):
                category_counts.append({
                    "category": doc["_id"],
                    "count": doc["count"]
                })
            
            stats["categories"] = category_counts
            
            # Get most frequent errors
            most_frequent = []
            pipeline = [
                {"$match": query},
                {"$sort": {"occurrence_count": -1}},
                {"$limit": 10},
                {"$project": {
                    "fingerprint": 1,
                    "category": 1,
                    "error_type": 1,
                    "normalized_message": 1,
                    "occurrence_count": 1,
                    "last_seen": 1
                }}
            ]
            
            async for doc in errors_collection.aggregate(pipeline):
                most_frequent.append({
                    "fingerprint": doc["fingerprint"],
                    "category": doc["category"],
                    "error_type": doc["error_type"],
                    "message": doc["normalized_message"],
                    "count": doc["occurrence_count"],
                    "last_seen": doc["last_seen"]
                })
            
            stats["most_frequent"] = most_frequent
            
            # Get recent errors
            recent_errors = []
            pipeline = [
                {"$match": query},
                {"$sort": {"last_seen": -1}},
                {"$limit": 10},
                {"$project": {
                    "fingerprint": 1,
                    "category": 1,
                    "error_type": 1,
                    "normalized_message": 1,
                    "occurrence_count": 1,
                    "last_seen": 1
                }}
            ]
            
            async for doc in errors_collection.aggregate(pipeline):
                recent_errors.append({
                    "fingerprint": doc["fingerprint"],
                    "category": doc["category"],
                    "error_type": doc["error_type"],
                    "message": doc["normalized_message"],
                    "count": doc["occurrence_count"],
                    "last_seen": doc["last_seen"]
                })
            
            stats["recent_errors"] = recent_errors
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting error statistics: {e}")
            return {"error": str(e)}
    
    @staticmethod
    async def get_error_details(fingerprint):
        """Get detailed information about a specific error
        
        Args:
            fingerprint: Error fingerprint to look up
        
        Returns:
            Dictionary with error details
        """
        if _db is None:
            return {"error": "Database not initialized"}
        
        try:
            errors_collection = _db.errors
            
            # Find the specific error
            error = await errors_collection.find_one({"fingerprint": fingerprint})
            
            if not error:
                return {"error": "Error not found"}
            
            # Convert to a clean dictionary
            details = {
                "fingerprint": error["fingerprint"],
                "category": error["category"],
                "error_type": error["error_type"],
                "error_message": error["error_message"],
                "first_seen": error["first_seen"],
                "last_seen": error["last_seen"],
                "occurrence_count": error["occurrence_count"],
                "last_traceback": error["last_traceback"],
                "last_context": error["last_context"],
                "recent_occurrences": error.get("recent_occurrences", [])[:10]  # Limit to 10
            }
            
            return details
            
        except Exception as e:
            logger.error(f"Error getting error details: {e}")
            return {"error": str(e)}
    
    @staticmethod
    def capture_exceptions(category=None, context=None):
        """Decorator for capturing exceptions in functions
        
        Args:
            category: Optional category to assign
            context: Optional fixed context to include
            
        Returns:
            Decorator function
        """
        def decorator(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    # Create context from args and kwargs
                    func_context = {
                        "function": func.__name__,
                        "module": func.__module__
                    }
                    
                    # Add fixed context if provided
                    if context:
                        func_context.update(context)
                    
                    # Track the error
                    await ErrorTelemetry.track_error(
                        error=e,
                        context=func_context,
                        category=category
                    )
                    
                    # Re-raise the exception
                    raise
            
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    # Create context from args and kwargs
                    func_context = {
                        "function": func.__name__,
                        "module": func.__module__
                    }
                    
                    # Add fixed context if provided
                    if context:
                        func_context.update(context)
                    
                    # Capture the error (using asyncio.run since track_error is async)
                    asyncio.create_task(ErrorTelemetry.track_error(
                        error=e,
                        context=func_context,
                        category=category
                    ))
                    
                    # Re-raise the exception
                    raise
            
            # Check if the function is a coroutine
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper
                
        return decorator
    
    @staticmethod
    async def start_maintenance_task():
        """Start background maintenance task for error telemetry"""
        global _background_task
        
        async def maintenance_loop():
            while True:
                try:
                    # Flush error buffer
                    await ErrorTelemetry.flush_error_buffer()
                    
                    # Clean up old errors
                    if _db:
                        cutoff_date = datetime.utcnow() - timedelta(days=ERROR_RECORD_TTL)
                        await _db.errors.delete_many({"last_seen": {"$lt": cutoff_date}})
                    
                    # Sleep until next run
                    await asyncio.sleep(FLUSH_INTERVAL)
                    
                except asyncio.CancelledError:
                    logger.info("Error telemetry maintenance task cancelled")
                    break
                except Exception as e:
                    logger.error(f"Error in telemetry maintenance task: {e}")
                    await asyncio.sleep(FLUSH_INTERVAL)
        
        if _background_task is None or _background_task.done():
            _background_task = asyncio.create_task(maintenance_loop())
            logger.info("Started error telemetry maintenance task")
    
    @staticmethod
    async def stop_maintenance_task():
        """Stop the background maintenance task"""
        global _background_task
        
        if _background_task and not _background_task.done():
            _background_task.cancel()
            try:
                await _background_task
            except asyncio.CancelledError:
                pass
            
            _background_task = None
            logger.info("Stopped error telemetry maintenance task")
    
    @staticmethod
    def enable():
        """Enable error telemetry"""
        global _error_telemetry_enabled
        _error_telemetry_enabled = True
        logger.info("Error telemetry enabled")
    
    @staticmethod
    def disable():
        """Disable error telemetry"""
        global _error_telemetry_enabled
        _error_telemetry_enabled = False
        logger.info("Error telemetry disabled")

# Initialize the error telemetry system
async def initialize_error_telemetry(bot=None):
    """Initialize error telemetry system
    
    Args:
        bot: Bot instance with database access
    
    Returns:
        Error telemetry instance
    """
    # Get database if we have a bot
    db = None
    if bot and hasattr(bot, "db"):
        try:
            db = bot.db()
            
            # Create indexes for error collection if needed
            await db.errors.create_index("fingerprint", unique=True)
            await db.errors.create_index("category")
            await db.errors.create_index("last_seen")
            
            logger.info("Created indexes for error collection")
        except Exception as e:
            logger.error(f"Failed to initialize database for error telemetry: {e}")
    
    # Create telemetry instance
    telemetry = ErrorTelemetry(db=db)
    
    # Start maintenance task
    await ErrorTelemetry.start_maintenance_task()
    
    return telemetry