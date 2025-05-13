"""
Interaction Handlers for Discord API Compatibility

This module provides helper functions for safely handling interactions across
different versions of discord.py and py-cord, especially for responding to
interactions in a way that's resilient to errors.
"""

import logging
import inspect
from typing import Any, Dict, List, Optional, Union

try:
    import discord
    from discord.ext import commands
except ImportError as e:
    logging.error(f"Failed to import Discord libraries: {e}")
    raise ImportError(
        "Failed to import Discord libraries. Please install discord.py or py-cord."
    ) from e

# Setup logger
logger = logging.getLogger(__name__)

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
    Safely respond to an interaction with proper error handling.
    
    This function tries to respond to an interaction in the most appropriate way,
    handling both fresh interactions and those that have already been responded to.
    
    Args:
        interaction: The Discord interaction to respond to
        content: Optional text content to send
        embed: Optional embed to send
        embeds: Optional list of embeds to send
        ephemeral: Whether the response should be ephemeral (only visible to the user)
        view: Optional UI view to attach
        **kwargs: Additional keyword arguments to pass to the response method
        
    Returns:
        bool: True if the response was sent successfully, False otherwise
    """
    if interaction is None:
        logger.warning("Cannot respond to None interaction")
        return False
    
    try:
        # Check if interaction is already responded to
        if interaction.response.is_done():
            # Try followup
            try:
                await interaction.followup.send(
                    content=content,
                    embed=embed,
                    embeds=embeds,
                    ephemeral=ephemeral,
                    view=view,
                    **kwargs
                )
                return True
            except Exception as e:
                # If followup fails, try to edit the original response
                logger.warning(f"Failed to send followup: {e}, trying to edit original response")
                try:
                    message = await interaction.original_response()
                    await message.edit(
                        content=content, 
                        embed=embed,
                        embeds=embeds,
                        view=view,
                        **kwargs
                    )
                    return True
                except Exception as e2:
                    logger.error(f"Failed to edit original response: {e2}")
                    return False
        else:
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
    except Exception as e:
        logger.error(f"Failed to respond to interaction: {e}")
        
        # One last attempt - try to send a DM if it's a critical message
        if not ephemeral and hasattr(interaction, "user") and interaction.user:
            try:
                await interaction.user.send(
                    content=content or "There was an error processing your command.",
                    embed=embed,
                    embeds=embeds
                )
                logger.info(f"Sent fallback DM to {interaction.user}")
                return True
            except Exception as e2:
                logger.error(f"Failed to send fallback DM: {e2}")
                
        return False

async def hybrid_send(
    ctx_or_interaction: Union[commands.Context, discord.Interaction],
    content: Optional[str] = None,
    embed: Optional[discord.Embed] = None,
    embeds: Optional[List[discord.Embed]] = None,
    ephemeral: bool = False,
    view: Optional[discord.ui.View] = None,
    **kwargs
) -> Optional[discord.Message]:
    """
    Send a message to either a Context or an Interaction with proper handling.
    
    This function detects whether it was passed a Context or an Interaction and
    responds appropriately, making it easier to write code that works with both
    traditional commands and application/slash commands.
    
    Args:
        ctx_or_interaction: Either a Context or an Interaction
        content: Optional text content to send
        embed: Optional embed to send
        embeds: Optional list of embeds to send
        ephemeral: Whether the response should be ephemeral (only for Interaction)
        view: Optional UI view to attach
        **kwargs: Additional keyword arguments to pass to the response method
        
    Returns:
        Optional[discord.Message]: The sent message, if available
    """
    # First check if it's an Interaction
    if isinstance(ctx_or_interaction, discord.Interaction):
        success = await safely_respond_to_interaction(
            ctx_or_interaction,
            content=content,
            embed=embed,
            embeds=embeds,
            ephemeral=ephemeral,
            view=view,
            **kwargs
        )
        if success:
            try:
                # Try to get the message for those who need it
                # This may fail for ephemeral messages
                return await ctx_or_interaction.original_response()
            except Exception:
                # It's okay if we can't get the message
                return None
        return None
    
    # Otherwise assume it's a Context
    try:
        # Filter out interaction-only parameters
        if "ephemeral" in kwargs:
            del kwargs["ephemeral"]
            
        # Context.send() returns the Message directly
        return await ctx_or_interaction.send(
            content=content,
            embed=embed,
            embeds=embeds,
            view=view,
            **kwargs
        )
    except Exception as e:
        logger.error(f"Failed to send message via Context: {e}")
        return None

def is_interaction(ctx_or_interaction: Any) -> bool:
    """
    Check if the given object is an Interaction.
    
    Args:
        ctx_or_interaction: The object to check
        
    Returns:
        bool: True if it's an Interaction, False otherwise
    """
    return isinstance(ctx_or_interaction, discord.Interaction)

def is_context(ctx_or_interaction: Any) -> bool:
    """
    Check if the given object is a Context.
    
    Args:
        ctx_or_interaction: The object to check
        
    Returns:
        bool: True if it's a Context, False otherwise
    """
    return isinstance(ctx_or_interaction, commands.Context)

def get_user(ctx_or_interaction: Any) -> Optional[Union[discord.User, discord.Member]]:
    """
    Get the user from either a Context or an Interaction.
    
    Args:
        ctx_or_interaction: Either a Context or an Interaction
        
    Returns:
        Optional[Union[discord.User, discord.Member]]: The user, if available
    """
    if is_interaction(ctx_or_interaction):
        return ctx_or_interaction.user
    elif is_context(ctx_or_interaction):
        return ctx_or_interaction.author
    return None

def get_guild(ctx_or_interaction: Any) -> Optional[discord.Guild]:
    """
    Get the guild from either a Context or an Interaction.
    
    Args:
        ctx_or_interaction: Either a Context or an Interaction
        
    Returns:
        Optional[discord.Guild]: The guild, if available
    """
    if is_interaction(ctx_or_interaction):
        return ctx_or_interaction.guild
    elif is_context(ctx_or_interaction):
        return ctx_or_interaction.guild
    return None

def get_guild_id(ctx_or_interaction: Any) -> Optional[int]:
    """
    Get the guild ID from either a Context or an Interaction.
    
    Args:
        ctx_or_interaction: Either a Context or an Interaction
        
    Returns:
        Optional[int]: The guild ID, if available
    """
    if is_interaction(ctx_or_interaction):
        return ctx_or_interaction.guild_id
    elif is_context(ctx_or_interaction):
        return ctx_or_interaction.guild.id if ctx_or_interaction.guild else None
    return None