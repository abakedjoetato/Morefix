"""
# module: premium_utils
Premium Feature Utilities

This module provides a standardized interface for premium feature validation.
It is the recommended interface for all new code that needs to validate premium features.
"""

import logging
import re
import asyncio
from typing import Dict, Any, List, Optional, Tuple, Union, TypeVar, cast

logger = logging.getLogger(__name__)

# Import core functionality from premium_feature_access
from utils.premium_feature_access import (
    get_feature_tier_requirement,
    verify_premium_tier,
    verify_premium_feature,
    check_feature_access,
    get_guild_premium_tier,
    check_tier_access,
    PREMIUM_FEATURES
)

# Feature name mapping for UI display
FEATURE_NAME_MAPPING = {
    "stats": "Player Statistics",
    "basic_commands": "Basic Commands",
    "help": "Help Commands",
    "info": "Server Information",
    "setup": "Server Setup",
    "player_search": "Player Search",
    "basic_settings": "Basic Settings",
    "leaderboard": "Leaderboards",
    "scheduled_updates": "Scheduled Updates",
    "weapon_stats": "Weapon Statistics",
    "playtime_tracking": "Playtime Tracking",
    "player_links": "Player Links",
    "killfeed": "Kill Feed",
    "multi_server": "Multi-Server Support",
    "advanced_stats": "Advanced Statistics",
    "rivalries": "Rivalries System",
    "embeds": "Discord Embeds",
    "data_export": "Data Export",
    "custom_commands": "Custom Commands",
    "admin_tools": "Admin Tools",
    "bot_logs": "Bot Logs",
    "premium_embeds": "Premium Embeds",
    "custom_embeds": "Custom Embeds",
    "events": "Events System",
    "factions": "Factions System",
    "bounties": "Bounties System",
    "economy": "Economy System",
    "custom_features": "Custom Features",
    "dedicated_hosting": "Dedicated Hosting",
    "custom_leaderboards": "Custom Leaderboards",
    "priority_support": "Priority Support",
    "white_label": "White Label Service",
    "tier_0": "Free Tier Access",
    "tier_1": "Basic Tier Access",
    "tier_2": "Standard Tier Access",
    "tier_3": "Premium Tier Access",
    "tier_4": "Enterprise Tier Access",
}

# Feature tier requirements
FEATURE_TIERS = {
    # Basic features (Tier 0 - Free)
    "killfeed": 0,
    "player_links": 0,
    "basic_leaderboard": 0,
    "basic_stats": 0,
    "bot_logs": 0,
    
    # Basic premium features (Tier 1)
    "stats": 1,
    "advanced_stats": 1,
    "leaderboard": 1,
    "extended_leaderboard": 1,
    "custom_embeds": 1,
    "premium_embeds": 1,
    
    # Standard premium features (Tier 2)
    "events": 2,
    "factions": 2,
    "economy": 2,
    "multi_server": 2,
    "advanced_analytics": 2,
    "scheduled_reports": 2,
    "custom_leaderboards": 2,
    
    # Pro premium features (Tier 3)
    "rivalries": 3,
    "bounties": 3,
    "white_label": 3,
    "priority_support": 3,
    
    # Always use these tier names for explicit tier checks
    "tier_0": 0,
    "tier_1": 1,
    "tier_2": 2,
    "tier_3": 3,
    "tier_4": 4,
}

def normalize_feature_name(feature_name: str) -> str:
    """
    Normalize a feature name for consistent lookup.
    
    Args:
        feature_name: Raw feature name
        
    Returns:
        Normalized feature name
    """
    # Convert to lowercase and remove spaces/underscores
    normalized = feature_name.lower().strip()
    
    # Replace spaces with underscores for consistency
    normalized = normalized.replace(" ", "_")
    
    # Handle common variations
    if normalized in ["player_stats", "player_statistics", "playerstats", "statistics", "stats", "player_stats"]:
        normalized = "stats"
    elif normalized in ["leaderboards", "top_players", "rankings"]:
        normalized = "leaderboard"
    elif normalized in ["advanced_analytics", "advanced_statistics"]:
        normalized = "advanced_stats"
    elif normalized in ["premium_embed", "premium_embeds"]:
        normalized = "premium_embeds"
    elif normalized in ["custom_embed", "custom_embeds"]:
        normalized = "custom_embeds"
    elif normalized in ["log", "logs"]:
        normalized = "bot_logs"
    elif normalized in ["multi", "multi_servers"]:
        normalized = "multi_server"
    
    # Special case for tier checks
    tier_match = re.match(r"tier[_\s]*(\d+)", normalized)
    if tier_match is not None:
        tier_num = tier_match.group(1)
        normalized = f"tier_{tier_num}"
    
    logger.debug(f"Normalized feature name '{feature_name}' to '{normalized}'")
    
    return normalized

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
        # Normalize feature name for consistent lookup
        normalized_feature = normalize_feature_name(feature_name)
        
        # Get the feature's required tier
        required_tier = FEATURE_TIERS.get(normalized_feature)
        
        # If feature not found in tier map, default to tier 1
        if required_tier is None:
            logger.warning(f"Feature '{normalized_feature}' not found in premium tier map, defaulting to tier 1")
            required_tier = 1
            
        # Check if the guild has the required tier
        return await has_premium_tier(db, guild_id, required_tier)
    except Exception as e:
        logger.error(f"Error verifying premium feature access for guild {guild_id}, feature {feature_name}: {e}")
        return False

def standardize_premium_check(
    db, 
    guild_id: Union[str, int], 
    feature_name: str, 
    error_message: bool = False
) -> Union[bool, Tuple[bool, Optional[str]]]:
    """
    Standardized premium check with optional error message.
    
    Args:
        db: Database connection
        guild_id: Discord guild ID
        feature_name: Feature name to check (will be normalized)
        error_message: Whether to return an error message for UI display
        
    Returns:
        If error_message is False: bool indicating access
        If error_message is True: Tuple of (bool access, Optional[str] error_message)
    """
    # Normalize feature name for consistent lookup
    normalized_feature = normalize_feature_name(feature_name)
    
    # Get the required tier for this feature from FEATURE_TIERS dictionary
    # Default to tier 1 if not found
    required_tier = 1
    # Use get() method which is safer than 'in' operator for different types
    required_tier = FEATURE_TIERS.get(normalized_feature, 1)
    
    # Handle special tier_N feature names directly
    tier_match = re.match(r"tier_(\d+)", normalized_feature)
    if tier_match is not None:
        required_tier = int(tier_match.group(1))
    
    # For async compatibility, we'll do the tier check directly here
    # instead of calling potentially async functions
    if error_message:
        # Return a tuple with error message
        return check_feature_access_sync(db, str(guild_id), normalized_feature, required_tier)
    else:
        # Just check if they have access
        has_access, _ = check_feature_access_sync(db, str(guild_id), normalized_feature, required_tier)
        return has_access
        
# Synchronous version of feature access checker with improved error handling
def check_feature_access_sync(
    db, guild_id: str, feature_name: str, required_tier: int = 1
) -> Tuple[bool, Optional[str]]:
    """Synchronous version of feature access checker for test compatibility"""
    try:
        # Import locally to avoid circular imports
        from utils.safe_database import is_db_available
    
        guild_tier = 0  # Default to free tier
        guild_doc = None
        
        # First check if database exists and is available
        if db is None:
            return False, "Database connection not available"
            
        # Check if database appears to be valid
        if not hasattr(db, "guilds"):
            return False, "Invalid database connection"
        
        # Handle both real MongoDB and mock databases with better error handling
        try:
            if hasattr(db.guilds, "find_one"):
                # Real MongoDB database - would be async in real application
                if hasattr(db.guilds.find_one, "__await__"):
                    # This is a real async method, but we're in a sync context
                    # Don't attempt to call it, just use a default placeholder
                    guild_doc = {"premium_tier": 0}
                else:
                    # This is a sync method, like in our MockDatabase
                    try:
                        # Use str(guild_id) to ensure proper type handling
                        guild_doc = db.guilds.find_one({"guild_id": str(guild_id)})
                    except Exception as query_error:
                        return False, f"Database query error: {query_error}"
            else:
                # MockDatabase for tests where guilds is a direct dictionary
                try:
                    guild_doc = db.guilds.get(str(guild_id))
                except AttributeError:
                    # No 'get' method, try direct access
                    try:
                        guild_doc = db.guilds[str(guild_id)]
                    except (KeyError, TypeError):
                        guild_doc = None
        except Exception as db_error:
            return False, f"Database access error: {db_error}"
        
        # Safely check if guild document exists and process with proper dictionary access
        if guild_doc:
            # Use .get() with default for safe dictionary access
            guild_tier = guild_doc.get("premium_tier", 0)
            
            # Validate tier is actually a number (not dict or other type)
            if not isinstance(guild_tier, int):
                try:
                    guild_tier = int(guild_tier)
                except (ValueError, TypeError):
                    guild_tier = 0  # Default to free tier if conversion fails
            
            # Check for feature-specific overrides with safe dictionary access
            premium_features = guild_doc.get("premium_features")
            
            # Verify we have a valid dictionary object
            if isinstance(premium_features, dict):
                # Use get() for safer access rather than 'in' operator
                override = premium_features.get(feature_name)
                
                # Explicit boolean checks for safer comparison
                if override is True:
                    # Feature explicitly enabled
                    return True, None
                elif override is False:
                    # Feature explicitly disabled
                    return False, f"Access to '{feature_name}' has been specifically disabled."
    
        # Normal tier-based check with explicit type checking
        if isinstance(guild_tier, int) and isinstance(required_tier, int):
            has_access = guild_tier >= required_tier
            
            if has_access:
                return True, None
            else:
                return False, f"This feature requires premium tier {required_tier} or higher. Current tier: {guild_tier}"
        else:
            # Handle type mismatch by converting to string for error message
            return False, f"Invalid tier configuration (required: {required_tier}, guild: {guild_tier})"
    
    except Exception as e:
        # Catch any other errors and return a safe error message
        return False, f"Error checking premium access: {str(e)}"

async def get_guild_tier(db, guild_id: Union[str, int]) -> int:
    """
    Get a guild's premium tier.
    
    Args:
        db: Database connection
        guild_id: Discord guild ID
        
    Returns:
        int: Guild's premium tier (0-4)
    """
    try:
        # Import locally to avoid circular imports
        from utils.safe_database import is_db_available, safe_find_one
        
        # Check if database is available
        if not is_db_available(db):
            logger.warning(f"Database not available when checking tier for guild {guild_id}")
            return 0  # Default to free tier for safety
        
        # Ensure guild_id is a string for consistent lookup
        guild_id_str = str(guild_id)
        
        # Use safe_find_one for better error handling
        guild_doc = await safe_find_one(db, "guilds", {"guild_id": guild_id_str})
        
        # Check if we got a valid document and it has premium_tier field
        if guild_doc and guild_doc.has("premium_tier"):
            tier = guild_doc.get("premium_tier", 0)
            
            # Handle the tier value carefully to avoid type errors
            # First check if we have an integer already
            if isinstance(tier, int):
                # We already have a valid integer
                pass
            # If we have None, default to 0 (free tier)
            elif tier is None:
                logger.warning(f"Premium tier is None for guild {guild_id}")
                tier = 0
            # Try to convert string, float, or bool values to integer
            elif isinstance(tier, (str, float, bool)):
                try:
                    # Convert to string first, then to int for safety
                    tier = int(str(tier))
                except (ValueError, TypeError):
                    logger.warning(f"Invalid premium tier format for guild {guild_id}: {tier}")
                    tier = 0  # Default to free tier if conversion fails
            # For any other type, log warning and default to free tier
            else:
                logger.warning(f"Unexpected tier type for guild {guild_id}: {type(tier)}")
                tier = 0
            
            # Ensure tier is in valid range (0-4)
            if 0 <= tier <= 4:
                return tier
            else:
                logger.warning(f"Guild {guild_id} has out-of-range tier: {tier}")
                return 0  # Default to free tier for out-of-range values
        
        # No guild document or no premium_tier field
        return 0  # Default to free tier
        
    except Exception as e:
        logger.error(f"Error retrieving premium tier for guild {guild_id}: {e}")
        return 0  # Default to free tier on error

# Alias for compatibility with verification script
get_premium_tier = get_guild_tier

# Add function aliases for compatibility with test scripts
async def has_premium_tier(db, guild_id: Union[str, int], tier: int) -> bool:
    """Check if a guild has a specific premium tier.
    
    Args:
        db: Database connection
        guild_id: Guild ID
        tier: Tier to check for
        
    Returns:
        True if guild has the specified tier or higher, False otherwise
    """
    try:
        # Get the guild's tier with error handling
        guild_tier = await get_guild_tier(db, guild_id)
        
        # Ensure both tier values are integers for safe comparison
        if isinstance(guild_tier, int) and isinstance(tier, int):
            return guild_tier >= tier
        else:
            # Try to convert to integers if possible
            try:
                guild_tier_int = int(guild_tier) if guild_tier is not None else 0
                tier_int = int(tier) if tier is not None else 1
                return guild_tier_int >= tier_int
            except (ValueError, TypeError):
                logger.error(f"Invalid tier comparison: guild_tier={guild_tier}, required_tier={tier}")
                return False
    except Exception as e:
        logger.error(f"Error checking premium tier for guild {guild_id}: {e}")
        return False

async def has_premium_feature(db, guild_id: Union[str, int], feature_name: str) -> bool:
    """Check if a guild has access to a premium feature.
    
    Args:
        db: Database connection
        guild_id: Guild ID
        feature_name: Feature to check access for
        
    Returns:
        True if guild has access to the feature, False otherwise
    """
    return await verify_premium_for_feature(db, guild_id, feature_name)

async def check_guild_feature_access(db, guild_id: Union[str, int], feature_names: List[str]) -> Dict[str, bool]:
    """
    Check multiple features at once for a guild.
    
    Args:
        db: Database connection
        guild_id: Discord guild ID
        feature_names: List of feature names to check
        
    Returns:
        Dict mapping feature names to access status
    """
    try:
        # Convert guild_id to string for consistent lookup
        guild_id_str = str(guild_id)
        
        # Get guild tier once for efficiency
        guild_tier = await get_guild_tier(db, guild_id_str)
        
        result = {}
        # Check each feature using the cached guild tier
        for feature in feature_names:
            try:
                # Normalize feature name
                normalized_feature = normalize_feature_name(feature)
                
                # Get required tier for this feature
                required_tier = FEATURE_TIERS.get(normalized_feature)
                
                # Default to tier 1 if feature not found in tier map
                if required_tier is None:
                    logger.warning(f"Feature '{normalized_feature}' not found in premium tier map, defaulting to tier 1")
                    required_tier = 1
                
                # Apply the same safe tier handling as in get_guild_tier
                # Handle guild_tier
                guild_tier_int = 0  # Default to free tier
                if isinstance(guild_tier, int):
                    guild_tier_int = guild_tier
                elif guild_tier is None:
                    guild_tier_int = 0
                elif isinstance(guild_tier, (str, float, bool)):
                    try:
                        guild_tier_int = int(str(guild_tier))
                    except (ValueError, TypeError):
                        logger.error(f"Invalid guild tier format for feature {feature}: {guild_tier}")
                
                # Handle required_tier
                required_tier_int = 1  # Default to basic tier requirement
                if isinstance(required_tier, int):
                    required_tier_int = required_tier
                elif required_tier is None:
                    required_tier_int = 1
                elif isinstance(required_tier, (str, float, bool)):
                    try:
                        required_tier_int = int(str(required_tier))
                    except (ValueError, TypeError):
                        logger.error(f"Invalid required tier format for feature {feature}: {required_tier}")
                
                # Safe integer comparison
                result[feature] = guild_tier_int >= required_tier_int
            except Exception as e:
                # Individual feature check failed, mark as unavailable
                logger.error(f"Error checking feature {feature} for guild {guild_id}: {e}")
                result[feature] = False
        
        return result
    except Exception as e:
        # Complete failure, return all features as unavailable
        logger.error(f"Error checking features for guild {guild_id}: {e}")
        return {feature: False for feature in feature_names}

# Legacy function name for compatibility with premium_trace.py and premium_trace_rewrite.py
async def check_premium_feature_access(db, guild_id: Union[str, int], feature_name: str) -> bool:
    """Compatibility function for backward compatibility with premium_trace scripts.
    Just calls verify_premium_for_feature.
    
    Args:
        db: Database connection
        guild_id: Guild ID
        feature_name: Feature to check access for
        
    Returns:
        True if guild has access to the feature, False otherwise
    """
    try:
        return await verify_premium_for_feature(db, guild_id, feature_name)
    except Exception as e:
        logger.error(f"Error in check_premium_feature_access for guild {guild_id}, feature {feature_name}: {e}")
        return False

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
    try:
        # Skip logging for common features to avoid log spam
        common_features = ["stats", "help", "info", "basic_commands"]
        normalized = normalize_feature_name(feature_name)
        if normalized in common_features:
            return
        
        # Log to console for debugging
        status = "granted" if granted else "denied"
        logger.debug(f"Premium access {status} for guild {guild_id}, feature '{feature_name}'")
        
        # Attempt to log to database if premium_access_logs collection exists
        if db is not None:
            try:
                # Check if collection exists first to avoid errors
                collections = await db.list_collection_names()
                if "premium_access_logs" in collections:
                    # Get current time safely
                    import datetime
                    current_time = datetime.datetime.utcnow()
                    
                    # Format the log entry
                    log_entry = {
                        "guild_id": str(guild_id),
                        "feature": feature_name,
                        "normalized_feature": normalized,
                        "access_granted": granted,
                        "timestamp": current_time,
                    }
                    
                    # Add user_id if provided
                    if user_id is not None:
                        log_entry["user_id"] = str(user_id)
                    
                    # Insert the log
                    await db.premium_access_logs.insert_one(log_entry)
            except Exception as inner_e:
                logger.warning(f"Failed to log to database: {inner_e}")
    except Exception as e:
        # Don't let logging failures affect the running application
        logger.error(f"Failed to log premium access attempt: {e}")