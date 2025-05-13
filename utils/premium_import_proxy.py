"""
Premium System Import Proxy

This module provides a clean importable proxy interface for premium system functions
without using monkey patching. This allows old code to import premium functions
from a stable location while the implementation may change.

Usage:
    from utils.premium_import_proxy import verify_premium_for_feature, get_premium_tier
"""

import logging
import functools
from typing import Any, Optional, Union, Tuple, Dict, List, Callable

logger = logging.getLogger(__name__)

# Import the actual implementation
from utils.premium_verification import (
    verify_premium_for_feature as _verify_premium_for_feature,
    get_guild_tier as _get_guild_tier,
    premium_feature_required as _premium_feature_required
)

# Feature name mapping for compatibility
FEATURE_NAME_MAP = {
    "stats": "basic_stats",
    "stats_server": "basic_stats",
    "stats_player": "basic_stats",
    "stats_weapon": "basic_stats",
    "stats_leaderboard": "leaderboards",
    "stats_weapon_categories": "basic_stats",
    "server": "basic_stats",
    "player": "basic_stats",
    "weapon": "basic_stats",
    "weapon_categories": "basic_stats",
    "leaderboard": "leaderboards",
    "leaderboards": "leaderboards",
    "rivalry": "rivalries",
    "bounty": "bounties",
    "faction": "factions",
    "event": "events",
    "premium": "basic_stats",
}

# Provide a stable interface for old code
async def verify_premium_for_feature(db, guild_id, guild_model=None, feature_name="premium", error_message=True):
    """
    Verify premium feature access with backward compatibility with old signatures.
    
    Args:
        db: Database connection
        guild_id: Guild ID
        guild_model: Guild model (unused, kept for compatibility)
        feature_name: Name of the feature to check
        error_message: Whether to include error message in response
        
    Returns:
        If error_message is True, returns (has_access, error_msg)
        If error_message is False, returns has_access
    """
    # Map old feature names to new ones
    mapped_feature = FEATURE_NAME_MAP.get(feature_name, feature_name)
    
    # Log the check for debugging
    logger.debug(f"Checking premium feature: {feature_name} → {mapped_feature}")
    
    # Check premium access
    has_access = await _verify_premium_for_feature(db, guild_id, mapped_feature)
    
    # Format response based on parameter
    if error_message:
        # Generate error message
        if not has_access:
            from utils.premium_verification import (
                get_required_tier_for_feature, 
                get_guild_tier,
                TIER_LEVELS
            )
            required_tier = get_required_tier_for_feature(mapped_feature)
            guild_tier = await get_guild_tier(db, guild_id)
            
            # Get names for these tier levels
            required_tier_name = next((name for name, level in TIER_LEVELS.items() 
                                     if level == required_tier), "premium")
            guild_tier_name = next((name for name, level in TIER_LEVELS.items() 
                                  if level == guild_tier), "free")
            
            error_msg = (
                f"This feature requires the **{required_tier_name.title()}** tier or higher.\n"
                f"Your server currently has the **{guild_tier_name.title()}** tier.\n"
                f"Use `/premium info` for more information."
            )
            return False, error_msg
        return True, None
    else:
        return has_access

async def get_premium_tier(db, guild_id, guild_model=None):
    """
    Get guild premium tier with backward compatibility.
    
    Args:
        db: Database connection
        guild_id: Guild ID
        guild_model: Guild model (unused, kept for compatibility)
        
    Returns:
        int: Premium tier (0-4)
    """
    return await _get_guild_tier(db, guild_id)

def premium_required(tier):
    """
    Decorator requiring premium tier with backward compatibility.
    
    Args:
        tier: Required tier level
        
    Returns:
        Decorator function
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(self, ctx, *args, **kwargs):
            # Get database from either the cog or bot
            db = getattr(self, 'db', None)
            if db is None and hasattr(self, 'bot'):
                db = getattr(self.bot, 'db', None)
                
            if not db:
                await ctx.send("⚠️ Unable to verify premium status - database connection error.")
                return
                
            # Get guild ID
            guild_id = ctx.guild.id if hasattr(ctx, 'guild') and ctx.guild else None
            if not guild_id:
                await ctx.send("⚠️ This command can only be used in a server.")
                return
                
            # Check if guild has required tier
            guild_tier = await get_premium_tier(db, guild_id)
            if guild_tier < tier:
                # Get tier name for better messaging
                from utils.premium_verification import TIER_LEVELS
                required_tier_name = next((name for name, level in TIER_LEVELS.items() 
                                         if level == tier), "premium")
                guild_tier_name = next((name for name, level in TIER_LEVELS.items() 
                                      if level == guild_tier), "free")
                
                await ctx.send(
                    f"⚠️ This command requires the **{required_tier_name.title()}** tier or higher.\n"
                    f"Your server currently has the **{guild_tier_name.title()}** tier.\n"
                    f"Use `/premium info` for more information."
                )
                return
                
            # If tier is sufficient, call the original function
            return await func(self, ctx, *args, **kwargs)
        return wrapper
    return decorator

def get_tier_requirement(feature_name):
    """
    Get required tier for a feature with backward compatibility.
    
    Args:
        feature_name: Name of the feature
        
    Returns:
        int: Required tier (0-4)
    """
    # Map old feature names to new ones
    mapped_feature = FEATURE_NAME_MAP.get(feature_name, feature_name)
    
    # Get required tier
    from utils.premium_verification import get_required_tier_for_feature
    return get_required_tier_for_feature(mapped_feature)

# Aliases for compatibility with different naming conventions
check_premium = verify_premium_for_feature
ensure_premium_tier = premium_required
get_guild_premium_tier = get_premium_tier
get_feature_tier_requirement = get_tier_requirement