"""
Interaction Handlers Module

This module provides utility functions for handling Discord interactions,
with compatibility between different Discord library versions.
"""

import logging
from typing import Any, Dict, List, Optional, Union, Callable, TypeVar, cast

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import discord compatibility module
from utils.discord_compat import discord, commands, app_commands

# Type variables for interactable objects
T = TypeVar('T')
InteractionT = TypeVar('InteractionT')
ContextT = TypeVar('ContextT')

async def hybrid_send(ctx_or_interaction: Any, 
                     content: Optional[str] = None, 
                     **kwargs) -> Any:
    """
    Send a message to either a Context or Interaction with compatibility.
    
    Args:
        ctx_or_interaction: The context or interaction to send to
        content: The content to send
        **kwargs: Additional arguments to pass to the send method
        
    Returns:
        The message sent or None
    """
    try:
        # Check if it's an interaction
        if hasattr(ctx_or_interaction, 'response') and hasattr(ctx_or_interaction.response, 'send_message'):
            # Check if the interaction has been responded to
            if not getattr(ctx_or_interaction.response, '_responded', False):
                # It's an interaction that hasn't been responded to
                if 'ephemeral' in kwargs:
                    ephemeral = kwargs.pop('ephemeral')
                else:
                    ephemeral = False
                    
                await ctx_or_interaction.response.send_message(content, ephemeral=ephemeral, **kwargs)
                
                # Try to get the original response
                if hasattr(ctx_or_interaction, 'original_response') or hasattr(ctx_or_interaction, 'original_message'):
                    try:
                        return await ctx_or_interaction.original_response()
                    except AttributeError:
                        try:
                            return await ctx_or_interaction.original_message()
                        except (AttributeError, TypeError):
                            return None
                return None
            elif hasattr(ctx_or_interaction, 'followup') and hasattr(ctx_or_interaction.followup, 'send'):
                # It's an interaction that has been responded to
                return await ctx_or_interaction.followup.send(content, **kwargs)
        # Check if it's a context
        elif hasattr(ctx_or_interaction, 'send'):
            # It's a context
            return await ctx_or_interaction.send(content, **kwargs)
        else:
            logger.error(f"Unknown context or interaction type: {type(ctx_or_interaction)}")
            return None
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        # Try to send a basic message as fallback
        try:
            if hasattr(ctx_or_interaction, 'send'):
                return await ctx_or_interaction.send(f"Error: {e}", **kwargs)
            elif hasattr(ctx_or_interaction, 'followup') and hasattr(ctx_or_interaction.followup, 'send'):
                return await ctx_or_interaction.followup.send(f"Error: {e}", **kwargs)
        except Exception:
            pass
        return None

async def hybrid_defer(ctx_or_interaction: Any, 
                      ephemeral: bool = False,
                      **kwargs) -> bool:
    """
    Defer a context or interaction with compatibility.
    
    Args:
        ctx_or_interaction: The context or interaction to defer
        ephemeral: Whether the response should be ephemeral
        **kwargs: Additional arguments to pass to the defer method
        
    Returns:
        Whether the defer was successful
    """
    try:
        # Check if it's an interaction
        if hasattr(ctx_or_interaction, 'response') and hasattr(ctx_or_interaction.response, 'defer'):
            # It's an interaction
            await ctx_or_interaction.response.defer(ephemeral=ephemeral, **kwargs)
            return True
        # Check if it's a context (contexts don't need to be deferred)
        elif hasattr(ctx_or_interaction, 'typing'):
            # For contexts, we can just use typing as indication of processing
            async with ctx_or_interaction.typing():
                pass
            return True
        else:
            logger.error(f"Unknown context or interaction type: {type(ctx_or_interaction)}")
            return False
    except Exception as e:
        logger.error(f"Error deferring: {e}")
        return False

async def hybrid_edit(ctx_or_interaction: Any,
                     content: Optional[str] = None,
                     **kwargs) -> Any:
    """
    Edit a message from either a Context or Interaction with compatibility.
    
    Args:
        ctx_or_interaction: The context or interaction to edit
        content: The new content
        **kwargs: Additional arguments to pass to the edit method
        
    Returns:
        The edited message or None
    """
    try:
        # Check if it's an interaction
        if hasattr(ctx_or_interaction, 'edit_original_response'):
            # It's an interaction
            return await ctx_or_interaction.edit_original_response(content=content, **kwargs)
        elif hasattr(ctx_or_interaction, 'edit_original_message'):
            # Alternate naming in some versions
            return await ctx_or_interaction.edit_original_message(content=content, **kwargs)
        # Check if it's a context or message
        elif hasattr(ctx_or_interaction, 'edit'):
            # It's a context or message
            return await ctx_or_interaction.edit(content=content, **kwargs)
        else:
            logger.error(f"Unknown context or interaction type: {type(ctx_or_interaction)}")
            return None
    except Exception as e:
        logger.error(f"Error editing message: {e}")
        return None

def is_interaction(ctx_or_interaction: Any) -> bool:
    """
    Check if an object is an interaction.
    
    Args:
        ctx_or_interaction: The object to check
        
    Returns:
        Whether the object is an interaction
    """
    return (
        hasattr(ctx_or_interaction, 'response') and 
        hasattr(ctx_or_interaction.response, 'send_message')
    )

def is_context(ctx_or_interaction: Any) -> bool:
    """
    Check if an object is a context.
    
    Args:
        ctx_or_interaction: The object to check
        
    Returns:
        Whether the object is a context
    """
    return (
        hasattr(ctx_or_interaction, 'send') and 
        not is_interaction(ctx_or_interaction)
    )

def get_user(ctx_or_interaction: Any) -> Optional[Any]:
    """
    Get the user from a context or interaction.
    
    Args:
        ctx_or_interaction: The context or interaction
        
    Returns:
        The user or None
    """
    if is_interaction(ctx_or_interaction):
        return getattr(ctx_or_interaction, 'user', None)
    else:
        return getattr(ctx_or_interaction, 'author', None)

def get_guild(ctx_or_interaction: Any) -> Optional[Any]:
    """
    Get the guild from a context or interaction.
    
    Args:
        ctx_or_interaction: The context or interaction
        
    Returns:
        The guild or None
    """
    return getattr(ctx_or_interaction, 'guild', None)

def get_channel(ctx_or_interaction: Any) -> Optional[Any]:
    """
    Get the channel from a context or interaction.
    
    Args:
        ctx_or_interaction: The context or interaction
        
    Returns:
        The channel or None
    """
    return getattr(ctx_or_interaction, 'channel', None)

# Export for easy importing
__all__ = [
    'hybrid_send', 'hybrid_defer', 'hybrid_edit',
    'is_interaction', 'is_context',
    'get_user', 'get_guild', 'get_channel'
]