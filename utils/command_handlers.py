"""
Command handling utilities for Discord bot cogs
"""

import logging
import functools
import traceback
from typing import Any, Callable, Dict, List, Optional, TypeVar, cast

import discord
from discord.ext import commands

from utils.safe_mongodb import SafeMongoDBResult

T = TypeVar('T')
logger = logging.getLogger(__name__)

def command_handler(
    collection_name: Optional[str] = None,
    operation_type: Optional[str] = None
):
    """
    Decorator for command handling with proper error handling and logging

    Args:
        collection_name: Optional collection name for database operation
        operation_type: Optional operation type for more specific error handling
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            try:
                logger.debug(f"Executing command handler for {func.__name__}")
                return await func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in command {func.__name__} ({operation_type or 'unknown'}): {e}")
                logger.debug(traceback.format_exc())
                if isinstance(e, discord.app_commands.errors.CommandInvokeError):
                    # Unwrap the original exception if it's a CommandInvokeError
                    original = e.original
                    if isinstance(original, Exception):
                        logger.error(f"Original error: {original}")
                return SafeMongoDBResult.error_result(
                    str(e),
                    None,
                    collection_name or "unknown"
                )
        return wrapper
    return decorator

async def defer_interaction(interaction: discord.Interaction) -> bool:
    """
    Safely defer an interaction with error handling
    
    Args:
        interaction: The interaction to defer
        
    Returns:
        True if deferred successfully, False otherwise
    """
    try:
        if not interaction.response.is_done():
            await interaction.response.defer()
            return True
    except Exception as e:
        logger.error(f"Failed to defer interaction: {e}")
    return False

def db_operation(operation_type: Optional[str] = None):
    """
    Decorator for database operations with proper error handling
    
    Args:
        operation_type: Optional operation type for more specific error handling
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> SafeMongoDBResult:
            try:
                logger.debug(f"Executing database operation {func.__name__}")
                result = await func(*args, **kwargs)
                if isinstance(result, SafeMongoDBResult):
                    return result
                else:
                    # If the function doesn't return a SafeMongoDBResult, wrap it
                    return SafeMongoDBResult.success_result(result)
            except Exception as e:
                logger.error(f"Error in database operation {func.__name__} ({operation_type or 'unknown'}): {e}")
                logger.debug(traceback.format_exc())
                return SafeMongoDBResult.error_result(
                    str(e),
                    None,
                    operation_type or func.__name__
                )
        return wrapper
    return decorator