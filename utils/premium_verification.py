"""
Premium Feature Verification System

This module provides a standardized interface for verifying premium feature access.
It handles all the necessary database queries, error handling, and type checking.
"""

import logging
import functools
from typing import Any, Dict, List, Optional, Union, Tuple, Callable
from utils.safe_database import (
    get_document_safely, 
    safe_get, 
    get_field_with_type_check,
    is_db_available
)

logger = logging.getLogger(__name__)

# Premium tier levels - ordered from lowest to highest
TIER_LEVELS = {
    "free": 0,
    "basic": 1,
    "standard": 2,
    "pro": 3,
    "enterprise": 4
}

# Feature to tier mapping
FEATURE_TIERS = {
    "advanced_analytics": 2,  # standard tier
    "custom_reports": 3,      # pro tier
    "priority_support": 1,    # basic tier
    "extended_history": 2,    # standard tier
    "custom_branding": 3,     # pro tier
    "advanced_permissions": 3, # pro tier
    "api_access": 3,          # pro tier
    "unlimited_storage": 4,   # enterprise tier
    "dedicated_support": 4,   # enterprise tier
    "custom_integration": 4,  # enterprise tier
    "multi_team": 3,          # pro tier
    "enhanced_security": 3    # pro tier
}

def normalize_feature_name(feature_name: str) -> str:
    """
    Normalize a feature name for consistent lookup.
    
    Args:
        feature_name: Raw feature name
        
    Returns:
        Normalized feature name
    """
    # Convert to lowercase and replace spaces/hyphens with underscores
    normalized = feature_name.lower().replace(' ', '_').replace('-', '_')
    
    # Remove any non-alphanumeric characters (except underscores)
    normalized = ''.join(c for c in normalized if c.isalnum() or c == '_')
    
    return normalized

def get_required_tier_for_feature(feature_name: str) -> int:
    """
    Get the required tier level for a feature.
    
    Args:
        feature_name: Feature to check (will be normalized)
        
    Returns:
        int: Required tier level (0-4)
    """
    normalized_name = normalize_feature_name(feature_name)
    
    # Check if we have a specific tier requirement for this feature
    if normalized_name in FEATURE_TIERS:
        return FEATURE_TIERS[normalized_name]
    
    # Default to standard tier (2) if not specifically defined
    logger.warning(f"Feature '{feature_name}' not found in tier mappings, defaulting to tier 2")
    return 2

async def get_guild_tier(db, guild_id: Union[str, int]) -> int:
    """
    Get a guild's premium tier.
    
    Args:
        db: Database connection
        guild_id: Discord guild ID
        
    Returns:
        int: Guild's premium tier (0-4)
    """
    # Validate inputs
    if not is_db_available(db):
        logger.error("Database not available for guild tier lookup")
        return 0
    
    str_guild_id = str(guild_id)
    
    try:
        # Get the guild's premium configuration
        guilds_collection = db.guilds
        guild_doc = await get_document_safely(guilds_collection, {"guild_id": str_guild_id})
        
        if not guild_doc:
            # Guild not found, default to free tier
            return 0
        
        # Get tier information (priority order: premium_tier as int, tier_name mapped to int, default to 0)
        tier = get_field_with_type_check(guild_doc, "premium_tier", int, None)
        
        if tier is not None:
            return max(0, min(tier, 4))  # Clamp between 0-4
        
        # Try to get tier by name
        tier_name = safe_get(guild_doc, "premium_tier_name", "")
        if isinstance(tier_name, str) and tier_name.lower() in TIER_LEVELS:
            return TIER_LEVELS[tier_name.lower()]
        
        # Fall back to a sensible default
        return 0
    except Exception as e:
        logger.error(f"Error getting guild tier for {guild_id}: {e}")
        return 0

async def verify_premium_for_feature(db, guild_id: Union[str, int], feature_name: str) -> bool:
    """
    Verify if a guild has access to a premium feature.
    
    This is the recommended function to use for most premium checks.
    
    Args:
        db: Database connection
        guild_id: Discord guild ID
        feature_name: Feature name to check (will be normalized)
        
    Returns:
        bool: True if the guild has access, False otherwise
    """
    try:
        # First check if premium verification is bypassed for this guild
        if await is_premium_verification_bypassed(db, guild_id):
            # Always grant access if verification is bypassed
            await log_premium_access_attempt(db, guild_id, feature_name, True)
            return True
        
        # Get the guild's tier and required tier for the feature
        guild_tier = await get_guild_tier(db, guild_id)
        required_tier = get_required_tier_for_feature(feature_name)
        
        # Check if the guild's tier is high enough
        has_access = guild_tier >= required_tier
        
        # Log the attempt for analytics
        await log_premium_access_attempt(db, guild_id, feature_name, has_access)
        
        return has_access
    except Exception as e:
        logger.error(f"Error verifying premium for feature '{feature_name}': {e}")
        return False

async def is_premium_verification_bypassed(db, guild_id: Union[str, int]) -> bool:
    """
    Check if premium verification is bypassed for this guild.
    
    Some guilds may have premium verification bypassed for testing or special cases.
    
    Args:
        db: Database connection
        guild_id: Discord guild ID
        
    Returns:
        bool: True if verification is bypassed, False otherwise
    """
    if not is_db_available(db):
        return False
    
    str_guild_id = str(guild_id)
    
    try:
        guilds_collection = db.guilds
        guild_doc = await get_document_safely(guilds_collection, {"guild_id": str_guild_id})
        
        # Check the bypass flag
        bypass = safe_get(guild_doc, "bypass_premium_verification", False)
        return bool(bypass)  # Ensure boolean result
    except Exception as e:
        logger.error(f"Error checking premium verification bypass for guild {guild_id}: {e}")
        return False

async def get_feature_access_details(db, guild_id: Union[str, int], feature_name: str) -> Dict[str, Any]:
    """
    Get detailed access information for a feature.
    
    Args:
        db: Database connection
        guild_id: Discord guild ID
        feature_name: Feature name to check
        
    Returns:
        Dict containing access details
    """
    normalized_feature = normalize_feature_name(feature_name)
    
    try:
        # Get the guild's tier
        guild_tier = await get_guild_tier(db, guild_id)
        required_tier = get_required_tier_for_feature(normalized_feature)
        
        # Determine tier names for display
        guild_tier_name = next((name for name, level in TIER_LEVELS.items() 
                                if level == guild_tier), "unknown")
        required_tier_name = next((name for name, level in TIER_LEVELS.items() 
                                  if level == required_tier), "unknown")
        
        # Check if the guild has access
        has_access = guild_tier >= required_tier
        
        return {
            "has_access": has_access,
            "guild_tier": guild_tier,
            "guild_tier_name": guild_tier_name,
            "required_tier": required_tier,
            "required_tier_name": required_tier_name,
            "feature_name": feature_name,
            "normalized_feature": normalized_feature
        }
    except Exception as e:
        logger.error(f"Error getting feature access details: {e}")
        return {
            "has_access": False,
            "error": str(e),
            "feature_name": feature_name
        }

async def log_premium_access_attempt(
    db, 
    guild_id: Union[str, int], 
    feature_name: str,
    granted: bool,
    user_id: Optional[Union[str, int]] = None
) -> None:
    """
    Log a premium access attempt for analytics and debugging.
    
    Args:
        db: Database connection
        guild_id: Discord guild ID
        feature_name: Feature name that was checked
        granted: Whether access was granted
        user_id: Optional Discord user ID who attempted to use the feature
    """
    if not is_db_available(db):
        return
    
    try:
        # Convert IDs to strings for consistency
        str_guild_id = str(guild_id)
        str_user_id = str(user_id) if user_id is not None else None
        
        # Create the log entry
        log_entry = {
            "timestamp": {"$currentDate": {"$type": "date"}},
            "guild_id": str_guild_id,
            "feature_name": normalize_feature_name(feature_name),
            "granted": granted
        }
        
        # Add user ID if provided
        if str_user_id:
            log_entry["user_id"] = str_user_id
        
        # Insert into the access logs collection
        access_logs = db.premium_access_logs
        await access_logs.insert_one(log_entry)
    except Exception as e:
        # Just log the error and continue - this is a non-critical operation
        logger.error(f"Failed to log premium access attempt: {e}")

def premium_feature_required(feature_name: str, min_tier: Optional[int] = None):
    """
    Decorator to require premium access for a command.
    
    Args:
        feature_name: Name of the required feature
        min_tier: Minimum tier required (overrides feature mapping if provided)
        
    Returns:
        Decorator function
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(self, ctx, *args, **kwargs):
            # Get the database from the cog or bot
            db = getattr(self, 'db', None)
            if db is None and hasattr(self, 'bot'):
                db = getattr(self.bot, 'db', None)
            
            if not db:
                logger.error("Database not available for premium verification")
                # Check if ctx is an Interaction or Context
                if hasattr(ctx, 'response') and hasattr(ctx.response, 'send_message'):
                    await ctx.response.send_message("⚠️ Server error: Unable to verify premium status.", ephemeral=True)
                elif hasattr(ctx, 'send'):
                    await ctx.send("⚠️ Server error: Unable to verify premium status.")
                return
            
            # Get the guild ID from the context
            guild_id = None
            if hasattr(ctx, 'guild') and ctx.guild:
                guild_id = ctx.guild.id
            elif hasattr(ctx, 'guild_id') and ctx.guild_id:
                guild_id = ctx.guild_id
            
            if not guild_id:
                if hasattr(ctx, 'response') and hasattr(ctx.response, 'send_message'):
                    await ctx.response.send_message("⚠️ This command can only be used in a server.", ephemeral=True)
                elif hasattr(ctx, 'send'):
                    await ctx.send("⚠️ This command can only be used in a server.")
                return
            
            # If min_tier was provided explicitly, use it instead of feature mapping
            required_tier = min_tier if min_tier is not None else get_required_tier_for_feature(feature_name)
            
            # Check if user has required tier by getting guild tier and comparing
            guild_tier = await get_guild_tier(db, guild_id)
            has_premium = guild_tier >= required_tier if required_tier is not None else False
            
            # Also check feature-based access if no explicit min_tier was provided
            if not has_premium and min_tier is None:
                has_premium = await verify_premium_for_feature(db, guild_id, feature_name)
            
            if not has_premium:
                # Get the tier name for better messaging
                tier_name = next((name for name, level in TIER_LEVELS.items() 
                                 if level == required_tier), "premium")
                
                # Handle both Interaction and Context objects
                if hasattr(ctx, 'response') and hasattr(ctx.response, 'send_message'):
                    await ctx.response.send_message(
                        f"⚠️ This feature requires the `{tier_name.title()}` tier or higher. "
                        f"Use `/premium info` to learn more about upgrading.",
                        ephemeral=True
                    )
                elif hasattr(ctx, 'send'):
                    await ctx.send(
                        f"⚠️ This feature requires the `{tier_name.title()}` tier or higher. "
                        f"Use `/premium info` to learn more about upgrading."
                    )
                return
            
            # If has premium, call the original function
            return await func(self, ctx, *args, **kwargs)
        
        # Store the feature name and min_tier in the wrapper function's attributes
        setattr(wrapper, "__premium_feature__", feature_name)
        if min_tier is not None:
            setattr(wrapper, "__premium_min_tier__", min_tier)
        return wrapper
    
    return decorator