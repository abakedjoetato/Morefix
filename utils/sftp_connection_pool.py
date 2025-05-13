"""
SFTP Connection Pool for Tower of Temptation PvP Statistics Bot

This module provides a robust connection pooling system for SFTP connections with:
1. Thread-safe connection management
2. Connection health checks and auto-reconnection
3. Guild-specific connection isolation
4. Resource usage limits with proper cleanup
5. Detailed error handling and logging
"""
import os
import logging
import asyncio
import random
import time
import traceback
import threading
from typing import Dict, Optional, List, Set, Tuple, Any, Callable, Awaitable, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import weakref

import asyncssh
from asyncssh import SSHClientConnection, SFTPClient

from utils.sftp_exceptions import (
    SFTPError, SFTPConnectionError, SFTPAuthenticationError, 
    SFTPResourceError, SFTPTimeoutError, map_library_error
)

# Configure module-specific logger
logger = logging.getLogger(__name__)

# Check if SFTP is enabled in the environment
SFTP_ENABLED = os.environ.get("SFTP_ENABLED", "false").lower() == "true"

if not SFTP_ENABLED:
    logger.warning("SFTP functionality is disabled. Set SFTP_ENABLED=true to enable it.")

# Default configuration values
DEFAULT_CONNECTION_TIMEOUT = 30
DEFAULT_OPERATION_TIMEOUT = 60
DEFAULT_MAX_CONNECTIONS_PER_GUILD = 5
DEFAULT_MAX_TOTAL_CONNECTIONS = 50
DEFAULT_CONNECTION_IDLE_TIMEOUT = 300  # 5 minutes
DEFAULT_HEALTH_CHECK_INTERVAL = 60     # 1 minute
DEFAULT_RETRY_DELAY = 2
DEFAULT_MAX_RETRIES = 3

# Configuration can be overridden through environment variables
MAX_CONNECTIONS_PER_GUILD = int(os.environ.get("SFTP_MAX_CONNECTIONS_PER_GUILD", DEFAULT_MAX_CONNECTIONS_PER_GUILD))
MAX_TOTAL_CONNECTIONS = int(os.environ.get("SFTP_MAX_TOTAL_CONNECTIONS", DEFAULT_MAX_TOTAL_CONNECTIONS))
CONNECTION_IDLE_TIMEOUT = int(os.environ.get("SFTP_CONNECTION_IDLE_TIMEOUT", DEFAULT_CONNECTION_IDLE_TIMEOUT))
HEALTH_CHECK_INTERVAL = int(os.environ.get("SFTP_HEALTH_CHECK_INTERVAL", DEFAULT_HEALTH_CHECK_INTERVAL))

# Guild configuration manager reference (will be set during initialization)
_guild_config_manager = None

@dataclass
class ConnectionInfo:
    """Information about a pooled SFTP connection"""
    
    # Connection identifiers
    connection_id: str
    guild_id: str
    host: str
    port: int
    username: str
    
    # Connection state
    client: Optional[SSHClientConnection] = None
    sftp_client: Optional[SFTPClient] = None
    connected: bool = False
    in_use: bool = False
    
    # Timestamps for lifecycle management
    created_at: datetime = field(default_factory=datetime.now)
    last_used_at: datetime = field(default_factory=datetime.now)
    last_health_check: datetime = field(default_factory=datetime.now)
    
    # Statistics
    connect_count: int = 0
    error_count: int = 0
    operation_count: int = 0
    
    # Last error information
    last_error: Optional[str] = None
    
    def __str__(self) -> str:
        """String representation with important details"""
        status = "Connected" if self.connected else f"Disconnected ({self.last_error})"
        idle_time = (datetime.now() - self.last_used_at).total_seconds()
        return (
            f"SFTP Connection {self.connection_id} to {self.host}:{self.port} "
            f"({self.username}) - Status: {status}, "
            f"Idle: {idle_time:.1f}s, Ops: {self.operation_count}"
        )
    
    def is_stale(self, idle_timeout: int = CONNECTION_IDLE_TIMEOUT) -> bool:
        """Check if connection has been idle for too long
        
        Args:
            idle_timeout: Maximum idle time in seconds
            
        Returns:
            True if connection is stale and should be closed
        """
        idle_time = (datetime.now() - self.last_used_at).total_seconds()
        return idle_time > idle_timeout
    
    def is_healthy(self) -> bool:
        """Check if connection appears to be in a healthy state
        
        Returns:
            True if connection looks healthy
        """
        return self.connected and not self.in_use and self.error_count <= 5
    
    def mark_used(self) -> None:
        """Mark connection as in use and update last_used_at"""
        self.in_use = True
        self.last_used_at = datetime.now()
        
    def mark_released(self) -> None:
        """Mark connection as no longer in use"""
        self.in_use = False
        self.last_used_at = datetime.now()
        
    def mark_health_checked(self) -> None:
        """Mark that a health check was performed on this connection"""
        self.last_health_check = datetime.now()
        
    def mark_error(self, error: str) -> None:
        """Mark that an error occurred on this connection
        
        Args:
            error: Error message to log
        """
        self.error_count += 1
        self.last_error = error
        
    def mark_operation(self) -> None:
        """Mark that an operation was performed on this connection"""
        self.operation_count += 1


class SFTPConnectionPool:
    """Thread-safe pool for managing SFTP connections
    
    Provides connection pooling, health checks, and resource management
    for SFTP connections across multiple guilds.
    """
    
    def __init__(self, bot=None):
        """Initialize the connection pool
        
        Args:
            bot: Optional bot instance for guild configuration access
        """
        # Main connection registry
        self._connections: Dict[str, ConnectionInfo] = {}
        
        # Track connections by guild for resource management
        self._guild_connections: Dict[str, Set[str]] = {}
        
        # Locks for thread safety
        self._pool_lock = asyncio.Lock()
        self._guild_locks: Dict[str, asyncio.Lock] = {}
        
        # Background task
        self._maintenance_task = None
        
        # Stats
        self._stats = {
            "total_connections_created": 0,
            "total_connections_closed": 0,
            "connection_errors": 0,
            "health_check_failures": 0,
        }
        
        # Flag to indicate if pool has been started
        self._started = False
        
        # Bot reference for guild configuration
        self._bot = bot
        self._guild_config = None
        
    async def start(self):
        """Start the connection pool maintenance task
        
        Returns:
            True if the pool was started successfully
        """
        if self._started:
            logger.debug("Connection pool already started")
            return True
            
        logger.info("Starting SFTP connection pool")
        
        # Initialize guild configuration manager if we have a bot
        if self._bot:
            try:
                from utils.guild_config import get_guild_config_manager
                self._guild_config = await get_guild_config_manager(self._bot)
                logger.info("Guild configuration manager initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize guild configuration manager: {e}")
        
        # Start background maintenance task
        self._maintenance_task = asyncio.create_task(self._maintenance_loop())
        self._started = True
        
        return True
        
    async def stop(self):
        """Stop the connection pool and close all connections
        
        Returns:
            True if the pool was stopped successfully
        """
        if not self._started:
            logger.debug("Connection pool not running")
            return True
            
        logger.info("Stopping SFTP connection pool")
        
        # Cancel maintenance task
        if self._maintenance_task and not self._maintenance_task.done():
            self._maintenance_task.cancel()
            try:
                await self._maintenance_task
            except asyncio.CancelledError:
                pass
            
        # Close all connections
        async with self._pool_lock:
            connection_ids = list(self._connections.keys())
            
        for conn_id in connection_ids:
            await self.close_connection(conn_id)
            
        self._started = False
        
        return True
    
    async def get_connection(
        self,
        guild_id: str,
        host: str,
        port: int = 22,
        username: Optional[str] = None,
        password: Optional[str] = None,
        timeout: int = DEFAULT_CONNECTION_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_delay: int = DEFAULT_RETRY_DELAY,
        force_new: bool = False
    ) -> Tuple[str, Optional[SFTPClient]]:
        """Get a connection from the pool or create a new one
        
        Args:
            guild_id: ID of the guild requesting the connection
            host: SFTP server hostname
            port: SFTP server port
            username: Login username
            password: Login password
            timeout: Connection timeout in seconds
            max_retries: Maximum number of connection attempts
            retry_delay: Delay between retries in seconds
            force_new: Force creation of a new connection even if one exists
        
        Returns:
            Tuple of (connection_id, sftp_client)
            
        Raises:
            SFTPConnectionError: If connection fails
            SFTPAuthenticationError: If authentication fails
            SFTPResourceError: If resource limits are exceeded
        """
        if not SFTP_ENABLED:
            logger.warning("SFTP connection requested but SFTP is disabled")
            raise SFTPError("SFTP functionality is disabled", {"enabled": False})
        
        if not self._started:
            logger.info("Connection pool not started, starting now")
            await self.start()
            
        # Parameter validation
        if host is None:
            raise ValueError("Host cannot be None")
            
        # Normalize connection parameters
        host = host.strip()
        username = username.strip() if username else ""
        
        # Set default username if none provided
        if not username:
            username = "anonymous"
        
        # Generate connection key
        conn_key = f"{host}:{port}:{username}:{guild_id}"
        
        # Get guild lock
        guild_lock = await self._get_guild_lock(guild_id)
        
        # Check existing connections for this guild
        if not force_new:
            async with guild_lock:
                if guild_id in self._guild_connections:
                    # Try to find an existing connection for this server
                    for existing_conn_id in self._guild_connections[guild_id]:
                        async with self._pool_lock:
                            if (existing_conn_id in self._connections and 
                                self._connections[existing_conn_id].host == host and
                                self._connections[existing_conn_id].port == port and
                                self._connections[existing_conn_id].username == username and
                                not self._connections[existing_conn_id].in_use):
                                
                                conn_info = self._connections[existing_conn_id]
                                
                                # Check if connection is still valid
                                if conn_info.connected:
                                    logger.debug(f"Reusing existing connection: {existing_conn_id}")
                                    conn_info.mark_used()
                                    return existing_conn_id, conn_info.sftp_client
        
        # We need to create a new connection
        
        # Get guild-specific resource limits if available
        max_total_connections = MAX_TOTAL_CONNECTIONS
        max_guild_connections = MAX_CONNECTIONS_PER_GUILD
        
        if self._guild_config:
            try:
                # Get resource limits for this guild
                resource_limits = await self._guild_config.get_resource_limits(guild_id)
                max_guild_connections = resource_limits.get("max_sftp_connections", MAX_CONNECTIONS_PER_GUILD)
                
                # Check rate limit for SFTP operations
                allowed, retry_after = await self._guild_config.check_rate_limit(guild_id, "sftp")
                if not allowed:
                    logger.warning(f"Rate limit reached for guild {guild_id}, retry after {retry_after:.1f}s")
                    raise SFTPResourceError(
                        f"Rate limit reached for SFTP operations, retry after {retry_after:.1f} seconds", 
                        resource_type="rate_limit",
                        details={"guild_id": guild_id, "retry_after": retry_after}
                    )
                    
                logger.debug(f"Using guild-specific limits for {guild_id}: max_connections={max_guild_connections}")
            except Exception as e:
                logger.warning(f"Error getting guild resource limits: {e}")
        
        # First check resource limits
        async with self._pool_lock:
            total_connections = len(self._connections)
            
            if total_connections >= max_total_connections:
                logger.warning(f"Total connection limit reached: {total_connections}/{max_total_connections}")
                
                # Try to clean up stale connections
                await self._cleanup_stale_connections()
                
                # Check again
                if len(self._connections) >= max_total_connections:
                    raise SFTPResourceError(
                        f"Maximum total connections limit ({max_total_connections}) reached", 
                        resource_type="connections",
                        details={"guild_id": guild_id, "total_connections": total_connections}
                    )
        
        # Check guild-specific limits
        async with guild_lock:
            guild_connection_count = len(self._guild_connections.get(guild_id, set()))
            
            if guild_connection_count >= max_guild_connections:
                logger.warning(f"Guild connection limit reached for {guild_id}: {guild_connection_count}/{max_guild_connections}")
                
                # Try to clean up stale connections for this guild
                await self._cleanup_guild_connections(guild_id)
                
                # Check again
                if len(self._guild_connections.get(guild_id, set())) >= max_guild_connections:
                    raise SFTPResourceError(
                        f"Maximum connections per guild ({max_guild_connections}) reached", 
                        resource_type="guild_connections",
                        details={"guild_id": guild_id, "guild_connections": guild_connection_count}
                    )
        
        # Create connection ID with timestamp and random component for uniqueness
        timestamp = int(time.time())
        random_component = random.randint(1000, 9999)
        connection_id = f"{host}:{port}:{timestamp}:{random_component}"
        
        # Create connection with retries
        connected = False
        sftp_client = None
        last_error = None
        
        # Create connection info
        conn_info = ConnectionInfo(
            connection_id=connection_id,
            guild_id=guild_id,
            host=host,
            port=port,
            username=username
        )
        
        # Add to tracking even before connecting so we don't exceed limits
        async with self._pool_lock:
            self._connections[connection_id] = conn_info
            self._stats["total_connections_created"] += 1
        
        async with guild_lock:
            if guild_id not in self._guild_connections:
                self._guild_connections[guild_id] = set()
            self._guild_connections[guild_id].add(connection_id)
        
        # Attempt connection with retries
        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"Establishing SFTP connection to {host}:{port} (attempt {attempt}/{max_retries})")
                
                # Create SSH client connection
                client = await asyncio.wait_for(
                    asyncssh.connect(
                        host=host,
                        port=port,
                        username=username,
                        password=password,
                        known_hosts=None  # For simplicity - in production should verify hosts
                    ),
                    timeout=timeout
                )
                
                # Create SFTP client
                sftp_client = await client.start_sftp_client()
                
                # Mark connection as successful
                connected = True
                conn_info.connected = True
                conn_info.client = client
                conn_info.sftp_client = sftp_client
                conn_info.connect_count += 1
                conn_info.mark_used()
                
                logger.info(f"SFTP connection established successfully: {connection_id}")
                break
                
            except asyncio.TimeoutError as e:
                last_error = SFTPTimeoutError(
                    f"Connection timed out after {timeout} seconds", 
                    operation="connect",
                    timeout_seconds=timeout,
                    details={"host": host, "port": port, "attempt": attempt}
                )
                last_error.log()
                
            except asyncssh.PermissionDenied as e:
                last_error = SFTPAuthenticationError(
                    str(e), 
                    host=host, 
                    username=username,
                    details={"port": port, "attempt": attempt}
                )
                last_error.log()
                break  # Don't retry auth failures
                
            except Exception as e:
                last_error = map_library_error(
                    e, 
                    host=host, 
                    port=port, 
                    username=username, 
                    operation="connect",
                    attempt=attempt
                )
                last_error.log()
            
            # If we get here, the connection failed
            if attempt < max_retries:
                logger.info(f"Retrying connection in {retry_delay} seconds")
                await asyncio.sleep(retry_delay)
            
        # If connection failed after all retries, clean up and raise error
        if not connected:
            logger.error(f"Failed to establish SFTP connection after {max_retries} attempts")
            
            # Update connection info
            conn_info.connected = False
            conn_info.mark_error(str(last_error))
            
            # Clean up failed connection
            await self.close_connection(connection_id)
            
            # Propagate the error
            if last_error:
                raise last_error
            else:
                raise SFTPConnectionError(
                    f"Failed to connect after {max_retries} attempts", 
                    host=host, 
                    port=port,
                    details={"username": username}
                )
                
        return connection_id, sftp_client
    
    async def release_connection(self, connection_id: str):
        """Release a connection back to the pool
        
        Args:
            connection_id: ID of the connection to release
        
        Returns:
            True if connection was successfully released
        """
        async with self._pool_lock:
            if connection_id not in self._connections:
                logger.warning(f"Attempt to release unknown connection: {connection_id}")
                return False
                
            conn_info = self._connections[connection_id]
            
            # Mark connection as no longer in use
            conn_info.mark_released()
            logger.debug(f"Connection released: {connection_id}")
            
            return True
    
    async def close_connection(self, connection_id: str):
        """Close and remove a connection from the pool
        
        Args:
            connection_id: ID of the connection to close
        
        Returns:
            True if connection was successfully closed
        """
        async with self._pool_lock:
            if connection_id not in self._connections:
                logger.warning(f"Attempt to close unknown connection: {connection_id}")
                return False
                
            conn_info = self._connections[connection_id]
            guild_id = conn_info.guild_id
            
            # Close SFTP client
            if conn_info.sftp_client:
                try:
                    conn_info.sftp_client.exit()
                except Exception as e:
                    logger.warning(f"Error closing SFTP client {connection_id}: {e}")
            
            # Close SSH connection
            if conn_info.client:
                try:
                    conn_info.client.close()
                except Exception as e:
                    logger.warning(f"Error closing SSH client {connection_id}: {e}")
            
            # Update stats
            self._stats["total_connections_closed"] += 1
            
            # Remove from connection registry
            del self._connections[connection_id]
        
        # Remove from guild tracking
        if guild_id:
            # Get guild lock
            guild_lock = await self._get_guild_lock(guild_id)
            
            async with guild_lock:
                if guild_id in self._guild_connections:
                    self._guild_connections[guild_id].discard(connection_id)
                    
                    # Clean up guild entry if no more connections
                    if not self._guild_connections[guild_id]:
                        del self._guild_connections[guild_id]
        
        logger.debug(f"Connection closed and removed from pool: {connection_id}")
        return True
    
    async def check_connection_health(self, connection_id: str) -> bool:
        """Check if a connection is healthy by running a simple SFTP operation
        
        Args:
            connection_id: ID of the connection to check
        
        Returns:
            True if connection is healthy, False otherwise
        """
        async with self._pool_lock:
            if connection_id not in self._connections:
                logger.warning(f"Attempt to check health of unknown connection: {connection_id}")
                return False
                
            conn_info = self._connections[connection_id]
            
            # Skip if connection is in use
            if conn_info.in_use:
                logger.debug(f"Skipping health check for in-use connection: {connection_id}")
                return True
                
            # Skip if not connected
            if not conn_info.connected or not conn_info.sftp_client:
                logger.debug(f"Connection {connection_id} not connected, marking unhealthy")
                return False
        
        # Perform health check
        try:
            logger.debug(f"Performing health check for connection: {connection_id}")
            
            # Run simple SFTP operation (list current directory)
            async with self._pool_lock:
                conn_info.mark_used()
            
            try:
                await asyncio.wait_for(
                    conn_info.sftp_client.stat('.'), 
                    timeout=10
                )
                
                # Update health check timestamp
                async with self._pool_lock:
                    conn_info.mark_health_checked()
                    conn_info.mark_released()
                
                return True
                
            except Exception as e:
                logger.warning(f"Health check failed for connection {connection_id}: {e}")
                
                async with self._pool_lock:
                    conn_info.connected = False
                    conn_info.mark_error(f"Health check failed: {e}")
                    conn_info.mark_released()
                    self._stats["health_check_failures"] += 1
                
                return False
                
        except Exception as e:
            logger.error(f"Error during health check for {connection_id}: {e}")
            
            async with self._pool_lock:
                conn_info.connected = False
                conn_info.mark_error(f"Health check error: {e}")
                conn_info.mark_released()
                self._stats["health_check_failures"] += 1
            
            return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the connection pool
        
        Returns:
            Dictionary with pool statistics
        """
        async with self._pool_lock:
            stats = {
                "active_connections": len(self._connections),
                "guilds_with_connections": len(self._guild_connections),
                "connections_in_use": sum(1 for c in self._connections.values() if c.in_use),
                **self._stats
            }
            
            # Add guild-specific stats
            guild_stats = {}
            for guild_id, conn_ids in self._guild_connections.items():
                guild_conn_count = len(conn_ids)
                in_use = sum(1 for cid in conn_ids if cid in self._connections and self._connections[cid].in_use)
                guild_stats[guild_id] = {
                    "total_connections": guild_conn_count,
                    "in_use": in_use
                }
                
            stats["guilds"] = guild_stats
            
            return stats
    
    async def _get_guild_lock(self, guild_id: str) -> asyncio.Lock:
        """Get or create a lock for a specific guild
        
        Args:
            guild_id: ID of the guild
            
        Returns:
            Lock for the guild
        """
        async with self._pool_lock:
            if guild_id not in self._guild_locks:
                self._guild_locks[guild_id] = asyncio.Lock()
            return self._guild_locks[guild_id]
    
    async def _cleanup_stale_connections(self):
        """Clean up connections that have been idle for too long"""
        stale_connections = []
        
        # Find stale connections
        async with self._pool_lock:
            for conn_id, conn_info in list(self._connections.items()):
                if not conn_info.in_use and conn_info.is_stale():
                    logger.info(f"Connection {conn_id} idle for too long, marking as stale")
                    stale_connections.append(conn_id)
        
        # Close stale connections
        for conn_id in stale_connections:
            await self.close_connection(conn_id)
            
        if stale_connections:
            logger.info(f"Cleaned up {len(stale_connections)} stale connections")
            
        return len(stale_connections)
    
    async def _cleanup_guild_connections(self, guild_id: str):
        """Clean up stale connections for a specific guild
        
        Args:
            guild_id: ID of the guild
            
        Returns:
            Number of connections cleaned up
        """
        stale_connections = []
        
        # Get guild lock
        guild_lock = await self._get_guild_lock(guild_id)
        
        # Find stale connections for this guild
        async with guild_lock:
            if guild_id in self._guild_connections:
                for conn_id in list(self._guild_connections[guild_id]):
                    async with self._pool_lock:
                        if conn_id in self._connections:
                            conn_info = self._connections[conn_id]
                            if not conn_info.in_use and conn_info.is_stale():
                                logger.info(f"Guild {guild_id} connection {conn_id} idle for too long, marking as stale")
                                stale_connections.append(conn_id)
        
        # Close stale connections
        for conn_id in stale_connections:
            await self.close_connection(conn_id)
            
        if stale_connections:
            logger.info(f"Cleaned up {len(stale_connections)} stale connections for guild {guild_id}")
            
        return len(stale_connections)
    
    async def _perform_health_checks(self):
        """Perform health checks on all connections"""
        async with self._pool_lock:
            connection_ids = list(self._connections.keys())
            
        for conn_id in connection_ids:
            try:
                await self.check_connection_health(conn_id)
            except Exception as e:
                logger.error(f"Error during health check for {conn_id}: {e}")
    
    async def _maintenance_loop(self):
        """Background task to maintain the connection pool"""
        logger.info(f"Starting connection pool maintenance (interval: {HEALTH_CHECK_INTERVAL}s)")
        
        while True:
            try:
                # Sleep first to allow connections to be established
                await asyncio.sleep(HEALTH_CHECK_INTERVAL)
                
                # Skip if no connections
                async with self._pool_lock:
                    if not self._connections:
                        continue
                
                # Log current state
                logger.debug(f"Connection pool: {len(self._connections)} connections, "
                             f"Guilds: {len(self._guild_connections)}")
                
                # Clean up stale connections
                await self._cleanup_stale_connections()
                
                # Perform health checks
                await self._perform_health_checks()
                
            except asyncio.CancelledError:
                logger.info("Connection pool maintenance task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in connection pool maintenance: {e}")
                traceback.print_exc()


# Singleton instance to be used throughout the application
_pool_instance = None
_pool_lock = asyncio.Lock()

async def get_connection_pool(bot=None) -> SFTPConnectionPool:
    """Get the singleton connection pool instance
    
    Args:
        bot: Optional bot instance for guild configuration access
    
    Returns:
        SFTPConnectionPool instance
    """
    global _pool_instance
    
    if _pool_instance is None:
        async with _pool_lock:
            if _pool_instance is None:
                _pool_instance = SFTPConnectionPool(bot=bot)
                await _pool_instance.start()
    
    return _pool_instance


class SFTPContextManager:
    """Context manager for safely using SFTP connections
    
    Use with 'async with' to automatically acquire and release connections:
    
    async with SFTPContextManager(guild_id, host, ...) as sftp:
        # Use sftp client here
        await sftp.listdir("/some/path")
    """
    
    def __init__(
        self,
        guild_id: str,
        host: str,
        port: int = 22,
        username: Optional[str] = None,
        password: Optional[str] = None,
        timeout: int = DEFAULT_CONNECTION_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_delay: int = DEFAULT_RETRY_DELAY,
        force_new: bool = False
    ):
        """Initialize the context manager
        
        Args:
            guild_id: ID of the guild requesting the connection
            host: SFTP server hostname
            port: SFTP server port
            username: Login username
            password: Login password
            timeout: Connection timeout in seconds
            max_retries: Maximum number of connection attempts
            retry_delay: Delay between retries in seconds
            force_new: Force creation of a new connection even if one exists
        """
        self.guild_id = guild_id
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.force_new = force_new
        
        # These will be set in __aenter__
        self.connection_id = None
        self.sftp_client = None
        self.pool = None
    
    async def __aenter__(self) -> SFTPClient:
        """Acquire a connection from the pool
        
        Returns:
            SFTP client object
            
        Raises:
            ValueError: If required parameters are missing
        """
        # Parameter validation
        if self.host is None:
            raise ValueError("Host cannot be None")
            
        # Default username if none provided
        if not self.username:
            self.username = "anonymous"
            
        self.pool = await get_connection_pool()
        
        # Get a connection
        self.connection_id, self.sftp_client = await self.pool.get_connection(
            guild_id=self.guild_id,
            host=self.host,
            port=self.port,
            username=self.username,
            password=self.password,
            timeout=self.timeout,
            max_retries=self.max_retries,
            retry_delay=self.retry_delay,
            force_new=self.force_new
        )
        
        return self.sftp_client
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Release the connection back to the pool"""
        if self.connection_id and self.pool:
            await self.pool.release_connection(self.connection_id)


# Initialize the background task when module is imported
async def initialize_sftp_pool(bot=None):
    """Initialize the SFTP connection pool
    
    Should be called during application startup.
    
    Args:
        bot: Optional bot instance for guild configuration access
    
    Returns:
        True if pool was initialized successfully
    """
    if SFTP_ENABLED:
        logger.info("Initializing SFTP connection pool")
        pool = await get_connection_pool(bot=bot)
        return True
    else:
        logger.warning("SFTP is disabled, skipping connection pool initialization")
        return False