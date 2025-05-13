"""
Discord Intent Helpers

This module provides helper functions for working with Discord intents,
compatible with both discord.py and py-cord.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple, Union, TypeVar, cast

# Try importing different libraries
try:
    import discord
    from discord import Intents
    DISCORD_AVAILABLE = True
except ImportError:
    DISCORD_AVAILABLE = False

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_default_intents() -> Any:
    """
    Get default intents for Discord bot with compatibility for different versions.
    
    Returns:
        The default intents or None if Discord is not available
    """
    if not DISCORD_AVAILABLE:
        logger.error("Discord library not available. Cannot get default intents.")
        return None
        
    try:
        # Create default intents
        intents = Intents.default()
        
        # Add common intents
        intents.members = True
        intents.message_content = True
        intents.guild_messages = True
        intents.guild_reactions = True
        intents.guilds = True
        
        # Try to enable newer intents if available
        try:
            intents.presences = True
        except Exception:
            # Presences might be unavailable in some versions
            pass
            
        try:
            intents.auto_moderation = True
        except Exception:
            # Auto moderation might be unavailable in some versions
            pass
            
        return intents
    except Exception as e:
        logger.error(f"Error creating default intents: {e}")
        
        # Try alternate method for older versions
        try:
            intents = discord.Intents(
                guilds=True,
                members=True,
                messages=True,
                reactions=True
            )
            
            # Try to set message content for newer versions
            try:
                intents.message_content = True
            except Exception:
                # Message content might be unavailable in some versions
                pass
                
            return intents
        except Exception as alt_e:
            logger.error(f"Error creating alternate intents: {alt_e}")
            
            # Try to get all intents as last resort
            try:
                return discord.Intents.all()
            except Exception:
                # Return None if nothing works
                return None

def get_minimal_intents() -> Any:
    """
    Get minimal intents for Discord bot with compatibility for different versions.
    
    Returns:
        The minimal intents or None if Discord is not available
    """
    if not DISCORD_AVAILABLE:
        logger.error("Discord library not available. Cannot get minimal intents.")
        return None
        
    try:
        # Create minimal intents
        intents = Intents.default()
        
        # Ensure only necessary intents are enabled
        intents.members = False
        intents.presences = False
        intents.message_content = False
        
        # Make sure guild and messages are enabled
        intents.guilds = True
        intents.guild_messages = True
        
        return intents
    except Exception as e:
        logger.error(f"Error creating minimal intents: {e}")
        
        # Try alternate method for older versions
        try:
            intents = discord.Intents(
                guilds=True,
                messages=True
            )
            return intents
        except Exception as alt_e:
            logger.error(f"Error creating alternate minimal intents: {alt_e}")
            
            # Try to get default intents as last resort
            try:
                return discord.Intents.default()
            except Exception:
                # Return None if nothing works
                return None

def get_intents_by_name(intent_names: List[str]) -> Any:
    """
    Get intents by name for Discord bot with compatibility for different versions.
    
    Args:
        intent_names: List of intent names to enable
        
    Returns:
        The specified intents or None if Discord is not available
    """
    if not DISCORD_AVAILABLE:
        logger.error("Discord library not available. Cannot get intents by name.")
        return None
        
    try:
        # Create empty intents
        intents = discord.Intents.none()
        
        # Valid intent names to check for
        valid_intents = [
            'guilds', 'members', 'bans', 'emojis', 'integrations',
            'webhooks', 'invites', 'voice_states', 'presences',
            'messages', 'guild_messages', 'dm_messages', 'reactions',
            'guild_reactions', 'dm_reactions', 'typing', 'guild_typing',
            'dm_typing', 'message_content', 'scheduled_events'
        ]
        
        # Enable specified intents
        for name in intent_names:
            name = name.lower()
            if name in valid_intents:
                setattr(intents, name, True)
                
        return intents
    except Exception as e:
        logger.error(f"Error creating intents by name: {e}")
        return get_default_intents()  # Fall back to defaults