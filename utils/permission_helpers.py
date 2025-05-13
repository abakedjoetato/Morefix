"""
Permission Helpers for Discord API Compatibility

This module provides utilities for working with Discord permissions
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

# Import attribute_access utility for safe attribute access
from utils.attribute_access import (
    safe_channel_getattr,
    safe_member_getattr,
    safe_role_getattr,
    safe_server_getattr
)

def get_channel_permissions(
    channel: Any,
    member: Any
) -> discord.Permissions:
    """
    Get a member's permissions in a channel with compatibility.
    
    Args:
        channel: Discord channel
        member: Discord member
        
    Returns:
        Permissions object
    """
    # Try specific overloads based on Discord library version
    try:
        # Use channel.permissions_for(member) method if available
        if hasattr(channel, "permissions_for"):
            return channel.permissions_for(member)
            
        # Try getting permissions from member for the channel
        if hasattr(member, "permissions_in"):
            return member.permissions_in(channel)
            
        # Fall back to permissions attribute for the member
        if hasattr(member, "guild_permissions"):
            return member.guild_permissions
            
        # Last resort: create default permissions
        return discord.Permissions.none()
    except Exception as e:
        logger.error(f"Error getting channel permissions: {e}")
        return discord.Permissions.none()

def has_permission(
    permissions: discord.Permissions,
    permission_name: str
) -> bool:
    """
    Check if permissions has a specific permission.
    
    Args:
        permissions: Permissions object
        permission_name: Permission name to check (e.g., "manage_messages")
        
    Returns:
        True if the permissions has the specified permission, False otherwise
    """
    try:
        # Check if the permission exists
        if hasattr(permissions, permission_name):
            return getattr(permissions, permission_name)
            
        # Check for administrator permission
        if permission_name != "administrator" and hasattr(permissions, "administrator"):
            if permissions.administrator:
                return True
                
        return False
    except Exception as e:
        logger.error(f"Error checking permission {permission_name}: {e}")
        return False

def has_channel_permission(
    channel: Any,
    member: Any,
    permission_name: str
) -> bool:
    """
    Check if a member has a specific permission in a channel.
    
    Args:
        channel: Discord channel
        member: Discord member
        permission_name: Permission name to check (e.g., "manage_messages")
        
    Returns:
        True if the member has the specified permission, False otherwise
    """
    # Get the member's permissions in the channel
    permissions = get_channel_permissions(channel, member)
    
    # Check the permission
    return has_permission(permissions, permission_name)

def get_required_permissions() -> discord.Permissions:
    """
    Get the permissions required for the bot to function properly.
    
    Returns:
        Required permissions
    """
    # Create basic permissions
    permissions = discord.Permissions.none()
    
    # Add required permissions
    permissions.read_messages = True  # View Channels
    permissions.send_messages = True
    permissions.embed_links = True
    permissions.attach_files = True
    permissions.read_message_history = True
    permissions.add_reactions = True
    
    # Additional permissions for advanced features
    permissions.manage_messages = True
    permissions.manage_webhooks = True
    
    return permissions

def get_permission_names(permissions: discord.Permissions) -> List[str]:
    """
    Get the names of enabled permissions.
    
    Args:
        permissions: Permissions object
        
    Returns:
        List of enabled permission names
    """
    # Get enabled permissions
    result = []
    
    # Check each permission
    for name, value in permissions:
        if value:
            result.append(name)
            
    return result

def format_permissions(permissions: discord.Permissions) -> str:
    """
    Format permissions for display.
    
    Args:
        permissions: Permissions object
        
    Returns:
        Formatted permission string
    """
    # Get enabled permissions
    names = get_permission_names(permissions)
    
    # Format permissions
    if not names:
        return "No permissions"
        
    return ", ".join(name.replace("_", " ").title() for name in names)

def create_permissions(**kwargs) -> discord.Permissions:
    """
    Create permissions with the specified values.
    
    Args:
        **kwargs: Permission names and values
        
    Returns:
        Permissions object
    """
    # Create empty permissions
    permissions = discord.Permissions.none()
    
    # Set permissions
    for name, value in kwargs.items():
        if hasattr(permissions, name):
            setattr(permissions, name, bool(value))
            
    return permissions

def merge_permissions(*permissions_list) -> discord.Permissions:
    """
    Merge multiple permissions objects.
    
    Args:
        *permissions_list: Permissions objects to merge
        
    Returns:
        Merged permissions
    """
    # Create empty permissions
    result = discord.Permissions.none()
    
    # Merge permissions
    for permissions in permissions_list:
        # Skip None values
        if permissions is None:
            continue
            
        # Get the permissions value
        if isinstance(permissions, int):
            result.value |= permissions
        else:
            result.value |= permissions.value
            
    return result

def can_run_command(
    ctx: commands.Context,
    command: commands.Command
) -> bool:
    """
    Check if a command can be run in the current context.
    
    Args:
        ctx: Command context
        command: Command to check
        
    Returns:
        True if the command can be run, False otherwise
    """
    try:
        # Check if the command is enabled
        if not command.enabled:
            return False
            
        # Check if the command is hidden
        if command.hidden and not ctx.author.guild_permissions.administrator:
            return False
            
        # Check command checks
        for check in command.checks:
            if not check(ctx):
                return False
                
        return True
    except Exception as e:
        logger.error(f"Error checking if command can be run: {e}")
        return False

def is_admin(member: Any) -> bool:
    """
    Check if a member is an administrator.
    
    Args:
        member: Discord member
        
    Returns:
        True if the member is an administrator, False otherwise
    """
    # Check if the member is the server owner
    if safe_member_getattr(member, "id") == safe_server_getattr(safe_member_getattr(member, "guild"), "owner_id"):
        return True
        
    # Check if the member has administrator permission
    return bool(safe_member_getattr(member, "guild_permissions").administrator)

def has_role(member: Any, role_id: int) -> bool:
    """
    Check if a member has a role.
    
    Args:
        member: Discord member
        role_id: Role ID
        
    Returns:
        True if the member has the role, False otherwise
    """
    # Get the member's roles
    roles = safe_member_getattr(member, "roles", [])
    
    # Check if the member has the role
    for role in roles:
        if safe_role_getattr(role, "id") == role_id:
            return True
            
    return False

def has_any_role(member: Any, role_ids: List[int]) -> bool:
    """
    Check if a member has any of the specified roles.
    
    Args:
        member: Discord member
        role_ids: List of role IDs
        
    Returns:
        True if the member has any of the roles, False otherwise
    """
    # Get the member's roles
    roles = safe_member_getattr(member, "roles", [])
    
    # Check if the member has any of the roles
    for role in roles:
        if safe_role_getattr(role, "id") in role_ids:
            return True
            
    return False

def has_all_roles(member: Any, role_ids: List[int]) -> bool:
    """
    Check if a member has all of the specified roles.
    
    Args:
        member: Discord member
        role_ids: List of role IDs
        
    Returns:
        True if the member has all of the roles, False otherwise
    """
    # Get the member's roles
    member_role_ids = [safe_role_getattr(role, "id") for role in safe_member_getattr(member, "roles", [])]
    
    # Check if the member has all of the roles
    for role_id in role_ids:
        if role_id not in member_role_ids:
            return False
            
    return True

def get_highest_role(member: Any) -> Any:
    """
    Get a member's highest role.
    
    Args:
        member: Discord member
        
    Returns:
        Highest role, or None if the member has no roles
    """
    # Get the member's roles
    roles = safe_member_getattr(member, "roles", [])
    
    # Return the highest role
    if not roles:
        return None
        
    return max(roles, key=lambda r: safe_role_getattr(r, "position", 0))

def get_role_position(role: Any) -> int:
    """
    Get a role's position.
    
    Args:
        role: Discord role
        
    Returns:
        Role position
    """
    return safe_role_getattr(role, "position", 0)

def can_manage_role(member: Any, role: Any) -> bool:
    """
    Check if a member can manage a role.
    
    Args:
        member: Discord member
        role: Discord role
        
    Returns:
        True if the member can manage the role, False otherwise
    """
    # Check if the member is the server owner
    if safe_member_getattr(member, "id") == safe_server_getattr(safe_member_getattr(member, "guild"), "owner_id"):
        return True
        
    # Check if the member has administrator permission
    if has_permission(safe_member_getattr(member, "guild_permissions"), "administrator"):
        return True
        
    # Check if the member has manage roles permission
    if not has_permission(safe_member_getattr(member, "guild_permissions"), "manage_roles"):
        return False
        
    # Check if the member's highest role is higher than the role
    highest_role = get_highest_role(member)
    if highest_role is None:
        return False
        
    return get_role_position(highest_role) > get_role_position(role)