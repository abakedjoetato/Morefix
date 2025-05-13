"""
Async Helper Utilities

This module provides async/await helper utilities to ensure compatibility
across different Python versions and Discord libraries.
"""

import asyncio
import functools
import inspect
import logging
import time
from typing import Any, Callable, Dict, List, Optional, Tuple, Union, TypeVar, cast, Coroutine

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

T = TypeVar('T')
F = TypeVar('F', bound=Callable[..., Any])
CoroFunc = Callable[..., Coroutine[Any, Any, T]]

def is_coroutine_function(func: Callable[..., Any]) -> bool:
    """
    Check if a function is a coroutine function.
    
    Args:
        func: The function to check
        
    Returns:
        Whether the function is a coroutine function
    """
    if func is None:
        return False
        
    if asyncio.iscoroutinefunction(func):
        return True
        
    # Unwrap partial functions
    if isinstance(func, functools.partial):
        return is_coroutine_function(func.func)
        
    # Check inspect
    return inspect.iscoroutinefunction(func)

async def ensure_async(func: Callable[..., Any], *args, **kwargs) -> Any:
    """
    Ensure a function is executed asynchronously.
    
    Args:
        func: The function to execute
        *args: The positional arguments to pass to the function
        **kwargs: The keyword arguments to pass to the function
        
    Returns:
        The result of the function
    """
    if func is None:
        return None
        
    try:
        if is_coroutine_function(func):
            return await func(*args, **kwargs)
        else:
            # Run in a thread pool if it's a blocking function
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None, functools.partial(func, *args, **kwargs)
            )
    except Exception as e:
        logger.error(f"Error ensuring async execution: {e}")
        return None

def ensure_sync(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    Ensure a function is executed synchronously.
    
    Args:
        func: The function to wrap
        
    Returns:
        A synchronous wrapper function
    """
    if func is None:
        return lambda *args, **kwargs: None
        
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if is_coroutine_function(func):
            # Create a new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(func(*args, **kwargs))
            finally:
                loop.close()
        else:
            return func(*args, **kwargs)
            
    return wrapper

async def safe_gather(*aws, return_exceptions=False) -> List[Any]:
    """
    Safely gather coroutines with proper error handling.
    
    Args:
        *aws: The awaitables to gather
        return_exceptions: Whether to return exceptions instead of raising them
        
    Returns:
        The results of the awaitables
    """
    try:
        return await asyncio.gather(*aws, return_exceptions=return_exceptions)
    except Exception as e:
        logger.error(f"Error gathering coroutines: {e}")
        if return_exceptions:
            return [e] * len(aws)
        else:
            raise

async def safe_wait(aws, timeout=None, return_when=asyncio.ALL_COMPLETED) -> Tuple[set, set]:
    """
    Safely wait for coroutines with proper error handling.
    
    Args:
        aws: The awaitables to wait for
        timeout: The timeout in seconds
        return_when: When to return
        
    Returns:
        The done and pending sets
    """
    try:
        return await asyncio.wait(aws, timeout=timeout, return_when=return_when)
    except Exception as e:
        logger.error(f"Error waiting for coroutines: {e}")
        return set(), set(aws)

class AsyncCache:
    """A simple async-compatible cache."""
    
    def __init__(self, ttl: float = 60.0):
        """
        Initialize the cache.
        
        Args:
            ttl: The time-to-live in seconds
        """
        self.cache = {}
        self.ttl = ttl
        
    async def get(self, key: str) -> Optional[Any]:
        """
        Get a value from the cache.
        
        Args:
            key: The key to get
            
        Returns:
            The value or None
        """
        if key not in self.cache:
            return None
            
        value, timestamp = self.cache[key]
        
        # Check if expired
        if time.time() - timestamp > self.ttl:
            del self.cache[key]
            return None
            
        return value
        
    async def set(self, key: str, value: Any) -> None:
        """
        Set a value in the cache.
        
        Args:
            key: The key to set
            value: The value to set
        """
        self.cache[key] = (value, time.time())
        
    async def get_or_set_async(self, key: str, getter: CoroFunc) -> Any:
        """
        Get a value from the cache or set it.
        
        Args:
            key: The key to get
            getter: The function to call to get the value
            
        Returns:
            The value
        """
        value = await self.get(key)
        if value is not None:
            return value
            
        value = await ensure_async(getter)
        await self.set(key, value)
        return value
        
    def invalidate(self, key: str) -> None:
        """
        Invalidate a cache key.
        
        Args:
            key: The key to invalidate
        """
        if key in self.cache:
            del self.cache[key]
            
    def clear(self) -> None:
        """Clear the cache."""
        self.cache.clear()

def cached_async(ttl: float = 60.0):
    """
    Decorator to cache the result of an async function.
    
    Args:
        ttl: The time-to-live in seconds
        
    Returns:
        The decorated function
    """
    cache = AsyncCache(ttl)
    
    def decorator(func: CoroFunc) -> CoroFunc:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Create a cache key
            key_parts = [func.__name__]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            key = ":".join(key_parts)
            
            return await cache.get_or_set_async(key, lambda: func(*args, **kwargs))
            
        return wrapper
        
    return decorator