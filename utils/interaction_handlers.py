"""
Interaction Handlers

This module provides compatibility functionality for handling Discord interactions
across different versions of the Discord library.
"""

import logging
import traceback
from typing import Any, Dict, Optional, Union, List, Callable

import discord
from utils.discord_compat import is_pycord_261_or_later

logger = logging.getLogger(__name__)

async def safely_respond_to_interaction(interaction: discord.Interaction, 
                                       content: Optional[str] = None,
                                       embed: Optional[discord.Embed] = None,
                                       embeds: Optional[List[discord.Embed]] = None,
                                       ephemeral: bool = False,
                                       view: Optional[discord.ui.View] = None,
                                       file: Optional[discord.File] = None,
                                       files: Optional[List[discord.File]] = None,
                                       allowed_mentions: Optional[discord.AllowedMentions] = None) -> bool:
    """
    Safely respond to an interaction with proper compatibility handling
    
    This function handles the differences between different Discord library versions
    for responding to interactions, including fallback mechanisms if the interaction
    has already been responded to.
    
    Args:
        interaction: The Discord interaction to respond to
        content: Text content to send
        embed: A single embed to send
        embeds: Multiple embeds to send (overrides embed if both are provided)
        ephemeral: Whether the response should be ephemeral (only visible to the user)
        view: Optional UI components to include
        file: A single file to send
        files: Multiple files to send (overrides file if both are provided)
        allowed_mentions: AllowedMentions settings for this response
        
    Returns:
        bool: True if the response was sent successfully, False otherwise
    """
    if interaction is None:
        logger.error("Cannot respond to None interaction")
        return False
    
    # Prepare kwargs for response
    kwargs = {}
    if content is not None:
        kwargs['content'] = content
    
    # Handle embeds (single embed takes precedence)
    if embeds is not None:
        kwargs['embeds'] = embeds
    elif embed is not None:
        kwargs['embed'] = embed
    
    # Handle files (multiple files take precedence)
    if files is not None:
        kwargs['files'] = files
    elif file is not None:
        kwargs['file'] = file
    
    if view is not None:
        kwargs['view'] = view
        
    if allowed_mentions is not None:
        kwargs['allowed_mentions'] = allowed_mentions
    
    # Handle ephemeral flag
    kwargs['ephemeral'] = ephemeral
    
    # Try to respond based on the interaction state
    try:
        # If we're using py-cord 2.6.1+
        if is_pycord_261_or_later():
            # Check if we need to use followup or original response
            if interaction.response.is_done():
                # If we've already responded, use followup
                await interaction.followup.send(**kwargs)
            else:
                # Use response for the first interaction response
                await interaction.response.send_message(**kwargs)
        else:
            # For older versions
            if not interaction.response.is_done():
                await interaction.response.send_message(**kwargs)
            else:
                # For older versions, try to use the followup approach
                if hasattr(interaction, "followup"):
                    await interaction.followup.send(**kwargs)
                else:
                    # Last resort for really old versions
                    await interaction.channel.send(**kwargs)
        
        return True
    except Exception as e:
        logger.error(f"Error responding to interaction: {e}\n{traceback.format_exc()}")
        
        # Try emergency fallback response if nothing else worked
        try:
            # Try to send a message to the user directly if everything else failed
            user = interaction.user
            if user:
                # This is a last resort if all other response methods failed
                await user.send(content="There was an error processing your command. Please try again later.")
        except Exception as inner_e:
            logger.error(f"Emergency fallback response also failed: {inner_e}")
            
        return False

# Alias for hybrid_send compatibility
async def hybrid_send(ctx_or_interaction: Any, 
                    content: Optional[str] = None,
                    embed: Optional[discord.Embed] = None,
                    embeds: Optional[List[discord.Embed]] = None,
                    ephemeral: bool = False,
                    view: Optional[discord.ui.View] = None,
                    file: Optional[discord.File] = None,
                    files: Optional[List[discord.File]] = None) -> bool:
    """
    Send a message to either a Context or Interaction
    
    This function is a compatibility layer for code that needs to work with both
    traditional commands (ctx) and application commands (interactions).
    
    Args:
        ctx_or_interaction: Either a Context or Interaction object
        content: Text content to send
        embed: A single embed to send
        embeds: Multiple embeds to send
        ephemeral: Whether the message should be ephemeral (only for interactions)
        view: UI components to include
        file: A single file to send
        files: Multiple files to send
        
    Returns:
        bool: True if message was sent successfully, False otherwise
    """
    kwargs = {}
    if content is not None:
        kwargs['content'] = content
        
    if embeds is not None:
        kwargs['embeds'] = embeds
    elif embed is not None:
        kwargs['embed'] = embed
        
    if files is not None:
        kwargs['files'] = files
    elif file is not None:
        kwargs['file'] = file
        
    if view is not None:
        kwargs['view'] = view
    
    try:
        # If it's an Interaction, use our safe response function
        if isinstance(ctx_or_interaction, discord.Interaction):
            kwargs['ephemeral'] = ephemeral
            return await safely_respond_to_interaction(ctx_or_interaction, **kwargs)
            
        # If it's a Context, use send
        elif hasattr(ctx_or_interaction, "send"):
            await ctx_or_interaction.send(**kwargs)
            return True
            
        # If it's a channel, use send directly
        elif hasattr(ctx_or_interaction, "send_message"):
            await ctx_or_interaction.send_message(**kwargs)
            return True
            
        # Unknown type
        else:
            logger.error(f"Unknown type for hybrid_send: {type(ctx_or_interaction)}")
            return False
            
    except Exception as e:
        logger.error(f"Error in hybrid_send: {e}\n{traceback.format_exc()}")
        return False