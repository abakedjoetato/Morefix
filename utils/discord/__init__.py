"""
Discord Compatibility Layer package

This package provides compatibility layers for Discord API interactions,
supporting both discord.py and py-cord 2.6.1.
"""

from utils.attribute_access import (
    safe_getattr,
    safe_server_getattr,
    safe_member_getattr,
    safe_channel_getattr,
    safe_role_getattr,
    safe_message_getattr
)

from utils.interaction_handlers import (
    is_interaction,
    is_context,
    safely_respond_to_interaction,
    hybrid_send,
    get_user,
    get_guild,
    get_guild_id
)

__all__ = [
    # Attribute access
    'safe_getattr',
    'safe_server_getattr',
    'safe_member_getattr',
    'safe_channel_getattr',
    'safe_role_getattr',
    'safe_message_getattr',
    
    # Interaction handlers
    'is_interaction',
    'is_context',
    'safely_respond_to_interaction',
    'hybrid_send',
    'get_user',
    'get_guild',
    'get_guild_id'
]