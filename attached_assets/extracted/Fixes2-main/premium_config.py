"""
Premium feature configuration settings
"""

from typing import Dict, List, Any, Optional

# Premium tier definitions
PREMIUM_TIERS = {
    0: {
        "name": "Free",
        "max_servers": 1,
        "price_gbp": 0,
        "features": ["basic_killfeed"]
    },
    1: {
        "name": "Basic",
        "max_servers": 2,
        "price_gbp": 5,
        "features": ["basic_killfeed", "basic_stats", "leaderboards"]
    },
    2: {
        "name": "Pro",
        "max_servers": 5,
        "price_gbp": 10,
        "features": ["killfeed", "basic_stats", "leaderboards", "rivalries", "bounties", 
                    "player_links", "economy", "advanced_analytics"]
    },
    3: {
        "name": "Enterprise",
        "max_servers": 10,
        "price_gbp": 20,
        "features": ["killfeed", "basic_stats", "leaderboards", "rivalries", "bounties", 
                    "player_links", "economy", "advanced_analytics", "factions", "events"]
    }
}

# Tier aliases (string to int)
TIER_ALIASES = {
    "free": 0,
    "basic": 1,
    "pro": 2,
    "enterprise": 3
}

def get_tier_name(tier_id: int) -> str:
    """Get the tier name from the tier ID
    
    Args:
        tier_id: Numeric tier ID
        
    Returns:
        str: Tier name or "Unknown" if tier not found
    """
    tier_data = PREMIUM_TIERS.get(tier_id)
    if tier_data:
        return tier_data["name"]
    return "Unknown"

def get_tier_features(tier_id: int) -> List[str]:
    """Get the list of features available for a tier
    
    Args:
        tier_id: Numeric tier ID
        
    Returns:
        List[str]: List of feature names or empty list if tier not found
    """
    tier_data = PREMIUM_TIERS.get(tier_id)
    if tier_data:
        return tier_data["features"]
    return []

def get_feature_tier(feature_name: str) -> Optional[int]:
    """Get the minimum tier required for a feature
    
    Args:
        feature_name: Name of the feature
        
    Returns:
        Optional[int]: Minimum tier ID required or None if feature not found
    """
    for tier_id, tier_data in PREMIUM_TIERS.items():
        if feature_name in tier_data["features"]:
            return tier_id
    return None

def get_max_servers(tier_id: int) -> int:
    """Get the maximum number of servers allowed for a tier
    
    Args:
        tier_id: Numeric tier ID
        
    Returns:
        int: Maximum number of servers or 1 if tier not found
    """
    tier_data = PREMIUM_TIERS.get(tier_id)
    if tier_data:
        return tier_data["max_servers"]
    return 1