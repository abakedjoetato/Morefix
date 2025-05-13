"""
Safe Attribute Access Module

This module provides safe attribute access for Discord objects,
handling different versions of Discord.py and py-cord.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple, Union, TypeVar, cast

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def safe_getattr(obj: Any, attr_name: str, default: Any = None) -> Any:
    """
    Safely get an attribute from an object, returning a default if it doesn't exist.
    
    Args:
        obj: The object to get the attribute from
        attr_name: The name of the attribute to get
        default: The default value to return if the attribute doesn't exist
        
    Returns:
        The attribute value or the default
    """
    if obj is None:
        return default
        
    try:
        return getattr(obj, attr_name, default)
    except Exception as e:
        logger.debug(f"Error getting attribute {attr_name}: {e}")
        return default

def safe_server_getattr(server: Any, attr_name: str, default: Any = None) -> Any:
    """
    Safely get an attribute from a server/guild, handling compatibility.
    
    Args:
        server: The server/guild object
        attr_name: The name of the attribute to get
        default: The default value to return if the attribute doesn't exist
        
    Returns:
        The attribute value or the default
    """
    if server is None:
        return default
        
    # Handle name and id specially
    if attr_name == 'name':
        try:
            return getattr(server, 'name', default)
        except:
            pass
            
        try:
            return getattr(server, 'guild_name', default)
        except:
            pass
            
    if attr_name == 'id':
        try:
            return getattr(server, 'id', default)
        except:
            pass
            
        try:
            return getattr(server, 'guild_id', default)
        except:
            pass
            
    return safe_getattr(server, attr_name, default)

def safe_member_getattr(member: Any, attr_name: str, default: Any = None) -> Any:
    """
    Safely get an attribute from a member, handling compatibility.
    
    Args:
        member: The member object
        attr_name: The name of the attribute to get
        default: The default value to return if the attribute doesn't exist
        
    Returns:
        The attribute value or the default
    """
    if member is None:
        return default
        
    # Handle name and id specially
    if attr_name == 'name':
        try:
            return getattr(member, 'name', default)
        except:
            pass
            
        try:
            return getattr(member, 'user_name', default)
        except:
            pass
            
        try:
            # Try to get user.name
            user = getattr(member, 'user', None)
            if user is not None:
                return getattr(user, 'name', default)
        except:
            pass
            
    if attr_name == 'id':
        try:
            return getattr(member, 'id', default)
        except:
            pass
            
        try:
            return getattr(member, 'user_id', default)
        except:
            pass
            
        try:
            # Try to get user.id
            user = getattr(member, 'user', None)
            if user is not None:
                return getattr(user, 'id', default)
        except:
            pass
            
    if attr_name == 'display_name':
        try:
            return getattr(member, 'display_name', default)
        except:
            pass
            
        try:
            return getattr(member, 'nick', default) or getattr(member, 'name', default)
        except:
            pass
            
    return safe_getattr(member, attr_name, default)

def safe_channel_getattr(channel: Any, attr_name: str, default: Any = None) -> Any:
    """
    Safely get an attribute from a channel, handling compatibility.
    
    Args:
        channel: The channel object
        attr_name: The name of the attribute to get
        default: The default value to return if the attribute doesn't exist
        
    Returns:
        The attribute value or the default
    """
    if channel is None:
        return default
        
    # Handle name and id specially
    if attr_name == 'name':
        try:
            return getattr(channel, 'name', default)
        except:
            pass
            
        try:
            return getattr(channel, 'channel_name', default)
        except:
            pass
            
    if attr_name == 'id':
        try:
            return getattr(channel, 'id', default)
        except:
            pass
            
        try:
            return getattr(channel, 'channel_id', default)
        except:
            pass
            
    return safe_getattr(channel, attr_name, default)

def safe_role_getattr(role: Any, attr_name: str, default: Any = None) -> Any:
    """
    Safely get an attribute from a role, handling compatibility.
    
    Args:
        role: The role object
        attr_name: The name of the attribute to get
        default: The default value to return if the attribute doesn't exist
        
    Returns:
        The attribute value or the default
    """
    if role is None:
        return default
        
    # Handle name and id specially
    if attr_name == 'name':
        try:
            return getattr(role, 'name', default)
        except:
            pass
            
        try:
            return getattr(role, 'role_name', default)
        except:
            pass
            
    if attr_name == 'id':
        try:
            return getattr(role, 'id', default)
        except:
            pass
            
        try:
            return getattr(role, 'role_id', default)
        except:
            pass
            
    return safe_getattr(role, attr_name, default)

def safe_message_getattr(message: Any, attr_name: str, default: Any = None) -> Any:
    """
    Safely get an attribute from a message, handling compatibility.
    
    Args:
        message: The message object
        attr_name: The name of the attribute to get
        default: The default value to return if the attribute doesn't exist
        
    Returns:
        The attribute value or the default
    """
    if message is None:
        return default
        
    # Handle content and id specially
    if attr_name == 'content':
        try:
            return getattr(message, 'content', default)
        except:
            pass
            
        try:
            return getattr(message, 'message_content', default)
        except:
            pass
            
    if attr_name == 'id':
        try:
            return getattr(message, 'id', default)
        except:
            pass
            
        try:
            return getattr(message, 'message_id', default)
        except:
            pass
            
    return safe_getattr(message, attr_name, default)