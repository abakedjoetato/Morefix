"""
Interaction Handlers for py-cord 2.6.1 Compatibility

This module provides functions for handling Discord interactions across
different versions of py-cord and discord.py.
"""

import logging
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union, cast

import discord
from discord.ext import commands

logger = logging.getLogger(__name__)

async def get_interaction_user(interaction_or_ctx: Union[discord.Interaction, commands.Context]) -> Optional[discord.User]:
    """
    Get the user from an interaction or context with compatibility
    
    Args:
        interaction_or_ctx: Discord interaction or context
        
    Returns:
        discord.User or None: The user who triggered the interaction/command
    """
    try:
        if isinstance(interaction_or_ctx, discord.Interaction):
            # Handle py-cord 2.6.1 and discord.py differences
            if hasattr(interaction_or_ctx, 'user') and interaction_or_ctx.user:
                return interaction_or_ctx.user
            elif hasattr(interaction_or_ctx, 'author') and interaction_or_ctx.author:
                return interaction_or_ctx.author
        elif isinstance(interaction_or_ctx, commands.Context):
            # Context objects should always have an author
            return interaction_or_ctx.author
            
        # Fallback
        logger.warning(f"Could not extract user from {type(interaction_or_ctx).__name__}")
        return None
    except Exception as e:
        logger.error(f"Error getting interaction user: {e}")
        return None

async def safely_respond_to_interaction(
    interaction: discord.Interaction,
    content: Optional[str] = None,
    embed: Optional[discord.Embed] = None,
    embeds: Optional[List[discord.Embed]] = None,
    ephemeral: bool = False,
    view: Optional[discord.ui.View] = None,
    **kwargs
) -> bool:
    """
    Safely respond to an interaction with py-cord 2.6.1 compatibility
    
    This function handles the differences between libraries and already-responded
    interactions.
    
    Args:
        interaction: Discord interaction
        content: Text content to send
        embed: Embed to send
        embeds: List of embeds to send
        ephemeral: Whether the response should be ephemeral
        view: UI view to attach
        **kwargs: Additional response options
        
    Returns:
        bool: True if the response was sent, False otherwise
    """
    try:
        # Check if the interaction can be responded to
        if hasattr(interaction, 'response') and hasattr(interaction.response, 'is_done'):
            already_responded = interaction.response.is_done()
        else:
            # Assume it's already responded if we can't check
            already_responded = True
            
        # Handle the response based on whether it's already been responded to
        if not already_responded:
            # Initial response
            await interaction.response.send_message(
                content=content,
                embed=embed,
                embeds=embeds,
                ephemeral=ephemeral,
                view=view,
                **kwargs
            )
            return True
        else:
            # Follow-up response
            if hasattr(interaction, 'followup') and callable(getattr(interaction, 'followup', None)):
                # Use followup if available
                await interaction.followup.send(
                    content=content,
                    embed=embed,
                    embeds=embeds,
                    ephemeral=ephemeral,
                    view=view,
                    **kwargs
                )
                return True
            elif hasattr(interaction, 'edit_original_response') and callable(getattr(interaction, 'edit_original_response', None)):
                # Try to edit the original response
                await interaction.edit_original_response(
                    content=content,
                    embed=embed,
                    embeds=embeds,
                    view=view,
                    **kwargs
                )
                return True
            elif hasattr(interaction, 'channel') and interaction.channel:
                # As a last resort, send a new message to the channel
                await interaction.channel.send(
                    content=content,
                    embed=embed,
                    embeds=embeds,
                    view=view,
                    **kwargs
                )
                return True
                
        logger.warning(f"Failed to respond to interaction: no valid response method found")
        return False
    except Exception as e:
        logger.error(f"Error responding to interaction: {e}")
        return False