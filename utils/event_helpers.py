"""
Event Helpers for Discord API Compatibility

This module provides utilities for working with Discord events
across different versions of Discord libraries.
"""

import asyncio
import inspect
import logging
import functools
from typing import Any, Callable, Coroutine, Dict, List, Optional, Set, TypeVar, Union, cast

# Setup logger
logger = logging.getLogger(__name__)

try:
    import discord
    from discord.ext import commands
    
    # Check if we're using py-cord by looking for voice_client attribute
    USING_PYCORD = hasattr(discord, "VoiceProtocol")
    
except ImportError as e:
    # Provide better error messages for missing dependencies
    logger.error(f"Failed to import Discord libraries: {e}")
    raise ImportError(
        "Failed to import Discord libraries. Please install discord.py or py-cord:\n"
        "For py-cord: pip install py-cord>=2.0.0\n"
        "For discord.py: pip install discord.py>=2.0.0"
    ) from e

# Import our async helpers
from utils.async_helpers import is_coroutine_function, ensure_async, ensure_sync, safe_gather

# Type variables for return typing
T = TypeVar('T')
EventT = TypeVar('EventT')
ListenerT = Callable[..., Coroutine[Any, Any, Any]]

class EventDispatcher:
    """
    Event dispatcher for Discord events.
    
    This class provides a way to register event listeners and dispatch events
    with proper error handling and compatibility across Discord library versions.
    """
    
    def __init__(self):
        """
        Initialize the event dispatcher.
        """
        self.listeners: Dict[str, List[ListenerT]] = {}
        self.once_listeners: Dict[str, List[ListenerT]] = {}
        
    def register_listener(
        self,
        event_name: str,
        listener: ListenerT,
        once: bool = False
    ) -> None:
        """
        Register an event listener.
        
        Args:
            event_name: Event name to listen for
            listener: Event listener function
            once: Whether to call the listener only once
        """
        # Ensure the listener is async
        async_listener = ensure_async(listener)
        
        # Get the appropriate listener list
        if once:
            listeners = self.once_listeners.setdefault(event_name, [])
        else:
            listeners = self.listeners.setdefault(event_name, [])
            
        # Add the listener
        listeners.append(async_listener)
        
    def remove_listener(
        self,
        event_name: str,
        listener: ListenerT,
        once: bool = False
    ) -> bool:
        """
        Remove an event listener.
        
        Args:
            event_name: Event name
            listener: Event listener function
            once: Whether the listener was registered with once=True
            
        Returns:
            True if the listener was removed, False otherwise
        """
        # Get the appropriate listener list
        if once:
            listeners = self.once_listeners.get(event_name, [])
        else:
            listeners = self.listeners.get(event_name, [])
            
        # Try to find and remove the listener
        for i, l in enumerate(listeners):
            if l == listener or getattr(l, "__wrapped__", None) == listener:
                listeners.pop(i)
                return True
                
        return False
        
    def clear_listeners(
        self,
        event_name: Optional[str] = None
    ) -> None:
        """
        Clear event listeners.
        
        Args:
            event_name: Event name to clear, or None to clear all
        """
        if event_name is None:
            # Clear all listeners
            self.listeners.clear()
            self.once_listeners.clear()
        else:
            # Clear listeners for a specific event
            self.listeners.pop(event_name, None)
            self.once_listeners.pop(event_name, None)
            
    async def dispatch(
        self,
        event_name: str,
        *args,
        **kwargs
    ) -> None:
        """
        Dispatch an event to listeners.
        
        Args:
            event_name: Event name
            *args: Event arguments
            **kwargs: Event keyword arguments
        """
        # Get listeners
        normal_listeners = self.listeners.get(event_name, [])
        once_listeners = self.once_listeners.pop(event_name, [])
        
        # Combine listeners
        all_listeners = normal_listeners + once_listeners
        
        # Process event in batches to avoid event queue backlog
        BATCH_SIZE = 10
        for i in range(0, len(all_listeners), BATCH_SIZE):
            batch = all_listeners[i:i+BATCH_SIZE]
            tasks = [self._call_listener(listener, *args, **kwargs) for listener in batch]
            await safe_gather(*tasks, return_exceptions=True)
            
    async def _call_listener(
        self,
        listener: ListenerT,
        *args,
        **kwargs
    ) -> None:
        """
        Call an event listener with error handling.
        
        Args:
            listener: Event listener function
            *args: Event arguments
            **kwargs: Event keyword arguments
        """
        try:
            await listener(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in event listener {listener.__name__}: {e}")
            
    def on(
        self,
        event_name: str
    ) -> Callable[[ListenerT], ListenerT]:
        """
        Decorator to register an event listener.
        
        Args:
            event_name: Event name to listen for
            
        Returns:
            Decorator function
        """
        def decorator(func: ListenerT) -> ListenerT:
            # Register the listener
            self.register_listener(event_name, func)
            return func
            
        return decorator
        
    def once(
        self,
        event_name: str
    ) -> Callable[[ListenerT], ListenerT]:
        """
        Decorator to register a one-time event listener.
        
        Args:
            event_name: Event name to listen for
            
        Returns:
            Decorator function
        """
        def decorator(func: ListenerT) -> ListenerT:
            # Register the one-time listener
            self.register_listener(event_name, func, once=True)
            return func
            
        return decorator

class CompatibleBot(commands.Bot):
    """
    Discord bot with compatibility enhancements.
    
    This class extends commands.Bot with additional compatibility features
    for working with events, intents, and other Discord API features.
    """
    
    def __init__(self, *args, **kwargs):
        """
        Initialize the compatible bot.
        
        Args:
            *args: Positional arguments to pass to commands.Bot
            **kwargs: Keyword arguments to pass to commands.Bot
        """
        # Initialize the event dispatcher
        self.event_dispatcher = EventDispatcher()
        
        # Store the original on_error handler
        self._original_on_error = getattr(self, "on_error", None)
        
        # Initialize the bot
        super().__init__(*args, **kwargs)
        
        # Replace the on_error method
        if hasattr(self, "on_error"):
            self._original_on_error = self.on_error
            self.on_error = self._safe_on_error
            
    async def _safe_on_error(self, event_method, *args, **kwargs):
        """
        Safe on_error method with better error handling.
        
        Args:
            event_method: Event method name
            *args: Event arguments
            **kwargs: Event keyword arguments
        """
        try:
            # Try calling the original on_error method
            if self._original_on_error is not None:
                if asyncio.iscoroutinefunction(self._original_on_error):
                    await self._original_on_error(event_method, *args, **kwargs)
                else:
                    self._original_on_error(event_method, *args, **kwargs)
            else:
                # Default error handling
                logger.error(f"Error in {event_method}: {args} {kwargs}")
                logger.exception("Exception:")
        except Exception as e:
            # Handle errors in the error handler
            logger.error(f"Error in on_error handler: {e}")
            logger.exception("Exception:")
            
    def add_listener(
        self,
        func: ListenerT,
        name: Optional[str] = None
    ) -> None:
        """
        Add an event listener with compatibility.
        
        Args:
            func: Event listener function
            name: Event name, or None to use the function name
        """
        # Get the event name
        if name is None:
            name = func.__name__
            
            # Remove "on_" prefix if present
            if name.startswith("on_"):
                name = name[3:]
                
        # Register with both systems for compatibility
        super().add_listener(func, name)
        self.event_dispatcher.register_listener(name, func)
        
    def dispatch(
        self,
        event_name: str,
        *args,
        **kwargs
    ) -> None:
        """
        Dispatch an event with compatibility.
        
        Args:
            event_name: Event name
            *args: Event arguments
            **kwargs: Event keyword arguments
        """
        # Dispatch with both systems for compatibility
        super().dispatch(event_name, *args, **kwargs)
        asyncio.create_task(self.event_dispatcher.dispatch(event_name, *args, **kwargs))
        
    def event(
        self,
        coro: Optional[Callable] = None,
        name: Optional[str] = None
    ) -> Union[Callable[[T], T], T]:
        """
        Decorator to register an event listener with compatibility.
        
        Args:
            coro: Event listener function
            name: Event name, or None to use the function name
            
        Returns:
            Decorator function or the decorated function
        """
        def decorator(func: T) -> T:
            # Get the event name
            event_name = name
            if event_name is None:
                event_name = func.__name__
                
                # Remove "on_" prefix if present
                if event_name.startswith("on_"):
                    event_name = event_name[3:]
                    
            # Register with both systems for compatibility
            self.add_listener(func, event_name)
            return func
            
        # Handle being called as @bot.event or @bot.event()
        if coro is not None:
            return decorator(coro)
            
        return decorator
        
    def on(
        self,
        event_name: str
    ) -> Callable[[ListenerT], ListenerT]:
        """
        Decorator to register an event listener.
        
        Args:
            event_name: Event name to listen for
            
        Returns:
            Decorator function
        """
        def decorator(func: ListenerT) -> ListenerT:
            # Register with both systems for compatibility
            self.add_listener(func, event_name)
            return func
            
        return decorator
        
    def once(
        self,
        event_name: str
    ) -> Callable[[ListenerT], ListenerT]:
        """
        Decorator to register a one-time event listener.
        
        Args:
            event_name: Event name to listen for
            
        Returns:
            Decorator function
        """
        def decorator(func: ListenerT) -> ListenerT:
            # Register with the event dispatcher
            self.event_dispatcher.register_listener(event_name, func, once=True)
            return func
            
        return decorator

def register_cog_events(bot: commands.Bot, cog: commands.Cog) -> None:
    """
    Register events from a cog with compatibility.
    
    Args:
        bot: Bot to register events with
        cog: Cog to register events from
    """
    # Check if the bot has the event_dispatcher attribute
    has_dispatcher = hasattr(bot, "event_dispatcher")
    
    # Get all methods in the cog
    for name, method in inspect.getmembers(cog, inspect.ismethod):
        # Check if the method is an event listener
        if name.startswith("on_") and is_coroutine_function(method):
            # Get the event name
            event_name = name[3:]
            
            # Register with both systems for compatibility
            bot.add_listener(method, event_name)
            
            # Register with the event dispatcher if available
            if has_dispatcher:
                bot.event_dispatcher.register_listener(event_name, method)