"""
Premium feature access management
Handles permissions and access to premium features
"""

import functools
import discord
from config import PREMIUM_TIERS

# Premium features available in the system
PREMIUM_FEATURES = {
    # Core features
    "log_parsing": {
        "description": "Parse server logs for activity tracking",
        "min_tier": "basic"
    },
    "advanced_stats": {
        "description": "Access to detailed player statistics and analytics",
        "min_tier": "basic"
    },
    "stats": {
        "description": "Player statistics tracking and analytics",
        "min_tier": "basic"
    },
    "player_links": {
        "description": "Link Discord users to in-game players",
        "min_tier": "basic"
    },
    "killfeed": {
        "description": "Real-time kill feed notifications",
        "min_tier": "basic"
    },
    "events": {
        "description": "Server event tracking and notifications",
        "min_tier": "basic"
    },
    
    # Pro features
    "custom_notifications": {
        "description": "Customizable notifications for server events",
        "min_tier": "pro"
    },
    "data_export": {
        "description": "Export player and server data to CSV",
        "min_tier": "pro"
    },
    "priority_support": {
        "description": "Priority access to support channels",
        "min_tier": "pro"
    },
    
    # Enterprise features
    "auto_moderation": {
        "description": "Automated moderation based on player behavior",
        "min_tier": "enterprise"
    },
    "custom_integration": {
        "description": "Custom integration with other services",
        "min_tier": "enterprise"
    },
    "dedicated_support": {
        "description": "Dedicated support channel with custom SLAs",
        "min_tier": "enterprise"
    }
}

# Server limits based on premium tier
SERVER_LIMITS = {
    "free": {
        "max_players_tracked": 100,
        "analytics_retention_days": 7,
        "log_imports_per_day": 3,
        "user_data_exports_per_month": 0
    },
    "basic": {
        "max_players_tracked": 250,
        "analytics_retention_days": 30,
        "log_imports_per_day": 10,
        "user_data_exports_per_month": 1
    },
    "pro": {
        "max_players_tracked": 1000,
        "analytics_retention_days": 90,
        "log_imports_per_day": 50,
        "user_data_exports_per_month": 10
    },
    "enterprise": {
        "max_players_tracked": 5000,
        "analytics_retention_days": 365,
        "log_imports_per_day": 100,
        "user_data_exports_per_month": 100
    }
}

def get_feature_access(feature_name, guild_tier):
    """
    Check if a feature is available for a given premium tier
    
    Args:
        feature_name: Name of the feature to check
        guild_tier: Premium tier of the guild ("free", "basic", "pro", "enterprise")
        
    Returns:
        bool: True if the feature is available, False otherwise
    """
    if feature_name not in PREMIUM_FEATURES:
        return False
        
    tier_levels = ["free", "basic", "pro", "enterprise"]
    feature_min_tier = PREMIUM_FEATURES[feature_name]["min_tier"]
    
    # Free tier has access to no premium features
    if guild_tier == "free":
        return False
        
    # Get the index of the tiers for comparison
    guild_tier_index = tier_levels.index(guild_tier)
    feature_tier_index = tier_levels.index(feature_min_tier)
    
    # Guild has access if its tier is equal or higher than the feature's required tier
    return guild_tier_index >= feature_tier_index

def get_server_limits(guild_tier):
    """
    Get the server limits for a given premium tier
    
    Args:
        guild_tier: Premium tier of the guild
        
    Returns:
        dict: Server limits for the given tier
    """
    if guild_tier not in SERVER_LIMITS:
        # Default to free tier if unknown
        return SERVER_LIMITS["free"]
        
    return SERVER_LIMITS[guild_tier]

def check_premium_feature_access(guild_id, feature_name, guild_tier="free"):
    """
    Check if a guild has access to a premium feature
    
    Args:
        guild_id: ID of the guild to check
        feature_name: Name of the feature to check
        guild_tier: Current premium tier of the guild (defaults to "free")
        
    Returns:
        bool: True if the guild has access to the feature, False otherwise
    """
    # Apply the standard feature access logic
    return get_feature_access(feature_name, guild_tier)

def get_feature_tier_requirement(feature_name):
    """
    Get the minimum tier required for a premium feature
    
    Args:
        feature_name: Name of the feature to check
        
    Returns:
        str: Minimum tier required ("basic", "pro", "enterprise") or None if invalid
    """
    if feature_name not in PREMIUM_FEATURES:
        return None
        
    return PREMIUM_FEATURES[feature_name]["min_tier"]

def get_features_for_tier(tier):
    """
    Get a list of features available for a specific premium tier
    
    Args:
        tier: Premium tier to check ("free", "basic", "pro", "enterprise")
        
    Returns:
        list: List of feature names available for the tier
    """
    tier_levels = ["free", "basic", "pro", "enterprise"]
    if tier not in tier_levels:
        return []
        
    tier_index = tier_levels.index(tier)
    available_features = []
    
    # Free tier has no premium features
    if tier == "free":
        return []
    
    # Check each feature's minimum tier level
    for feature_name, feature_data in PREMIUM_FEATURES.items():
        feature_min_tier = feature_data["min_tier"]
        feature_tier_index = tier_levels.index(feature_min_tier)
        
        # Include feature if the tier level is sufficient
        if tier_index >= feature_tier_index:
            available_features.append(feature_name)
            
    return available_features

def verify_premium_tier(guild_id, required_tier):
    """
    Verify that a guild has at least the specified premium tier
    
    Args:
        guild_id: ID of the guild to check
        required_tier: Minimum tier required ("free", "basic", "pro", "enterprise")
        
    Returns:
        tuple: (has_access, current_tier) where has_access is a boolean and
               current_tier is the guild's current tier as a string
    """
    # For this implementation, we'll mock a database lookup to determine the guild's tier
    # In a real implementation, this would query the database to get the guild's actual tier
    tier_levels = ["free", "basic", "pro", "enterprise"]
    
    # Pretend to look up the guild's tier - for now returning a default value
    # This would normally be a database query
    current_tier = "free"
    
    # Special case - if the required tier is "free", everyone has access
    if required_tier == "free":
        return True, current_tier
        
    # Get the indices for comparison
    if required_tier not in tier_levels or current_tier not in tier_levels:
        return False, current_tier
        
    required_tier_index = tier_levels.index(required_tier)
    current_tier_index = tier_levels.index(current_tier)
    
    # Check if the guild's tier is at least the required tier
    has_access = current_tier_index >= required_tier_index
    
    return has_access, current_tier

def verify_premium_feature(guild_id, feature_name):
    """
    Verify that a guild has access to a specific premium feature
    
    Args:
        guild_id: ID of the guild to check
        feature_name: Name of the feature to check
        
    Returns:
        tuple: (has_access, current_tier, required_tier) where has_access is a boolean,
               current_tier is the guild's current tier, and required_tier is the
               minimum tier required for the feature
    """
    # Get the minimum tier required for this feature
    required_tier = get_feature_tier_requirement(feature_name)
    if not required_tier:
        # Feature doesn't exist
        return False, "unknown", "unknown"
    
    # Mock lookup of guild's premium tier - this would be a database query in a real implementation
    current_tier = "free"  # Default to free tier
    
    # Check if the guild's tier is sufficient for this feature
    has_access = get_feature_access(feature_name, current_tier)
    
    return has_access, current_tier, required_tier

def check_feature_access(guild_id, feature_name):
    """
    Check if a guild has access to a specific feature
    
    Args:
        guild_id: ID of the guild to check
        feature_name: Name of the feature to check
        
    Returns:
        bool: True if the guild has access to the feature, False otherwise
    """
    # Look up the guild's premium tier
    # In a real implementation, this would be a database query
    guild_tier = "free"  # Default to free tier
    
    # Check if the feature is available for this tier
    has_access = get_feature_access(feature_name, guild_tier)
    
    return has_access

def get_guild_premium_tier(guild_id):
    """
    Get the premium tier of a guild
    
    Args:
        guild_id: ID of the guild to check
        
    Returns:
        str: The premium tier of the guild ("free", "basic", "pro", "enterprise")
    """
    # In a real implementation, this would be a database query
    # For now, we'll always return "free" as the default tier
    return "free"

def premium_tier_required(tier):
    """
    Decorator to restrict commands to premium tier guilds
    
    Args:
        tier: Minimum tier required ("free", "basic", "pro", "enterprise")
    
    Returns:
        Decorator function that checks the guild's tier
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Get the context from the first argument
            # This could be a ctx or an interaction depending on the command type
            ctx_or_interaction = args[0]
            
            # Get the guild ID from the context
            if hasattr(ctx_or_interaction, 'guild_id'):
                # Interaction
                guild_id = ctx_or_interaction.guild_id
            elif hasattr(ctx_or_interaction, 'guild') and ctx_or_interaction.guild:
                # Traditional context
                guild_id = ctx_or_interaction.guild.id
            else:
                # Default to no guild
                guild_id = None
                
            if not guild_id:
                # Not in a guild
                return await ctx_or_interaction.send("This command must be used in a server.", ephemeral=True)
                
            # Check if the guild has the required tier
            has_access, current_tier = verify_premium_tier(guild_id, tier)
            
            if not has_access:
                # Guild doesn't have the required tier
                embed = discord.Embed(
                    title="Premium Feature",
                    description=f"This command requires the {tier.capitalize()} tier or higher.\n"
                               f"Your server is currently on the {current_tier.capitalize()} tier.",
                    color=0xFF5555
                )
                embed.add_field(name="Upgrade", value="Contact the bot owner to upgrade your server's tier.")
                
                if hasattr(ctx_or_interaction, 'send'):
                    await ctx_or_interaction.send(embed=embed, ephemeral=True)
                else:
                    await ctx_or_interaction.response.send_message(embed=embed, ephemeral=True)
                return None
                
            # Guild has access, execute the command
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def check_tier_access(guild_id, required_tier):
    """
    Check if a guild has access to features at the specified tier
    
    Args:
        guild_id: ID of the guild to check
        required_tier: Minimum tier required ("free", "basic", "pro", "enterprise")
        
    Returns:
        bool: True if the guild has access to the specified tier, False otherwise
    """
    # In a real implementation, this would be a database query
    # For now, we'll use the default tier
    current_tier = get_guild_premium_tier(guild_id)
    
    # Get the tier levels for comparison
    tier_levels = ["free", "basic", "pro", "enterprise"]
    
    # Special case - if the required tier is "free", everyone has access
    if required_tier == "free":
        return True
        
    # Get the indices for comparison
    if required_tier not in tier_levels or current_tier not in tier_levels:
        return False
        
    required_tier_index = tier_levels.index(required_tier)
    current_tier_index = tier_levels.index(current_tier)
    
    # Check if the guild's tier is at least the required tier
    return current_tier_index >= required_tier_index