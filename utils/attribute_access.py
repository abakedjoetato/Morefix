"""
Attribute Access Safety Module

This module provides utility functions for safely accessing attributes of Discord objects,
especially server objects where attributes may have different names or structure across
different versions of discord.py and py-cord.
"""

import logging
from typing import Any, Dict, List, Optional, TypeVar, Union

# Setup logger
logger = logging.getLogger(__name__)

def safe_server_getattr(server: Any, attr: str, default: Any = None) -> Any:
    """
    Safely get an attribute from a server object with version compatibility.
    
    This handles different attribute names between discord.py and py-cord,
    especially for server/guild objects.
    
    Args:
        server: The server/guild object
        attr: The attribute name to access
        default: Default value if attribute doesn't exist
        
    Returns:
        The attribute value or default
    """
    if server is None:
        return default
    
    # Define attribute mappings for different versions
    # Format: {requested_attr: [possible_names]}
    attr_mappings = {
        "name": ["name", "server_name"],
        "id": ["id", "guild_id", "server_id", "_id"],
        "owner_id": ["owner_id", "owner"],
        "region": ["region", "voice_region"],
        "icon": ["icon", "icon_url", "icon_id"],
        "features": ["features", "server_features"],
        "splash": ["splash", "splash_url"],
        "banner": ["banner", "banner_url"],
        "description": ["description", "server_description"],
        "verification_level": ["verification_level", "verify_level"],
        "default_notifications": ["default_notifications", "default_notification_level"],
        "explicit_content_filter": ["explicit_content_filter", "explicit_filter"],
        "roles": ["roles", "role_ids"],
        "emojis": ["emojis", "emoji_ids"],
        "members": ["members", "member_count", "approximate_member_count"],
        "channels": ["channels", "channel_ids"],
    }
    
    # Check if we have a mapping for this attribute
    if attr in attr_mappings:
        # Try each possible attribute name
        for possible_attr in attr_mappings[attr]:
            try:
                value = getattr(server, possible_attr, None)
                if value is not None:
                    return value
            except Exception as e:
                # Log error at debug level since this is expected for some attributes
                logger.debug(f"Error getting attribute {possible_attr} from server: {e}")
        
        # If we get here, none of the mapped attributes existed
        return default
    
    # For attributes without mappings, just use normal getattr
    try:
        return getattr(server, attr, default)
    except Exception as e:
        logger.warning(f"Error getting unmapped attribute {attr} from server: {e}")
        return default

def safe_member_getattr(member: Any, attr: str, default: Any = None) -> Any:
    """
    Safely get an attribute from a member object with version compatibility.
    
    Args:
        member: The member object
        attr: The attribute name to access
        default: Default value if attribute doesn't exist
        
    Returns:
        The attribute value or default
    """
    if member is None:
        return default
    
    # Define attribute mappings for different versions
    attr_mappings = {
        "name": ["name", "username"],
        "id": ["id", "user_id", "_id"],
        "discriminator": ["discriminator", "discrim"],
        "avatar": ["avatar", "avatar_url", "avatar_id"],
        "bot": ["bot", "is_bot"],
        "system": ["system", "is_system"],
        "display_name": ["display_name", "nick", "nickname"],
        "roles": ["roles", "role_ids"],
        "joined_at": ["joined_at", "join_date"],
        "premium_since": ["premium_since", "boosting_since"],
        "pending": ["pending", "is_pending"],
    }
    
    # Check if we have a mapping for this attribute
    if attr in attr_mappings:
        # Try each possible attribute name
        for possible_attr in attr_mappings[attr]:
            try:
                value = getattr(member, possible_attr, None)
                if value is not None:
                    return value
            except Exception as e:
                logger.debug(f"Error getting attribute {possible_attr} from member: {e}")
        
        # If we get here, none of the mapped attributes existed
        return default
    
    # For attributes without mappings, just use normal getattr
    try:
        return getattr(member, attr, default)
    except Exception as e:
        logger.warning(f"Error getting unmapped attribute {attr} from member: {e}")
        return default

def safe_channel_getattr(channel: Any, attr: str, default: Any = None) -> Any:
    """
    Safely get an attribute from a channel object with version compatibility.
    
    Args:
        channel: The channel object
        attr: The attribute name to access
        default: Default value if attribute doesn't exist
        
    Returns:
        The attribute value or default
    """
    if channel is None:
        return default
    
    # Define attribute mappings for different versions
    attr_mappings = {
        "name": ["name", "channel_name"],
        "id": ["id", "channel_id", "_id"],
        "guild_id": ["guild_id", "guild", "server_id"],
        "position": ["position", "channel_position"],
        "nsfw": ["nsfw", "is_nsfw"],
        "category_id": ["category_id", "parent_id", "parent"],
        "type": ["type", "channel_type"],
        "topic": ["topic", "channel_topic"],
        "slowmode_delay": ["slowmode_delay", "rate_limit_per_user"],
        "members": ["members", "member_ids"],
        "user_limit": ["user_limit", "max_users"],
        "bitrate": ["bitrate", "voice_bitrate"],
    }
    
    # Check if we have a mapping for this attribute
    if attr in attr_mappings:
        # Try each possible attribute name
        for possible_attr in attr_mappings[attr]:
            try:
                value = getattr(channel, possible_attr, None)
                if value is not None:
                    return value
            except Exception as e:
                logger.debug(f"Error getting attribute {possible_attr} from channel: {e}")
        
        # If we get here, none of the mapped attributes existed
        return default
    
    # For attributes without mappings, just use normal getattr
    try:
        return getattr(channel, attr, default)
    except Exception as e:
        logger.warning(f"Error getting unmapped attribute {attr} from channel: {e}")
        return default

def safe_role_getattr(role: Any, attr: str, default: Any = None) -> Any:
    """
    Safely get an attribute from a role object with version compatibility.
    
    Args:
        role: The role object
        attr: The attribute name to access
        default: Default value if attribute doesn't exist
        
    Returns:
        The attribute value or default
    """
    if role is None:
        return default
    
    # Define attribute mappings for different versions
    attr_mappings = {
        "name": ["name", "role_name"],
        "id": ["id", "role_id", "_id"],
        "guild_id": ["guild_id", "guild", "server_id"],
        "position": ["position", "role_position"],
        "permissions": ["permissions", "role_permissions"],
        "color": ["color", "colour", "role_color"],
        "hoist": ["hoist", "is_hoisted"],
        "managed": ["managed", "is_managed"],
        "mentionable": ["mentionable", "is_mentionable"],
        "tags": ["tags", "role_tags"],
    }
    
    # Check if we have a mapping for this attribute
    if attr in attr_mappings:
        # Try each possible attribute name
        for possible_attr in attr_mappings[attr]:
            try:
                value = getattr(role, possible_attr, None)
                if value is not None:
                    return value
            except Exception as e:
                logger.debug(f"Error getting attribute {possible_attr} from role: {e}")
        
        # If we get here, none of the mapped attributes existed
        return default
    
    # For attributes without mappings, just use normal getattr
    try:
        return getattr(role, attr, default)
    except Exception as e:
        logger.warning(f"Error getting unmapped attribute {attr} from role: {e}")
        return default

def safe_message_getattr(message: Any, attr: str, default: Any = None) -> Any:
    """
    Safely get an attribute from a message object with version compatibility.
    
    Args:
        message: The message object
        attr: The attribute name to access
        default: Default value if attribute doesn't exist
        
    Returns:
        The attribute value or default
    """
    if message is None:
        return default
    
    # Define attribute mappings for different versions
    attr_mappings = {
        "content": ["content", "message_content"],
        "id": ["id", "message_id", "_id"],
        "channel_id": ["channel_id", "channel"],
        "guild_id": ["guild_id", "guild"],
        "author": ["author", "user", "sender"],
        "created_at": ["created_at", "timestamp", "date"],
        "edited_at": ["edited_at", "edit_timestamp"],
        "embeds": ["embeds", "message_embeds"],
        "attachments": ["attachments", "message_attachments"],
        "pinned": ["pinned", "is_pinned"],
        "reactions": ["reactions", "message_reactions"],
        "mentions": ["mentions", "message_mentions"],
    }
    
    # Check if we have a mapping for this attribute
    if attr in attr_mappings:
        # Try each possible attribute name
        for possible_attr in attr_mappings[attr]:
            try:
                value = getattr(message, possible_attr, None)
                if value is not None:
                    return value
            except Exception as e:
                logger.debug(f"Error getting attribute {possible_attr} from message: {e}")
        
        # If we get here, none of the mapped attributes existed
        return default
    
    # For attributes without mappings, just use normal getattr
    try:
        return getattr(message, attr, default)
    except Exception as e:
        logger.warning(f"Error getting unmapped attribute {attr} from message: {e}")
        return default