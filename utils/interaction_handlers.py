"""
Interaction Handlers for py-cord 2.6.1 Compatibility

This module provides utilities for safely interacting with Discord Interactions
across different versions of py-cord and discord.py.
"""

import logging
import traceback
from typing import Union, Any, Dict, Optional

import discord
from discord.ext import commands

logger = logging.getLogger(__name__)

async def safely_respond_to_interaction(
    interaction: discord.Interaction,
    content_or_embed: Union[str, discord.Embed, Dict[str, Any], None] = None,
    *,
    ephemeral: bool = False,
    view: Optional[discord.ui.View] = None,
    delete_after: Optional[float] = None,
    file: Optional[discord.File] = None,
    files: Optional[list] = None
) -> bool:
    """
    Safely respond to an interaction using proper response methods depending on state
    
    Args:
        interaction: The Discord interaction to respond to
        content_or_embed: Content, embed or data dict to send as response
        ephemeral: Whether the response should be ephemeral
        view: View component to attach to the response
        delete_after: Time after which to delete the response (followup only)
        file: File to attach to the response
        files: Files to attach to the response
        
    Returns:
        bool: True if response was sent successfully, False otherwise
    """
    try:
        # Prepare kwargs for response/followup
        kwargs = {'ephemeral': ephemeral}
        if view is not None:
            kwargs['view'] = view
            
        # Handle file attachments
        if file is not None:
            kwargs['file'] = file
        if files is not None:
            kwargs['files'] = files
            
        # Process content or embed
        if isinstance(content_or_embed, str):
            kwargs['content'] = content_or_embed
        elif isinstance(content_or_embed, discord.Embed):
            kwargs['embed'] = content_or_embed
        elif isinstance(content_or_embed, dict):
            # Handle sending a data dict
            kwargs.update(content_or_embed)
        
        # Check if interaction has been responded to already
        if hasattr(interaction, 'response') and hasattr(interaction.response, 'is_done'):
            if interaction.response.is_done():
                # Already responded, use followup
                if hasattr(interaction, 'followup'):
                    # Use modern followup
                    if delete_after is not None:
                        # Map delete_after to followup call if supported
                        if hasattr(interaction.followup, 'send') and 'delete_after' in interaction.followup.send.__code__.co_varnames:
                            kwargs['delete_after'] = delete_after
                    
                    # Send the followup
                    await interaction.followup.send(**kwargs)
                    return True
                else:
                    # Old versions might not have followup
                    logger.warning("Interaction response already sent but followup not available")
                    return False
            else:
                # Not responded yet, send initial response
                await interaction.response.send_message(**kwargs)
                return True
        else:
            # No response attribute, try basic methods
            try:
                # Try the direct response send approach
                await interaction.response.send_message(**kwargs)
                return True
            except AttributeError:
                # For very old versions or edge cases
                try:
                    await interaction.send(**kwargs)
                    return True
                except Exception as e:
                    logger.error(f"Failed to respond to interaction: {e}")
                    return False
                    
    except Exception as e:
        logger.error(f"Error in safely_respond_to_interaction: {e}", exc_info=True)
        return False

def get_interaction_user(ctx_or_interaction) -> Optional[Union[discord.User, discord.Member]]:
    """
    Get the user from an interaction or context object
    
    Args:
        ctx_or_interaction: The interaction or context
        
    Returns:
        Optional[Union[discord.User, discord.Member]]: The user or None if not found
    """
    # Extract from interaction
    if isinstance(ctx_or_interaction, discord.Interaction):
        if hasattr(ctx_or_interaction, 'user') and ctx_or_interaction.user is not None:
            return ctx_or_interaction.user
        elif hasattr(ctx_or_interaction, 'author') and ctx_or_interaction.author is not None:
            return ctx_or_interaction.author
            
    # Extract from context
    elif isinstance(ctx_or_interaction, commands.Context):
        if hasattr(ctx_or_interaction, 'author') and ctx_or_interaction.author is not None:
            return ctx_or_interaction.author
        elif hasattr(ctx_or_interaction, 'user') and ctx_or_interaction.user is not None:
            return ctx_or_interaction.user
            
    # Try generic attribute access as last resort
    try:
        if hasattr(ctx_or_interaction, 'user'):
            return ctx_or_interaction.user
        elif hasattr(ctx_or_interaction, 'author'):
            return ctx_or_interaction.author
    except:
        pass
        
    # Couldn't find user
    return None