"""
Interaction Handlers Module

This module provides utilities for handling Discord message interactions,
compatible with both Context and Interaction models across Discord.py and py-cord.
"""

import logging
import traceback
from typing import Any, Dict, List, Optional, Tuple, Union, TypeVar, cast

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def is_interaction(obj: Any) -> bool:
    """
    Check if an object is a Discord interaction.
    
    Args:
        obj: Object to check
        
    Returns:
        Whether the object is an interaction
    """
    # Check for interaction attribute
    if hasattr(obj, 'response') and callable(getattr(obj, 'response', None)):
        return True
        
    # Check for application command interaction
    if hasattr(obj, 'interaction') and obj.interaction is not None:
        return True
        
    return False

def is_context(obj: Any) -> bool:
    """
    Check if an object is a Discord context.
    
    Args:
        obj: Object to check
        
    Returns:
        Whether the object is a context
    """
    # Check for send method
    if hasattr(obj, 'send') and callable(getattr(obj, 'send', None)):
        # Make sure it's not an interaction
        if not is_interaction(obj):
            return True
            
    return False

async def safely_respond_to_interaction(interaction: Any, content: Optional[str] = None, **kwargs) -> bool:
    """
    Safely respond to a Discord interaction with proper error handling.
    
    Args:
        interaction: The interaction to respond to
        content: The content to send
        **kwargs: Additional arguments to pass to the response method
        
    Returns:
        Whether the response was successful
    """
    if interaction is None:
        return False
        
    # Try different methods for responding based on the interaction type
    try:
        # Try response.send_message
        if hasattr(interaction, 'response') and hasattr(interaction.response, 'send_message'):
            await interaction.response.send_message(content=content, **kwargs)
            return True
            
        # Try followup.send
        if hasattr(interaction, 'followup') and hasattr(interaction.followup, 'send'):
            await interaction.followup.send(content=content, **kwargs)
            return True
            
        # Try plain send for ApplicationContext
        if hasattr(interaction, 'send') and callable(getattr(interaction, 'send', None)):
            await interaction.send(content=content, **kwargs)
            return True
            
        # Try Webhook-style interaction
        if hasattr(interaction, 'send') and callable(getattr(interaction, 'send', None)):
            await interaction.send(content, **kwargs)
            return True
            
        logger.error(f"Couldn't find a way to respond to interaction: {type(interaction)}")
        return False
        
    except Exception as e:
        logger.error(f"Error responding to interaction: {e}")
        logger.error(traceback.format_exc())
        
        # Try to use a fallback method if the primary failed
        try:
            # Fallback to channel.send if all else fails
            if hasattr(interaction, 'channel') and interaction.channel is not None:
                if hasattr(interaction.channel, 'send'):
                    await interaction.channel.send(content, **kwargs)
                    return True
        except Exception as fallback_error:
            logger.error(f"Fallback error: {fallback_error}")
            
        return False

async def hybrid_send(ctx_or_interaction: Any, content: Optional[str] = None, embed: Optional[Any] = None, 
                      embeds: Optional[List[Any]] = None, ephemeral: bool = False, 
                      view: Optional[Any] = None, **kwargs) -> Any:
    """
    Send a message that works with both context and interaction objects.
    
    Args:
        ctx_or_interaction: The context or interaction to send to
        content: The content to send
        embed: The embed to send
        embeds: The embeds to send
        ephemeral: Whether the message should be ephemeral
        view: The view component to send
        **kwargs: Additional arguments to pass to the send method
        
    Returns:
        The message sent, or None if it failed
    """
    if ctx_or_interaction is None:
        return None
        
    # Handle interactions specially
    if is_interaction(ctx_or_interaction):
        try:
            # Only pass ephemeral for interactions
            return await safely_respond_to_interaction(
                ctx_or_interaction,
                content=content,
                embed=embed,
                embeds=embeds,
                ephemeral=ephemeral,
                view=view,
                **kwargs
            )
        except Exception as e:
            logger.error(f"Error sending to interaction: {e}")
            logger.error(traceback.format_exc())
            return None
            
    # Handle context objects
    elif is_context(ctx_or_interaction):
        try:
            # Don't pass ephemeral for context sends
            kwargs_copy = kwargs.copy()
            if 'ephemeral' in kwargs_copy:
                del kwargs_copy['ephemeral']
                
            return await ctx_or_interaction.send(
                content,
                embed=embed,
                embeds=embeds,
                view=view,
                **kwargs_copy
            )
        except Exception as e:
            logger.error(f"Error sending to context: {e}")
            logger.error(traceback.format_exc())
            return None
            
    # Unknown object, try the safest option
    logger.warning(f"Unknown object type for hybrid_send: {type(ctx_or_interaction)}")
    try:
        # Try both methods for maximum compatibility
        if hasattr(ctx_or_interaction, 'send') and callable(getattr(ctx_or_interaction, 'send', None)):
            return await ctx_or_interaction.send(
                content,
                embed=embed,
                embeds=embeds,
                **kwargs
            )
            
        # Last resort, try to get channel
        if hasattr(ctx_or_interaction, 'channel') and ctx_or_interaction.channel is not None:
            if hasattr(ctx_or_interaction.channel, 'send'):
                return await ctx_or_interaction.channel.send(
                    content,
                    embed=embed,
                    embeds=embeds,
                    **kwargs
                )
    except Exception as e:
        logger.error(f"Error in hybrid send fallback: {e}")
        
    return None

def get_user(ctx_or_interaction: Any) -> Optional[Any]:
    """
    Get the user from a context or interaction object.
    
    Args:
        ctx_or_interaction: The context or interaction to get the user from
        
    Returns:
        The user or None
    """
    if ctx_or_interaction is None:
        return None
        
    # Try various attributes based on the object type
    try:
        # Direct author attribute
        if hasattr(ctx_or_interaction, 'author') and ctx_or_interaction.author is not None:
            return ctx_or_interaction.author
            
        # User attribute
        if hasattr(ctx_or_interaction, 'user') and ctx_or_interaction.user is not None:
            return ctx_or_interaction.user
            
        # Interaction user
        if hasattr(ctx_or_interaction, 'interaction') and ctx_or_interaction.interaction is not None:
            if hasattr(ctx_or_interaction.interaction, 'user') and ctx_or_interaction.interaction.user is not None:
                return ctx_or_interaction.interaction.user
    except Exception as e:
        logger.error(f"Error getting user: {e}")
        
    return None

def get_guild(ctx_or_interaction: Any) -> Optional[Any]:
    """
    Get the guild from a context or interaction object.
    
    Args:
        ctx_or_interaction: The context or interaction to get the guild from
        
    Returns:
        The guild or None
    """
    if ctx_or_interaction is None:
        return None
        
    # Try various attributes based on the object type
    try:
        # Direct guild attribute
        if hasattr(ctx_or_interaction, 'guild') and ctx_or_interaction.guild is not None:
            return ctx_or_interaction.guild
            
        # Guild from channel
        if hasattr(ctx_or_interaction, 'channel') and ctx_or_interaction.channel is not None:
            if hasattr(ctx_or_interaction.channel, 'guild') and ctx_or_interaction.channel.guild is not None:
                return ctx_or_interaction.channel.guild
    except Exception as e:
        logger.error(f"Error getting guild: {e}")
        
    return None

def get_guild_id(ctx_or_interaction: Any) -> Optional[int]:
    """
    Get the guild ID from a context or interaction object.
    
    Args:
        ctx_or_interaction: The context or interaction to get the guild ID from
        
    Returns:
        The guild ID or None
    """
    if ctx_or_interaction is None:
        return None
        
    # Try to get the guild first
    guild = get_guild(ctx_or_interaction)
    if guild is not None and hasattr(guild, 'id'):
        return guild.id
        
    # Try various attributes based on the object type
    try:
        # Direct guild_id attribute
        if hasattr(ctx_or_interaction, 'guild_id') and ctx_or_interaction.guild_id is not None:
            return ctx_or_interaction.guild_id
            
        # Guild ID from channel
        if hasattr(ctx_or_interaction, 'channel') and ctx_or_interaction.channel is not None:
            if hasattr(ctx_or_interaction.channel, 'guild_id') and ctx_or_interaction.channel.guild_id is not None:
                return ctx_or_interaction.channel.guild_id
    except Exception as e:
        logger.error(f"Error getting guild ID: {e}")
        
    return None