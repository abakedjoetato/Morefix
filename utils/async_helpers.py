"""
Async Helpers for Discord API Compatibility

This module provides helpers for safely working with asynchronous functions
across different versions of Python and Discord libraries.
"""

import asyncio
import inspect
import logging
import functools
from typing import Any, Callable, Coroutine, Dict, List, Optional, TypeVar, Union, cast

# Setup logger
logger = logging.getLogger(__name__)

# Type variables for return typing
T = TypeVar('T')
R = TypeVar('R')
AsyncCallable = Callable[..., Coroutine[Any, Any, R]]
SyncCallable = Callable[..., R]
AnyCallable = Union[AsyncCallable[R], SyncCallable[R]]

def is_coroutine_function(func: Callable) -> bool:
    """
    Check if a function is a coroutine function.
    
    This is a safe wrapper around inspect.iscoroutinefunction that handles
    edge cases like decorated functions.
    
    Args:
        func: Function to check
        
    Returns:
        True if the function is a coroutine function, False otherwise
    """
    # First check if the function is a native coroutine function
    if inspect.iscoroutinefunction(func):
        return True
        
    # Check if the function is an async generator
    if inspect.isasyncgenfunction(func):
        return True
        
    # Check if the function is a decorated coroutine function
    if hasattr(func, "__wrapped__"):
        return is_coroutine_function(func.__wrapped__)
        
    # Check for a _is_coroutine attribute (used by discord.py)
    if hasattr(func, "_is_coroutine") and func._is_coroutine:
        return True
        
    return False

def ensure_async(func: AnyCallable[R]) -> AsyncCallable[R]:
    """
    Ensure that a function is async.
    
    If the function is already async, it's returned as-is.
    If the function is sync, it's wrapped in a coroutine.
    
    Args:
        func: Function to ensure is async
        
    Returns:
        Async version of the function
    """
    if is_coroutine_function(func):
        return cast(AsyncCallable[R], func)
        
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
        
    return wrapper

def ensure_sync(func: AnyCallable[R]) -> SyncCallable[R]:
    """
    Ensure that a function is sync.
    
    If the function is already sync, it's returned as-is.
    If the function is async, it's wrapped to run in the event loop.
    
    Args:
        func: Function to ensure is sync
        
    Returns:
        Sync version of the function
    """
    if not is_coroutine_function(func):
        return cast(SyncCallable[R], func)
        
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Get the current event loop
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            # Create a new event loop if one doesn't exist
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        # Run the coroutine in the event loop
        if loop.is_running():
            # Create a future for the coroutine
            future = asyncio.run_coroutine_threadsafe(func(*args, **kwargs), loop)
            return future.result()
        else:
            # Run the coroutine directly
            return loop.run_until_complete(func(*args, **kwargs))
            
    return wrapper

async def safe_gather(*coros_or_futures, return_exceptions=False):
    """
    Safely gather coroutines or futures.
    
    This is a wrapper around asyncio.gather that handles exceptions better
    and provides better error messages.
    
    Args:
        *coros_or_futures: Coroutines or futures to gather
        return_exceptions: Whether to return exceptions or raise them
        
    Returns:
        List of results from the coroutines or futures
    """
    # Filter out None values
    coros = [c for c in coros_or_futures if c is not None]
    
    if not coros:
        return []
        
    try:
        return await asyncio.gather(*coros, return_exceptions=return_exceptions)
    except Exception as e:
        logger.error(f"Error gathering coroutines: {e}")
        if return_exceptions:
            return [e] * len(coros)
        raise

async def safe_wait(
    aws,
    *,
    timeout=None,
    return_when=asyncio.ALL_COMPLETED
):
    """
    Safely wait for coroutines to complete.
    
    This is a wrapper around asyncio.wait that handles exceptions better
    and provides better error messages.
    
    Args:
        aws: Coroutines to wait for
        timeout: Maximum time to wait
        return_when: When to return (ALL_COMPLETED, FIRST_COMPLETED, FIRST_EXCEPTION)
        
    Returns:
        Tuple of (done, pending) sets
    """
    # Filter out None values
    coros = [c for c in aws if c is not None]
    
    if not coros:
        return set(), set()
        
    try:
        done, pending = await asyncio.wait(
            coros,
            timeout=timeout,
            return_when=return_when
        )
        return done, pending
    except Exception as e:
        logger.error(f"Error waiting for coroutines: {e}")
        return set(), set(coros)

class AsyncCache:
    """
    Cache for async function results.
    
    This class provides a cache for async function results, with support
    for TTL (time to live) and automatic invalidation.
    """
    
    def __init__(self, ttl: float = 300.0):
        """
        Initialize the cache.
        
        Args:
            ttl: Time to live in seconds
        """
        self.cache: Dict[str, Any] = {}
        self.ttl = ttl
        self.timestamps: Dict[str, float] = {}
        
    def get(self, key: str) -> Optional[Any]:
        """
        Get a value from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value, or None if not found or expired
        """
        # Check if the key exists
        if key not in self.cache:
            return None
            
        # Check if the value has expired
        if self.ttl > 0:
            # Get the timestamp
            timestamp = self.timestamps.get(key, 0)
            
            # Check if the value has expired
            if timestamp + self.ttl < asyncio.get_event_loop().time():
                # Remove the expired value
                del self.cache[key]
                del self.timestamps[key]
                return None
                
        # Return the cached value
        return self.cache[key]
        
    def set(self, key: str, value: Any) -> None:
        """
        Set a value in the cache.
        
        Args:
            key: Cache key
            value: Value to cache
        """
        # Set the value
        self.cache[key] = value
        
        # Set the timestamp
        if self.ttl > 0:
            self.timestamps[key] = asyncio.get_event_loop().time()
            
    def delete(self, key: str) -> None:
        """
        Delete a value from the cache.
        
        Args:
            key: Cache key
        """
        # Delete the value
        if key in self.cache:
            del self.cache[key]
            
        # Delete the timestamp
        if key in self.timestamps:
            del self.timestamps[key]
            
    def clear(self) -> None:
        """
        Clear the cache.
        """
        # Clear the cache and timestamps
        self.cache.clear()
        self.timestamps.clear()
        
    def get_or_set(self, key: str, func: Callable[[], Any]) -> Any:
        """
        Get a value from the cache, or set it if not found.
        
        Args:
            key: Cache key
            func: Function to call if the value is not found
            
        Returns:
            Cached value
        """
        # Get the value
        value = self.get(key)
        
        # If the value is not found, set it
        if value is None:
            value = func()
            self.set(key, value)
            
        return value
        
    async def get_or_set_async(self, key: str, func: Callable[[], Coroutine[Any, Any, Any]]) -> Any:
        """
        Get a value from the cache, or set it if not found.
        
        Args:
            key: Cache key
            func: Async function to call if the value is not found
            
        Returns:
            Cached value
        """
        # Get the value
        value = self.get(key)
        
        # If the value is not found, set it
        if value is None:
            value = await func()
            self.set(key, value)
            
        return value
        
async_cache = AsyncCache()

def cached_async(ttl: float = 300.0):
    """
    Decorator for caching async function results.
    
    Args:
        ttl: Time to live in seconds
        
    Returns:
        Decorated function
    """
    def decorator(func: AsyncCallable):
        # Create a cache for this function
        cache = AsyncCache(ttl=ttl)
        
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Create a key from the arguments
            key_parts = [func.__name__]
            
            # Add positional arguments
            for arg in args:
                key_parts.append(str(arg))
                
            # Add keyword arguments
            for k, v in sorted(kwargs.items()):
                key_parts.append(f"{k}={v}")
                
            # Join the parts
            key = ":".join(key_parts)
            
            # Get or set the value
            return await cache.get_or_set_async(key, lambda: func(*args, **kwargs))
            
        return wrapper
        
    return decorator