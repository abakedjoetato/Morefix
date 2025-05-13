"""
Interaction handling utilities for Discord bot cogs
"""

import logging
from typing import Any, Dict, List, Optional, Union, cast

import discord
from discord.ext import commands

logger = logging.getLogger(__name__)

async def safely_respond_to_interaction(
    interaction: discord.Interaction, 
    message: str, 
    ephemeral: bool = False, 
    embed: Optional[discord.Embed] = None
) -> bool:
    """
    Safely respond to an interaction with error handling
    
    Args:
        interaction: The interaction to respond to
        message: The message to send
        ephemeral: Whether the response should be ephemeral
        embed: Optional embed to send
        
    Returns:
        True if responded successfully, False otherwise
    """
    try:
        if not interaction.response.is_done():
            if embed:
                await interaction.response.send_message(message, ephemeral=ephemeral, embed=embed)
            else:
                await interaction.response.send_message(message, ephemeral=ephemeral)
            return True
        else:
            if embed:
                await interaction.followup.send(message, ephemeral=ephemeral, embed=embed)
            else:
                await interaction.followup.send(message, ephemeral=ephemeral)
            return True
    except Exception as e:
        logger.error(f"Failed to respond to interaction: {e}")
        return False

def get_interaction_user(interaction: discord.Interaction) -> Optional[Union[discord.User, discord.Member]]:
    """
    Get the user from an interaction with proper type handling
    
    Args:
        interaction: The interaction
        
    Returns:
        The user or None if not found
    """
    # In py-cord 2.6.1, interaction.user is available but in some older versions
    # we need to access interaction.user
    user = getattr(interaction, "user", None)
    if user is None:
        # Fall back to author for older versions
        user = getattr(interaction, "author", None)
    
    return user

def get_interaction_user_id(interaction: discord.Interaction) -> Optional[int]:
    """
    Get the user ID from an interaction with proper type handling
    
    Args:
        interaction: The interaction
        
    Returns:
        The user ID or None if not found
    """
    # In py-cord 2.6.1, interaction.user.id is available but in some older versions
    # we might need to access interaction.user_id directly
    user_id = getattr(interaction, "user_id", None)
    if user_id is None:
        # Fall back to user.id
        user = get_interaction_user(interaction)
        if user is not None:
            user_id = user.id
    
    return user_id

async def send_embed_response(
    ctx_or_interaction: Union[commands.Context, discord.Interaction],
    title: str,
    description: str,
    color: Union[discord.Color, int] = discord.Color.blue(),
    ephemeral: bool = False,
    fields: Optional[List[Dict[str, str]]] = None
) -> bool:
    """
    Send an embed response to either a context or interaction
    
    Args:
        ctx_or_interaction: The context or interaction
        title: The embed title
        description: The embed description
        color: The embed color
        ephemeral: Whether the response should be ephemeral (for interactions)
        fields: Optional list of fields to add to the embed
        
    Returns:
        True if sent successfully, False otherwise
    """
    try:
        embed = discord.Embed(
            title=title,
            description=description,
            color=color
        )
        
        if fields:
            for field in fields:
                embed.add_field(
                    name=field.get("name", ""),
                    value=field.get("value", ""),
                    inline=field.get("inline", False)
                )
        
        if isinstance(ctx_or_interaction, commands.Context):
            await ctx_or_interaction.send(embed=embed)
            return True
        elif isinstance(ctx_or_interaction, discord.Interaction):
            return await safely_respond_to_interaction(
                ctx_or_interaction, 
                "",  # Empty message, using embed for content
                ephemeral=ephemeral, 
                embed=embed
            )
        
        return False
    except Exception as e:
        logger.error(f"Failed to send embed response: {e}")
        return False

async def send_channel_message(
    channel: discord.abc.Messageable,
    message: str,
    embed: Optional[discord.Embed] = None
) -> Optional[discord.Message]:
    """
    Send a message to a channel with error handling
    
    Args:
        channel: The channel to send to
        message: The message to send
        embed: Optional embed to send
        
    Returns:
        The sent message or None if failed
    """
    try:
        if embed:
            return await channel.send(message, embed=embed)
        else:
            return await channel.send(message)
    except Exception as e:
        logger.error(f"Failed to send channel message: {e}")
        return None

async def update_message(
    message: discord.Message,
    new_content: Optional[str] = None,
    new_embed: Optional[discord.Embed] = None
) -> bool:
    """
    Update a message with error handling
    
    Args:
        message: The message to update
        new_content: Optional new content
        new_embed: Optional new embed
        
    Returns:
        True if updated successfully, False otherwise
    """
    try:
        kwargs = {}
        if new_content is not None:
            kwargs["content"] = new_content
        if new_embed is not None:
            kwargs["embed"] = new_embed
            
        if kwargs:
            await message.edit(**kwargs)
            return True
        
        return False
    except Exception as e:
        logger.error(f"Failed to update message: {e}")
        return False