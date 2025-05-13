"""
Interaction Handlers for py-cord 2.6.1 Compatibility

This module provides utility functions for handling interactions and responses
with compatibility across different versions of py-cord and discord.py.
"""

import logging
import traceback
from typing import Any, Dict, List, Optional, Union, Callable, TypeVar, Awaitable

import discord
from discord.ext import commands

from utils.command_imports import (
    is_compatible_with_pycord_261,
    PYCORD_261,
    HAS_APP_COMMANDS
)

logger = logging.getLogger(__name__)

# Define a type for interaction or context
InteractionOrCtx = Union[discord.Interaction, commands.Context]

async def safely_respond_to_interaction(
    interaction: discord.Interaction,
    content: Optional[str] = None,
    *,
    embed: Optional[discord.Embed] = None,
    embeds: Optional[List[discord.Embed]] = None,
    file: Optional[discord.File] = None,
    files: Optional[List[discord.File]] = None,
    view: Optional[discord.ui.View] = None,
    ephemeral: bool = False,
    delete_after: Optional[float] = None,
    **kwargs
) -> Optional[Union[discord.Message, discord.InteractionMessage, discord.WebhookMessage]]:
    """
    Safely respond to an interaction with py-cord 2.6.1 compatibility
    
    This function handles the differences between py-cord 2.6.1 and other versions
    when responding to interactions.
    
    Args:
        interaction: The interaction to respond to
        content: Optional content for the response
        embed: Optional embed for the response
        embeds: Optional list of embeds for the response
        file: Optional file for the response
        files: Optional list of files for the response
        view: Optional view for the response
        ephemeral: Whether the response should be ephemeral
        delete_after: Optional time after which to delete the response
        **kwargs: Additional parameters for the response
        
    Returns:
        The response message, if available
    """
    if not interaction:
        logger.warning("Cannot respond to None interaction")
        return None
        
    try:
        # Check if the interaction has already been responded to
        is_responded = False
        
        # Check the interaction's response attribute based on library version
        if is_compatible_with_pycord_261():
            # py-cord 2.6.1 uses interaction.response and has an is_done() method
            if hasattr(interaction, 'response') and interaction.response:
                if hasattr(interaction.response, 'is_done') and callable(interaction.response.is_done):
                    is_responded = interaction.response.is_done()
        else:
            # Other libraries might use different attributes
            is_responded = getattr(interaction, "_responded", False)
        
        # Create a kwargs dict for the response
        response_kwargs = {
            "content": content,
            "ephemeral": ephemeral,
            **kwargs
        }
        
        # Add embed or embeds if provided
        if embed:
            response_kwargs["embed"] = embed
        elif embeds:
            response_kwargs["embeds"] = embeds
            
        # Add file or files if provided
        if file:
            response_kwargs["file"] = file
        elif files:
            response_kwargs["files"] = files
            
        # Add view if provided
        if view:
            response_kwargs["view"] = view
        
        # Handle the response based on whether it's already been responded to
        if not is_responded:
            # First response - use the send_message method with library compatibility
            if is_compatible_with_pycord_261():
                # py-cord 2.6.1 uses interaction.response.send_message
                if hasattr(interaction, 'response') and hasattr(interaction.response, 'send_message'):
                    await interaction.response.send_message(**response_kwargs)
                    
                    # Get the message from followup if available
                    if hasattr(interaction, 'followup') and hasattr(interaction.followup, 'message'):
                        return interaction.followup.message
                    
                    # Otherwise, return None as we can't get the message object
                    return None
                else:
                    logger.warning("Cannot find response.send_message on interaction")
                    return None
            else:
                # Other libraries might use respond
                if hasattr(interaction, 'respond') and callable(interaction.respond):
                    return await interaction.respond(**response_kwargs)
                else:
                    logger.warning("Cannot find respond method on interaction")
                    return None
        else:
            # Follow-up response - use followup/edit_original_message with library compatibility
            if is_compatible_with_pycord_261():
                # py-cord 2.6.1 uses interaction.followup.send for follow-ups
                if hasattr(interaction, 'followup') and hasattr(interaction.followup, 'send'):
                    return await interaction.followup.send(**response_kwargs)
                else:
                    logger.warning("Cannot find followup.send on interaction")
                    
                    # Try channel.send as a fallback
                    if hasattr(interaction, 'channel') and interaction.channel:
                        if hasattr(interaction.channel, 'send') and callable(interaction.channel.send):
                            return await interaction.channel.send(**response_kwargs)
                    
                    return None
            else:
                # Other libraries might use send_message/edit_original_message
                if hasattr(interaction, 'edit_original_message') and callable(interaction.edit_original_message):
                    return await interaction.edit_original_message(**response_kwargs)
                elif hasattr(interaction, 'send_message') and callable(interaction.send_message):
                    return await interaction.send_message(**response_kwargs)
                elif hasattr(interaction, 'send') and callable(interaction.send):
                    return await interaction.send(**response_kwargs)
                else:
                    logger.warning("Cannot find appropriate follow-up method on interaction")
                    return None
    except Exception as e:
        logger.error(f"Error responding to interaction: {e}")
        logger.error(traceback.format_exc())
        
        # Try to respond with a generic error message
        try:
            if is_compatible_with_pycord_261():
                # Check if we can send a followup
                if hasattr(interaction, 'followup') and hasattr(interaction.followup, 'send'):
                    await interaction.followup.send(
                        content="An error occurred while processing your request.",
                        ephemeral=True
                    )
            else:
                # Try using send as a fallback
                if hasattr(interaction, 'send') and callable(interaction.send):
                    await interaction.send(
                        content="An error occurred while processing your request.",
                        ephemeral=True
                    )
        except Exception:
            # If this fails too, just log it
            logger.error("Failed to send error message to user")
        
        return None

async def get_interaction_user(interaction_or_ctx: InteractionOrCtx) -> Optional[discord.User]:
    """
    Get the user from an interaction or context with library compatibility
    
    Args:
        interaction_or_ctx: The interaction or context
        
    Returns:
        The user, or None if not found
    """
    try:
        if isinstance(interaction_or_ctx, discord.Interaction):
            # For interactions, use user attribute
            return getattr(interaction_or_ctx, 'user', None)
        elif isinstance(interaction_or_ctx, commands.Context):
            # For context, use author attribute
            return getattr(interaction_or_ctx, 'author', None)
        else:
            logger.warning(f"Unknown interaction type: {type(interaction_or_ctx)}")
            return None
    except Exception as e:
        logger.error(f"Error getting interaction user: {e}")
        return None

async def send_modal(
    interaction: discord.Interaction,
    title: str,
    input_fields: List[Dict[str, Any]],
    custom_id: Optional[str] = None
) -> bool:
    """
    Send a modal with py-cord 2.6.1 compatibility
    
    Args:
        interaction: The interaction to respond with a modal
        title: The title of the modal
        input_fields: List of input field definitions
        custom_id: Optional custom ID for the modal
        
    Returns:
        bool: True if the modal was sent successfully, False otherwise
    """
    try:
        # Generate custom_id if not provided
        if not custom_id:
            custom_id = f"modal_{title.lower().replace(' ', '_')}"
            
        if is_compatible_with_pycord_261():
            # py-cord 2.6.1 uses Modal class
            # Check what version of Modal class we have
            try:
                # Import Modal and InputText classes
                from discord.ui import Modal, InputText
                
                # Create a new Modal subclass
                class DynamicModal(Modal):
                    def __init__(self, title, custom_id, input_fields):
                        super().__init__(title=title, custom_id=custom_id)
                        
                        # Add each input field
                        for field in input_fields:
                            self.add_item(InputText(
                                label=field.get("label", "Input"),
                                placeholder=field.get("placeholder", ""),
                                value=field.get("value", ""),
                                required=field.get("required", True),
                                style=field.get("style", InputText.short),
                                custom_id=field.get("custom_id", f"input_{len(self.children)}")
                            ))
                    
                    async def callback(self, interaction):
                        # Default callback - for custom handling, caller should add their own
                        results = {}
                        for child in self.children:
                            results[child.custom_id] = child.value
                        
                        await interaction.response.send_message(f"Modal submitted: {results}", ephemeral=True)
                
                # Create the modal instance
                modal = DynamicModal(title=title, custom_id=custom_id, input_fields=input_fields)
                
                # Send the modal
                if hasattr(interaction, 'response') and hasattr(interaction.response, 'send_modal'):
                    await interaction.response.send_modal(modal)
                    return True
                else:
                    logger.warning("Cannot find response.send_modal on interaction")
                    return False
            except ImportError as e:
                logger.error(f"Error importing Modal/InputText: {e}")
                return False
        else:
            # Other libraries might have different methods
            logger.warning("Modal support for non-py-cord libraries not implemented")
            return False
    except Exception as e:
        logger.error(f"Error sending modal: {e}")
        logger.error(traceback.format_exc())
        return False