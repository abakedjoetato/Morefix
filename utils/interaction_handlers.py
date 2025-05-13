"""
Interaction handling utilities

This module provides functions to handle interactions consistently across
different Discord library versions.
"""

import logging
import inspect
import functools
from typing import Any, Callable, Dict, List, Optional, Union, cast

import discord
from discord import Interaction, InteractionResponse, Embed, Member, User

from utils.command_imports import is_compatible_with_pycord_261

logger = logging.getLogger(__name__)

def get_user_from_interaction(interaction: Interaction) -> Optional[Union[User, Member]]:
    """
    Get the user or member who triggered the interaction
    
    Args:
        interaction: The Discord interaction
        
    Returns:
        The user or member, or None if not found
    """
    # In py-cord, this is interaction.user
    # In discord.py, might be interaction.user or interaction.author
    
    # Try py-cord style first
    if hasattr(interaction, 'user') and interaction.user is not None:
        return interaction.user
        
    # Try discord.py style
    if hasattr(interaction, 'author') and interaction.author is not None:
        return interaction.author
        
    # Last resort, try to get from guild
    if hasattr(interaction, 'guild') and interaction.guild is not None and hasattr(interaction, 'user_id'):
        return interaction.guild.get_member(interaction.user_id)
        
    return None

def safe_interaction_response(func):
    """
    Decorator to safely handle interaction responses
    
    This handles various interaction response methods across different 
    Discord library versions and ensures we don't try to respond multiple times.
    
    Args:
        func: The function to decorate
        
    Returns:
        The decorated function
    """
    @functools.wraps(func)
    async def wrapper(interaction, *args, **kwargs):
        try:
            # Check if interaction can be responded to
            if hasattr(interaction, 'response') and hasattr(interaction.response, 'is_done'):
                if interaction.response.is_done():
                    # Already responded, use followup or edit_original_response
                    if hasattr(interaction, 'followup'):
                        # Use followup if available (py-cord or discord.py)
                        result = await interaction.followup.send(*args, **kwargs)
                        return result
                    elif hasattr(interaction, 'edit_original_response'):
                        # Use edit if followup not available
                        result = await interaction.edit_original_response(*args, **kwargs)
                        return result
                    else:
                        logger.warning("Interaction already responded to, but no followup method available")
                        return None
                else:
                    # Not responded yet, call the original function
                    return await func(interaction, *args, **kwargs)
            else:
                # No way to check if responded, just try the original function
                return await func(interaction, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error in interaction response: {e}")
            # Try to send a message directly if possible
            try:
                if hasattr(interaction, 'channel') and interaction.channel:
                    await interaction.channel.send(f"Error processing command: {str(e)}")
            except:
                pass
            return None
    
    return wrapper

@safe_interaction_response
async def respond_to_interaction(
    interaction: Interaction,
    content: Optional[str] = None,
    embed: Optional[Embed] = None,
    ephemeral: bool = False
):
    """
    Respond to an interaction in a way that works across Discord library versions
    
    Args:
        interaction: The Discord interaction
        content: Text content to send
        embed: Embed to send
        ephemeral: Whether the response should be ephemeral
        
    Returns:
        The response object
    """
    try:
        # Check if we can defer the response first
        if not interaction.response.is_done():
            # Respond using the library-specific method
            if is_compatible_with_pycord_261():
                # py-cord style
                return await interaction.response.send_message(
                    content=content,
                    embed=embed,
                    ephemeral=ephemeral
                )
            else:
                # discord.py style
                return await interaction.response.send_message(
                    content=content,
                    embed=embed,
                    ephemeral=ephemeral
                )
        else:
            # Already responded, use followup
            if hasattr(interaction, 'followup'):
                return await interaction.followup.send(
                    content=content,
                    embed=embed,
                    ephemeral=ephemeral
                )
            else:
                logger.warning("Interaction already responded to and no followup available")
                return None
    except Exception as e:
        logger.error(f"Error responding to interaction: {e}")
        # Try to send a message directly if possible
        try:
            if hasattr(interaction, 'channel') and interaction.channel:
                return await interaction.channel.send(
                    content=content,
                    embed=embed
                )
        except Exception as e2:
            logger.error(f"Failed to send fallback message: {e2}")
        return None

def patch_interaction_respond():
    """
    Patch interaction response methods to be consistent across Discord library versions
    
    This adds helper methods to the Interaction class to make it easier to respond
    consistently regardless of which Discord library version is being used.
    """
    # Add our safe respond method to the Interaction class
    if not hasattr(discord.Interaction, 'safe_respond'):
        setattr(discord.Interaction, 'safe_respond', respond_to_interaction)
        logger.info("Added safe_respond method to Interaction class")
        
    # If using py-cord 2.6.1, also patch to add some discord.py-like methods
    if is_compatible_with_pycord_261():
        # Add any py-cord specific patches here
        pass
    else:
        # Add any discord.py specific patches here
        pass