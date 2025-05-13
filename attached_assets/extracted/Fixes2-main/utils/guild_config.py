"""
Guild Configuration for Tower of Temptation PvP Statistics Bot

This module provides utilities for managing guild-specific configurations:
1. SFTP connection settings
2. Resource limits based on premium tier
3. Rate limiting
4. Guild preference management
5. Multi-guild isolation

Ensures proper resource allocation and isolation between guilds.
"""
import os
import logging
from typing import Dict, Any, Optional, List, Set, Tuple, Union
import asyncio
import time
import random
from datetime import datetime, timedelta

# Configure module-specific logger
logger = logging.getLogger(__name__)

# Default resource limits by premium tier
DEFAULT_RESOURCE_LIMITS = {
    # Free tier
    0: {
        "max_sftp_connections": 2,
        "max_sftp_operations_per_minute": 5, 
        "max_file_size_mb": 5,
        "connection_idle_timeout": 120,  # 2 minutes
        "max_search_depth": 2,
        "max_retry_count": 2
    },
    # Basic tier
    1: {
        "max_sftp_connections": 5,
        "max_sftp_operations_per_minute": 15,
        "max_file_size_mb": 15,
        "connection_idle_timeout": 300,  # 5 minutes
        "max_search_depth": 3,
        "max_retry_count": 3
    },
    # Pro tier
    2: {
        "max_sftp_connections": 10,
        "max_sftp_operations_per_minute": 30,
        "max_file_size_mb": 25,
        "connection_idle_timeout": 600,  # 10 minutes
        "max_search_depth": 5,
        "max_retry_count": 4
    },
    # Enterprise tier
    3: {
        "max_sftp_connections": 20,
        "max_sftp_operations_per_minute": 60,
        "max_file_size_mb": 50,
        "connection_idle_timeout": 900,  # 15 minutes
        "max_search_depth": 10,
        "max_retry_count": 5
    }
}

# Cache for guild configurations to reduce database queries
GUILD_CONFIG_CACHE = {}
GUILD_CONFIG_TTL = 300  # Cache TTL in seconds

# Rate limit tracking
RATE_LIMITS = {}
RATE_LIMIT_LOCK = asyncio.Lock()

class GuildConfig:
    """Guild configuration manager with resource allocation"""
    
    def __init__(self, bot):
        """Initialize guild configuration manager
        
        Args:
            bot: Bot instance with database access
        """
        self.bot = bot
        self.cache_ttl = int(os.environ.get("GUILD_CONFIG_CACHE_TTL", GUILD_CONFIG_TTL))
        
        # Ensure premium tiers are initialized
        self._override_resource_limits = {}
        self._initialize_resource_limits()
        
    def _initialize_resource_limits(self):
        """Initialize resource limits from environment variables"""
        try:
            # Check for environment variable overrides
            for tier in range(4):  # 0-3 tiers
                tier_prefix = f"TIER_{tier}_"
                tier_overrides = {}
                
                # Check for each resource limit
                for limit_name in DEFAULT_RESOURCE_LIMITS[0].keys():
                    env_name = f"{tier_prefix}{limit_name.upper()}"
                    if env_name in os.environ:
                        try:
                            tier_overrides[limit_name] = int(os.environ[env_name])
                        except ValueError:
                            logger.warning(f"Invalid value for {env_name}: {os.environ[env_name]}")
                
                # If any overrides were found, store them
                if tier_overrides:
                    self._override_resource_limits[tier] = tier_overrides
                    logger.info(f"Resource limit overrides for tier {tier}: {tier_overrides}")
                    
        except Exception as e:
            logger.error(f"Error initializing resource limits: {e}")
    
    async def get_guild_config(self, guild_id: str) -> Dict[str, Any]:
        """Get configuration for a specific guild
        
        Args:
            guild_id: Discord guild ID
            
        Returns:
            Guild configuration dictionary
        """
        # Check cache first
        cache_key = f"guild_config:{guild_id}"
        if cache_key in GUILD_CONFIG_CACHE:
            cache_entry = GUILD_CONFIG_CACHE[cache_key]
            if (datetime.now() - cache_entry['timestamp']).total_seconds() < self.cache_ttl:
                return cache_entry['config']
        
        # Get from database
        try:
            db = self.bot.db()
            guild_doc = await db.guilds.find_one({'guild_id': str(guild_id)})
            
            if not guild_doc:
                # Create default config
                guild_doc = {
                    'guild_id': str(guild_id),
                    'premium_tier': 0,
                    'settings': {},
                    'servers': {}
                }
            
            # Check for premium tier
            premium_tier = guild_doc.get('premium_tier', 0)
            
            # Also check premium collection
            premium_doc = await db.premium.find_one({'guild_id': str(guild_id)})
            if premium_doc and premium_doc.get('active', False):
                # Get the highest tier from both sources
                premium_tier = max(premium_tier, premium_doc.get('tier', 0))
            
            # Add premium tier to config
            guild_doc['premium_tier'] = premium_tier
            
            # Ensure settings dictionary exists
            if 'settings' not in guild_doc:
                guild_doc['settings'] = {}
                
            # Ensure servers dictionary exists
            if 'servers' not in guild_doc:
                guild_doc['servers'] = {}
            
            # Cache the result
            GUILD_CONFIG_CACHE[cache_key] = {
                'timestamp': datetime.now(),
                'config': guild_doc
            }
            
            return guild_doc
            
        except Exception as e:
            logger.error(f"Error getting guild config for {guild_id}: {e}")
            
            # Return default config
            return {
                'guild_id': str(guild_id),
                'premium_tier': 0,
                'settings': {},
                'servers': {}
            }
    
    async def get_guild_premium_tier(self, guild_id: str) -> int:
        """Get premium tier for a guild
        
        Args:
            guild_id: Discord guild ID
            
        Returns:
            Premium tier (0-3, where 0 is free tier)
        """
        guild_config = await self.get_guild_config(guild_id)
        return guild_config.get('premium_tier', 0)
    
    async def get_resource_limits(self, guild_id: str) -> Dict[str, Any]:
        """Get resource limits for a guild based on premium tier
        
        Args:
            guild_id: Discord guild ID
            
        Returns:
            Dictionary of resource limits
        """
        # Get premium tier
        premium_tier = await self.get_guild_premium_tier(guild_id)
        
        # Get base limits for this tier
        base_limits = DEFAULT_RESOURCE_LIMITS.get(premium_tier, DEFAULT_RESOURCE_LIMITS[0])
        
        # Apply any overrides
        if premium_tier in self._override_resource_limits:
            overrides = self._override_resource_limits[premium_tier]
            return {**base_limits, **overrides}
            
        return base_limits
    
    async def check_rate_limit(self, guild_id: str, operation: str) -> Tuple[bool, Optional[float]]:
        """Check if operation is rate limited for this guild
        
        Args:
            guild_id: Discord guild ID
            operation: Operation type (e.g., 'sftp', 'database')
            
        Returns:
            Tuple of (allowed, retry_after_seconds)
        """
        # Get resource limits
        limits = await self.get_resource_limits(guild_id)
        
        # Determine rate limit based on operation
        if operation == 'sftp':
            max_operations = limits.get('max_sftp_operations_per_minute', 5)
        else:
            max_operations = 10  # Default for other operations
            
        # Get current window (1-minute rolling window)
        now = time.time()
        window_start = now - 60
        
        async with RATE_LIMIT_LOCK:
            # Initialize rate limit tracking if needed
            rate_limit_key = f"{guild_id}:{operation}"
            if rate_limit_key not in RATE_LIMITS:
                RATE_LIMITS[rate_limit_key] = []
                
            # Clean up old operations outside window
            RATE_LIMITS[rate_limit_key] = [t for t in RATE_LIMITS[rate_limit_key] if t >= window_start]
            
            # Check if limit is reached
            operations_count = len(RATE_LIMITS[rate_limit_key])
            
            if operations_count >= max_operations:
                # Rate limit reached, calculate retry-after
                oldest_timestamp = RATE_LIMITS[rate_limit_key][0]
                retry_after = oldest_timestamp + 60 - now
                return False, max(0.1, retry_after)
                
            # Not rate limited, add timestamp
            RATE_LIMITS[rate_limit_key].append(now)
            return True, None
    
    async def get_guild_sftp_configs(self, guild_id: str) -> List[Dict[str, Any]]:
        """Get all SFTP configurations for a guild
        
        Args:
            guild_id: Discord guild ID
            
        Returns:
            List of SFTP configurations
        """
        guild_config = await self.get_guild_config(guild_id)
        sftp_configs = []
        
        # Check servers in guild config
        for server_id, server in guild_config.get('servers', {}).items():
            # Check if SFTP is configured
            if ('hostname' in server or 'sftp_host' in server) and ('username' in server or 'sftp_username' in server):
                # Add server_id to the config
                server['server_id'] = server_id
                server['guild_id'] = str(guild_id)
                sftp_configs.append(server)
        
        try:
            # Check databases for additional configurations
            db = self.bot.db()
            
            # Check main servers collection
            query = {'guild_id': str(guild_id)}
            async for server in db.servers.find(query):
                # Check if SFTP is configured
                if ('hostname' in server or 'sftp_host' in server) and ('username' in server or 'sftp_username' in server):
                    # Add to configs
                    sftp_configs.append(server)
            
            # Check game_servers collection if it exists
            if hasattr(db, 'game_servers'):
                async for server in db.game_servers.find(query):
                    # Check if SFTP is configured
                    if ('hostname' in server or 'sftp_host' in server) and ('username' in server or 'sftp_username' in server):
                        # Add to configs
                        sftp_configs.append(server)
                
        except Exception as e:
            logger.error(f"Error getting SFTP configs for guild {guild_id}: {e}")
            
        return sftp_configs
    
    async def get_sftp_connection_params(self, guild_id: str, server_id: str) -> Optional[Dict[str, Any]]:
        """Get SFTP connection parameters for a specific server
        
        Args:
            guild_id: Discord guild ID
            server_id: Server ID
            
        Returns:
            Dictionary with connection parameters or None if not found
        """
        try:
            # Get SFTP configurations
            sftp_configs = await self.get_guild_sftp_configs(guild_id)
            
            # Find config for this server
            for config in sftp_configs:
                if config.get('server_id') == server_id:
                    # Extract connection parameters
                    return {
                        'host': config.get('hostname') or config.get('sftp_host'),
                        'port': config.get('port') or config.get('sftp_port', 22),
                        'username': config.get('username') or config.get('sftp_username'),
                        'password': config.get('password') or config.get('sftp_password'),
                        'server_id': server_id,
                        'guild_id': guild_id,
                        # Include any other helpful parameters
                        'name': config.get('name', server_id),
                        'log_paths': config.get('log_paths', [])
                    }
                    
            # Server not found
            return None
            
        except Exception as e:
            logger.error(f"Error getting SFTP connection params for guild {guild_id}, server {server_id}: {e}")
            return None
    
    async def update_guild_setting(self, guild_id: str, setting: str, value: Any) -> bool:
        """Update a setting for a guild
        
        Args:
            guild_id: Discord guild ID
            setting: Setting name
            value: Setting value
            
        Returns:
            True if setting was updated successfully
        """
        try:
            # Update database
            db = self.bot.db()
            result = await db.guilds.update_one(
                {'guild_id': str(guild_id)},
                {'$set': {f'settings.{setting}': value}},
                upsert=True
            )
            
            # Update cache
            cache_key = f"guild_config:{guild_id}"
            if cache_key in GUILD_CONFIG_CACHE:
                guild_config = GUILD_CONFIG_CACHE[cache_key]['config']
                if 'settings' not in guild_config:
                    guild_config['settings'] = {}
                guild_config['settings'][setting] = value
                GUILD_CONFIG_CACHE[cache_key]['timestamp'] = datetime.now()
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating guild setting {setting} for {guild_id}: {e}")
            return False
    
    async def update_server_config(self, guild_id: str, server_id: str, config: Dict[str, Any]) -> bool:
        """Update configuration for a server
        
        Args:
            guild_id: Discord guild ID
            server_id: Server ID
            config: Server configuration
            
        Returns:
            True if configuration was updated successfully
        """
        try:
            # Update database
            db = self.bot.db()
            result = await db.guilds.update_one(
                {'guild_id': str(guild_id)},
                {'$set': {f'servers.{server_id}': config}},
                upsert=True
            )
            
            # Update cache
            cache_key = f"guild_config:{guild_id}"
            if cache_key in GUILD_CONFIG_CACHE:
                guild_config = GUILD_CONFIG_CACHE[cache_key]['config']
                if 'servers' not in guild_config:
                    guild_config['servers'] = {}
                guild_config['servers'][server_id] = config
                GUILD_CONFIG_CACHE[cache_key]['timestamp'] = datetime.now()
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating server config for guild {guild_id}, server {server_id}: {e}")
            return False
    
    def invalidate_cache(self, guild_id: Optional[str] = None):
        """Invalidate guild configuration cache
        
        Args:
            guild_id: Optional guild ID to invalidate, or None for all guilds
        """
        if guild_id:
            # Invalidate specific guild
            cache_key = f"guild_config:{guild_id}"
            if cache_key in GUILD_CONFIG_CACHE:
                del GUILD_CONFIG_CACHE[cache_key]
        else:
            # Invalidate all guilds
            GUILD_CONFIG_CACHE.clear()

# Singleton instance
_guild_config_instance = None
_guild_config_lock = asyncio.Lock()

async def get_guild_config_manager(bot) -> GuildConfig:
    """Get guild configuration manager singleton
    
    Args:
        bot: Bot instance with database access
        
    Returns:
        GuildConfig instance
    """
    global _guild_config_instance
    
    if _guild_config_instance is None:
        async with _guild_config_lock:
            if _guild_config_instance is None:
                _guild_config_instance = GuildConfig(bot)
    
    return _guild_config_instance