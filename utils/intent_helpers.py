"""
Intent Helpers for Discord API Compatibility

This module provides utilities for working with Discord gateway intents
across different versions of Discord libraries.
"""

import logging
from typing import Any, Dict, List, Optional, Set, Union

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

def get_default_intents() -> discord.Intents:
    """
    Get default intents compatible with both discord.py and py-cord.
    
    Returns:
        Default intents for the current Discord library
    """
    # Create default intents
    intents = discord.Intents.default()
    
    # Enable message content intent if available
    # (Required in discord.py 2.0+)
    if hasattr(intents, "message_content"):
        intents.message_content = True
        
    # Enable members intent
    intents.members = True
    
    # Enable presences intent
    if hasattr(intents, "presences"):
        intents.presences = True
        
    return intents

def get_all_intents() -> discord.Intents:
    """
    Get all intents compatible with both discord.py and py-cord.
    
    Returns:
        All intents for the current Discord library
    """
    # Create all intents
    intents = discord.Intents.all()
    
    return intents

def get_minimal_intents() -> discord.Intents:
    """
    Get minimal intents needed for basic bot functionality.
    
    Returns:
        Minimal intents for the current Discord library
    """
    # Create default intents
    intents = discord.Intents.default()
    
    # Disable typing events to reduce gateway traffic
    if hasattr(intents, "typing"):
        intents.typing = False
        
    # Disable presence updates to reduce gateway traffic
    if hasattr(intents, "presences"):
        intents.presences = False
        
    return intents

def create_intents(
    guilds: bool = True,
    members: bool = False,
    bans: bool = False,
    emojis: bool = False,
    integrations: bool = False,
    webhooks: bool = False,
    invites: bool = False,
    voice_states: bool = False,
    presences: bool = False,
    guild_messages: bool = True,
    dm_messages: bool = True,
    guild_reactions: bool = False,
    dm_reactions: bool = False,
    guild_typing: bool = False,
    dm_typing: bool = False,
    message_content: bool = False,
    scheduled_events: bool = False,
    auto_moderation: bool = False
) -> discord.Intents:
    """
    Create custom intents with compatibility across Discord library versions.
    
    Args:
        guilds: Whether to receive guild/server events
        members: Whether to receive member events
        bans: Whether to receive ban events
        emojis: Whether to receive emoji events
        integrations: Whether to receive integration events
        webhooks: Whether to receive webhook events
        invites: Whether to receive invite events
        voice_states: Whether to receive voice state events
        presences: Whether to receive presence (status) updates
        guild_messages: Whether to receive guild/server message events
        dm_messages: Whether to receive DM message events
        guild_reactions: Whether to receive guild/server reaction events
        dm_reactions: Whether to receive DM reaction events
        guild_typing: Whether to receive guild/server typing events
        dm_typing: Whether to receive DM typing events
        message_content: Whether to receive message content
        scheduled_events: Whether to receive scheduled event events
        auto_moderation: Whether to receive auto moderation events
        
    Returns:
        Custom intents for the current Discord library
    """
    # Start with empty intents
    intents = discord.Intents.none()
    
    # Set common intents
    intents.guilds = guilds
    intents.members = members
    intents.bans = bans
    intents.webhooks = webhooks
    intents.invites = invites
    intents.voice_states = voice_states
    
    # Set message intents
    if hasattr(intents, "guild_messages"):
        # discord.py style
        intents.guild_messages = guild_messages
        intents.dm_messages = dm_messages
        intents.guild_reactions = guild_reactions
        intents.dm_reactions = dm_reactions
        intents.guild_typing = guild_typing
        intents.dm_typing = dm_typing
    else:
        # py-cord style
        intents.messages = guild_messages or dm_messages
        intents.reactions = guild_reactions or dm_reactions
        intents.typing = guild_typing or dm_typing
        
    # Set emoji/sticker intents
    if hasattr(intents, "emojis"):
        intents.emojis = emojis
    elif hasattr(intents, "emojis_and_stickers"):
        intents.emojis_and_stickers = emojis
        
    # Set integration intents
    if hasattr(intents, "integrations"):
        intents.integrations = integrations
        
    # Set presence intents
    if hasattr(intents, "presences"):
        intents.presences = presences
        
    # Set message content intent
    if hasattr(intents, "message_content"):
        intents.message_content = message_content
        
    # Set scheduled events intent
    if hasattr(intents, "scheduled_events"):
        intents.scheduled_events = scheduled_events
        
    # Set auto moderation intent
    if hasattr(intents, "auto_moderation"):
        intents.auto_moderation = auto_moderation
    elif hasattr(intents, "auto_moderation_configuration"):
        intents.auto_moderation_configuration = auto_moderation
        intents.auto_moderation_execution = auto_moderation
        
    return intents

def merge_intents(
    *intents_list: discord.Intents
) -> discord.Intents:
    """
    Merge multiple intents objects.
    
    Args:
        *intents_list: Discord intents objects to merge
        
    Returns:
        Merged intents
    """
    # Start with empty intents
    result = discord.Intents.none()
    
    # For each intent object
    for intents in intents_list:
        # Skip None values
        if intents is None:
            continue
            
        # For each intent flag
        for name, value in intents.__dict__.items():
            # Skip private attributes
            if name.startswith("_"):
                continue
                
            # Set the flag if any input has it enabled
            if value:
                setattr(result, name, True)
                
    return result

def create_bot_with_intents(
    intents: Optional[discord.Intents] = None,
    **kwargs
) -> commands.Bot:
    """
    Create a bot with compatible intents.
    
    Args:
        intents: Intents to use, or None for default intents
        **kwargs: Additional arguments to pass to the Bot constructor
        
    Returns:
        Bot instance
    """
    # Get default intents if not provided
    if intents is None:
        intents = get_default_intents()
        
    # Create the bot
    bot = commands.Bot(
        intents=intents,
        **kwargs
    )
    
    return bot

def add_required_intents(
    bot: commands.Bot,
    guild_messages: bool = True,
    message_content: bool = True,
    members: bool = True
) -> None:
    """
    Add required intents to an existing bot.
    
    This function modifies the bot's intents to ensure that required
    intents are enabled.
    
    Args:
        bot: Bot to modify
        guild_messages: Whether to enable guild messages intent
        message_content: Whether to enable message content intent
        members: Whether to enable members intent
    """
    # Get the bot's intents
    intents = bot.intents
    
    # Set message intents
    if guild_messages:
        if hasattr(intents, "guild_messages"):
            # discord.py style
            intents.guild_messages = True
        elif hasattr(intents, "messages"):
            # py-cord style
            intents.messages = True
            
    # Set message content intent
    if message_content and hasattr(intents, "message_content"):
        intents.message_content = True
        
    # Set members intent
    if members:
        intents.members = True