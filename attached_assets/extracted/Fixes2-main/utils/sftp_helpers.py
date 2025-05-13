"""
SFTP Helpers for Tower of Temptation PvP Statistics Bot

This module provides high-level helper functions for common SFTP operations:
1. File operations (read, write, list, find)
2. Directory operations (list, create, check)
3. Path manipulation and normalization
4. File pattern matching and filtering

Uses the connection pool for efficient connection management.
"""
import os
import logging
import re
import fnmatch
import asyncio
import io
from typing import List, Dict, Optional, Tuple, Union, BinaryIO, Set, Any
from datetime import datetime, timedelta
import stat

import asyncssh
from asyncssh import SFTPClient

from utils.sftp_connection_pool import SFTPContextManager, initialize_sftp_pool
from utils.sftp_exceptions import (
    SFTPError, SFTPFileError, SFTPDirectoryError, 
    map_library_error, format_error_for_user
)

# Configure module-specific logger
logger = logging.getLogger(__name__)

# Cache for directory listings to reduce redundant operations
DIR_CACHE = {}
DIR_CACHE_TTL = 60  # Cache directory listings for 60 seconds

async def list_directory(
    guild_id: str,
    host: str,
    port: int,
    username: str,
    password: str,
    path: str,
    pattern: Optional[str] = None,
    use_cache: bool = True,
    recursive: bool = False,
    max_depth: int = 3,
    include_dirs: bool = False,
    sort_by_date: bool = False
) -> List[Dict[str, Any]]:
    """List files in a directory with pattern matching and sorting
    
    Args:
        guild_id: Guild ID for connection isolation
        host: SFTP server hostname
        port: SFTP server port
        username: Login username
        password: Login password
        path: Directory path to list
        pattern: Optional glob pattern to filter files (e.g., "*.csv")
        use_cache: Whether to use cached directory listings
        recursive: Whether to list subdirectories recursively
        max_depth: Maximum recursion depth
        include_dirs: Whether to include directories in results
        sort_by_date: Whether to sort by modification time (newest first)
    
    Returns:
        List of file info dictionaries with paths relative to the given path
    
    Raises:
        SFTPDirectoryError: If directory can't be listed
    """
    cache_key = f"{host}:{port}:{path}:{pattern}:{recursive}:{max_depth}:{include_dirs}"
    
    # Check cache if enabled
    if use_cache and cache_key in DIR_CACHE:
        cache_time, cache_results = DIR_CACHE[cache_key]
        if (datetime.now() - cache_time).total_seconds() < DIR_CACHE_TTL:
            logger.debug(f"Using cached directory listing for {path}")
            return cache_results
    
    # File list to return
    file_list = []
    
    try:
        async with SFTPContextManager(
            guild_id=guild_id,
            host=host,
            port=port,
            username=username,
            password=password
        ) as sftp:
            # Process directory
            file_list = await _process_directory(
                sftp=sftp,
                base_path=path,
                current_path=path,
                pattern=pattern,
                recursive=recursive,
                current_depth=0,
                max_depth=max_depth,
                include_dirs=include_dirs
            )
            
            # Sort by date if requested
            if sort_by_date and file_list:
                # Make sure we have modification times for all files
                for file_info in file_list:
                    if "mtime" not in file_info:
                        try:
                            stat_result = await sftp.stat(file_info["full_path"])
                            file_info["mtime"] = stat_result.mtime
                        except Exception:
                            # Use a very old time for files without mtime
                            file_info["mtime"] = 0
                
                # Sort by modification time, newest first
                file_list.sort(key=lambda x: x.get("mtime", 0), reverse=True)
            
            # Update cache
            if use_cache:
                DIR_CACHE[cache_key] = (datetime.now(), file_list)
                
            return file_list
            
    except asyncssh.SFTPNoSuchFile:
        # If directory doesn't exist, return empty list rather than error
        logger.warning(f"Directory not found: {path}")
        return []
    except Exception as e:
        error = map_library_error(
            e, 
            host=host, 
            path=path, 
            operation="list",
            recursive=recursive
        )
        error.log()
        raise error

async def _process_directory(
    sftp: SFTPClient,
    base_path: str,
    current_path: str,
    pattern: Optional[str] = None,
    recursive: bool = False,
    current_depth: int = 0,
    max_depth: int = 3,
    include_dirs: bool = False
) -> List[Dict[str, Any]]:
    """Process a directory recursively to find matching files
    
    Args:
        sftp: Open SFTP client
        base_path: Base directory path for making relative paths
        current_path: Current directory being processed
        pattern: Optional glob pattern to filter files
        recursive: Whether to process subdirectories
        current_depth: Current recursion depth
        max_depth: Maximum recursion depth
        include_dirs: Whether to include directories in results
    
    Returns:
        List of file info dictionaries
    """
    result = []
    
    try:
        # List files in current directory
        dir_entries = await sftp.readdir(current_path)
        
        # Process each entry
        for entry in dir_entries:
            entry_path = os.path.join(current_path, entry.filename)
            
            # Skip parent and current directory entries
            if entry.filename in ('.', '..'):
                continue
            
            # Create relative path from base directory
            if current_path == base_path:
                rel_path = entry.filename
            else:
                rel_path = os.path.relpath(entry_path, base_path)
            
            # Check if this is a directory
            is_dir = stat.S_ISDIR(entry.attrs.permissions) if entry.attrs and hasattr(entry.attrs, 'permissions') else False
            
            # Process directories if recursive
            if is_dir:
                # Add directory to result if requested
                if include_dirs:
                    result.append({
                        'name': entry.filename,
                        'path': rel_path,
                        'full_path': entry_path,
                        'type': 'directory',
                        'size': 0,
                        'mtime': entry.attrs.mtime if entry.attrs and hasattr(entry.attrs, 'mtime') else None
                    })
                
                # Process subdirectory if we haven't reached max depth
                if recursive and current_depth < max_depth:
                    sub_files = await _process_directory(
                        sftp=sftp,
                        base_path=base_path,
                        current_path=entry_path,
                        pattern=pattern,
                        recursive=recursive,
                        current_depth=current_depth + 1,
                        max_depth=max_depth,
                        include_dirs=include_dirs
                    )
                    result.extend(sub_files)
            else:
                # This is a file - check if it matches pattern
                if pattern and not fnmatch.fnmatch(entry.filename.lower(), pattern.lower()):
                    continue
                    
                # Add file to result
                result.append({
                    'name': entry.filename,
                    'path': rel_path,
                    'full_path': entry_path,
                    'type': 'file',
                    'size': entry.attrs.size if entry.attrs and hasattr(entry.attrs, 'size') else 0,
                    'mtime': entry.attrs.mtime if entry.attrs and hasattr(entry.attrs, 'mtime') else None
                })
                
        return result
    
    except Exception as e:
        logger.error(f"Error processing directory {current_path}: {e}")
        return []

async def read_file(
    guild_id: str,
    host: str,
    port: int,
    username: str,
    password: str,
    path: str,
    timeout: int = 30,
    chunk_size: int = 65536,  # 64KB chunks
    max_size: int = 10485760  # 10MB max file size
) -> bytes:
    """Read a file from SFTP server
    
    Args:
        guild_id: Guild ID for connection isolation
        host: SFTP server hostname
        port: SFTP server port
        username: Login username
        password: Login password
        path: Path to file
        timeout: Operation timeout in seconds
        chunk_size: Size of chunks to read at a time
        max_size: Maximum file size to read
    
    Returns:
        File contents as bytes
    
    Raises:
        SFTPFileError: If file can't be read
        ValueError: If file exceeds max_size
    """
    try:
        async with SFTPContextManager(
            guild_id=guild_id,
            host=host,
            port=port,
            username=username,
            password=password
        ) as sftp:
            # Check file size first
            stat_result = await sftp.stat(path)
            file_size = stat_result.size
            
            if file_size > max_size:
                raise ValueError(
                    f"File is too large: {file_size} bytes (max: {max_size} bytes)"
                )
                
            # Read file in chunks
            data = bytearray()
            
            async with sftp.open(path, 'rb') as f:
                while True:
                    # Check if max size would be exceeded
                    if len(data) >= max_size:
                        raise ValueError(
                            f"Read size limit exceeded: {max_size} bytes"
                        )
                        
                    # Read chunk with timeout
                    try:
                        chunk = await asyncio.wait_for(
                            f.read(chunk_size),
                            timeout=timeout
                        )
                    except asyncio.TimeoutError:
                        raise SFTPFileError(
                            f"Timeout reading file after {timeout} seconds", 
                            path=path, 
                            operation="read",
                            details={"bytes_read": len(data), "file_size": file_size}
                        )
                        
                    if not chunk:
                        break
                        
                    data.extend(chunk)
                    
            return bytes(data)
            
    except SFTPError:
        # Re-raise existing SFTPError exceptions
        raise
    except Exception as e:
        error = map_library_error(
            e, 
            host=host, 
            path=path, 
            operation="read"
        )
        error.log()
        raise error

async def write_file(
    guild_id: str,
    host: str,
    port: int,
    username: str,
    password: str,
    path: str,
    data: Union[bytes, str, BinaryIO],
    timeout: int = 30,
    chunk_size: int = 65536,  # 64KB chunks
    max_size: int = 10485760  # 10MB max file size
) -> int:
    """Write data to a file on SFTP server
    
    Args:
        guild_id: Guild ID for connection isolation
        host: SFTP server hostname
        port: SFTP server port
        username: Login username
        password: Login password
        path: Path to file
        data: Data to write (bytes, string, or file-like object)
        timeout: Operation timeout in seconds
        chunk_size: Size of chunks to write at a time
        max_size: Maximum file size to write
    
    Returns:
        Number of bytes written
    
    Raises:
        SFTPFileError: If file can't be written
        ValueError: If data exceeds max_size
    """
    # Convert string to bytes if needed
    if isinstance(data, str):
        data = data.encode('utf-8')
        
    # Get data size
    if isinstance(data, bytes):
        data_size = len(data)
    elif hasattr(data, 'seek') and hasattr(data, 'tell'):
        # It's a file-like object, get size
        current_pos = data.tell()
        data.seek(0, os.SEEK_END)
        data_size = data.tell()
        data.seek(current_pos)  # Restore position
    else:
        raise ValueError("Data must be bytes, string, or file-like object")
        
    # Check size limit
    if data_size > max_size:
        raise ValueError(
            f"Data is too large: {data_size} bytes (max: {max_size} bytes)"
        )
    
    # Create a BytesIO if data is bytes
    if isinstance(data, bytes):
        data = io.BytesIO(data)
    
    try:
        async with SFTPContextManager(
            guild_id=guild_id,
            host=host,
            port=port,
            username=username,
            password=password
        ) as sftp:
            # Make sure parent directory exists
            parent_dir = os.path.dirname(path)
            if parent_dir:
                try:
                    await sftp.stat(parent_dir)
                except asyncssh.SFTPNoSuchFile:
                    # Create parent directories if they don't exist
                    await sftp.mkdir(parent_dir, parents=True)
            
            # Write file in chunks
            bytes_written = 0
            
            async with sftp.open(path, 'wb') as f:
                while True:
                    # Read chunk from source
                    chunk = data.read(chunk_size)
                    
                    if not chunk:
                        break
                        
                    # Write chunk with timeout
                    try:
                        await asyncio.wait_for(
                            f.write(chunk),
                            timeout=timeout
                        )
                    except asyncio.TimeoutError:
                        raise SFTPFileError(
                            f"Timeout writing file after {timeout} seconds", 
                            path=path, 
                            operation="write",
                            details={"bytes_written": bytes_written, "data_size": data_size}
                        )
                        
                    bytes_written += len(chunk)
                    
            return bytes_written
            
    except SFTPError:
        # Re-raise existing SFTPError exceptions
        raise
    except Exception as e:
        error = map_library_error(
            e, 
            host=host, 
            path=path, 
            operation="write"
        )
        error.log()
        raise error

async def delete_file(
    guild_id: str,
    host: str,
    port: int,
    username: str,
    password: str,
    path: str,
    timeout: int = 30
) -> bool:
    """Delete a file from SFTP server
    
    Args:
        guild_id: Guild ID for connection isolation
        host: SFTP server hostname
        port: SFTP server port
        username: Login username
        password: Login password
        path: Path to file
        timeout: Operation timeout in seconds
    
    Returns:
        True if file was deleted successfully
    
    Raises:
        SFTPFileError: If file can't be deleted
    """
    try:
        async with SFTPContextManager(
            guild_id=guild_id,
            host=host,
            port=port,
            username=username,
            password=password
        ) as sftp:
            # Delete file with timeout
            try:
                await asyncio.wait_for(
                    sftp.remove(path),
                    timeout=timeout
                )
                
                # Invalidate any cache entries that might include this file
                _invalidate_related_cache(host, port, path)
                
                return True
                
            except asyncio.TimeoutError:
                raise SFTPFileError(
                    f"Timeout deleting file after {timeout} seconds", 
                    path=path, 
                    operation="delete"
                )
            
    except SFTPError:
        # Re-raise existing SFTPError exceptions
        raise
    except Exception as e:
        error = map_library_error(
            e, 
            host=host, 
            path=path, 
            operation="delete"
        )
        error.log()
        raise error

async def find_files(
    guild_id: str,
    host: str,
    port: int,
    username: str,
    password: str,
    base_path: str,
    pattern: str,
    recursive: bool = True,
    max_depth: int = 5,
    max_files: int = 100,
    sort_by_date: bool = True
) -> List[Dict[str, Any]]:
    """Find files matching a pattern, with sorting and limiting
    
    Args:
        guild_id: Guild ID for connection isolation
        host: SFTP server hostname
        port: SFTP server port
        username: Login username
        password: Login password
        base_path: Base directory to start search
        pattern: Glob pattern to match files (e.g., "*.csv")
        recursive: Whether to search subdirectories
        max_depth: Maximum recursion depth
        max_files: Maximum number of files to return
        sort_by_date: Whether to sort by modification time (newest first)
    
    Returns:
        List of matching file info dictionaries
    
    Raises:
        SFTPDirectoryError: If directory can't be listed
    """
    # Use the directory listing function with our parameters
    files = await list_directory(
        guild_id=guild_id,
        host=host,
        port=port,
        username=username,
        password=password,
        path=base_path,
        pattern=pattern,
        recursive=recursive,
        max_depth=max_depth,
        include_dirs=False,
        sort_by_date=sort_by_date
    )
    
    # Limit number of files returned
    if max_files > 0 and len(files) > max_files:
        files = files[:max_files]
        
    return files

async def file_exists(
    guild_id: str,
    host: str,
    port: int,
    username: str,
    password: str,
    path: str
) -> bool:
    """Check if a file exists on SFTP server
    
    Args:
        guild_id: Guild ID for connection isolation
        host: SFTP server hostname
        port: SFTP server port
        username: Login username
        password: Login password
        path: Path to file
    
    Returns:
        True if file exists, False otherwise
    """
    try:
        async with SFTPContextManager(
            guild_id=guild_id,
            host=host,
            port=port,
            username=username,
            password=password
        ) as sftp:
            # Check if file exists
            try:
                attrs = await sftp.stat(path)
                # Make sure it's a file, not a directory
                if attrs and hasattr(attrs, 'permissions'):
                    return not stat.S_ISDIR(attrs.permissions)
                return True
            except asyncssh.SFTPNoSuchFile:
                return False
            
    except Exception:
        # For this function, we just return False on any errors
        return False

async def dir_exists(
    guild_id: str,
    host: str,
    port: int,
    username: str,
    password: str,
    path: str
) -> bool:
    """Check if a directory exists on SFTP server
    
    Args:
        guild_id: Guild ID for connection isolation
        host: SFTP server hostname
        port: SFTP server port
        username: Login username
        password: Login password
        path: Path to directory
    
    Returns:
        True if directory exists, False otherwise
    """
    try:
        async with SFTPContextManager(
            guild_id=guild_id,
            host=host,
            port=port,
            username=username,
            password=password
        ) as sftp:
            # Check if path exists and is a directory
            try:
                attrs = await sftp.stat(path)
                # Make sure it's a directory
                if attrs and hasattr(attrs, 'permissions'):
                    return stat.S_ISDIR(attrs.permissions)
                return False
            except asyncssh.SFTPNoSuchFile:
                return False
            
    except Exception:
        # For this function, we just return False on any errors
        return False

async def create_directory(
    guild_id: str,
    host: str,
    port: int,
    username: str,
    password: str,
    path: str,
    parents: bool = True,
    timeout: int = 30
) -> bool:
    """Create a directory on SFTP server
    
    Args:
        guild_id: Guild ID for connection isolation
        host: SFTP server hostname
        port: SFTP server port
        username: Login username
        password: Login password
        path: Path to directory
        parents: Whether to create parent directories if they don't exist
        timeout: Operation timeout in seconds
    
    Returns:
        True if directory was created successfully
    
    Raises:
        SFTPDirectoryError: If directory can't be created
    """
    try:
        async with SFTPContextManager(
            guild_id=guild_id,
            host=host,
            port=port,
            username=username,
            password=password
        ) as sftp:
            # Create directory with timeout
            try:
                await asyncio.wait_for(
                    sftp.mkdir(path, parents=parents),
                    timeout=timeout
                )
                
                # Invalidate any cache entries that might include this directory
                _invalidate_related_cache(host, port, path)
                
                return True
                
            except asyncio.TimeoutError:
                raise SFTPDirectoryError(
                    f"Timeout creating directory after {timeout} seconds", 
                    path=path, 
                    operation="create"
                )
            
    except SFTPError:
        # Re-raise existing SFTPError exceptions
        raise
    except Exception as e:
        error = map_library_error(
            e, 
            host=host, 
            path=path, 
            operation="create_dir"
        )
        error.log()
        raise error

async def get_latest_csv_files(
    guild_id: str,
    host: str,
    port: int,
    username: str,
    password: str,
    base_path: str,
    max_files: int = 10,
    max_age_hours: int = 24
) -> List[Dict[str, Any]]:
    """Get the latest CSV files with age filtering
    
    Args:
        guild_id: Guild ID for connection isolation
        host: SFTP server hostname
        port: SFTP server port
        username: Login username
        password: Login password
        base_path: Base directory to start search
        max_files: Maximum number of files to return
        max_age_hours: Maximum age of files in hours (0 for no limit)
    
    Returns:
        List of matching file info dictionaries
    """
    # Find CSV files
    files = await find_files(
        guild_id=guild_id,
        host=host,
        port=port,
        username=username,
        password=password,
        base_path=base_path,
        pattern="*.csv",
        recursive=True,
        max_depth=5,
        max_files=0,  # No limit yet as we'll filter by date
        sort_by_date=True
    )
    
    # Filter by age if specified
    if max_age_hours > 0 and files:
        now = datetime.now()
        oldest_time = now - timedelta(hours=max_age_hours)
        
        # Filter files by modification time
        filtered_files = []
        for file_info in files:
            mtime = file_info.get("mtime")
            if mtime:
                file_time = datetime.fromtimestamp(mtime)
                if file_time >= oldest_time:
                    filtered_files.append(file_info)
            else:
                # If no mtime, just include the file
                filtered_files.append(file_info)
                
        files = filtered_files
    
    # Limit number of files
    if max_files > 0 and len(files) > max_files:
        files = files[:max_files]
        
    return files

def _invalidate_related_cache(host: str, port: int, path: str) -> None:
    """Invalidate any cache entries related to the given path
    
    Args:
        host: SFTP server hostname
        port: SFTP server port
        path: Path that was modified
    """
    prefix = f"{host}:{port}:"
    parent_dir = os.path.dirname(path)
    
    # Find and remove any cache entries related to this path or its parent directories
    keys_to_remove = []
    for cache_key in DIR_CACHE.keys():
        if cache_key.startswith(prefix):
            # Extract the directory path from the cache key
            parts = cache_key.split(":", 3)
            if len(parts) >= 4:
                dir_path = parts[2]
                
                # Check if this cache entry is for this path or a parent directory
                if dir_path == parent_dir or path.startswith(dir_path):
                    keys_to_remove.append(cache_key)
    
    # Remove invalidated cache entries
    for key in keys_to_remove:
        DIR_CACHE.pop(key, None)
        
    if keys_to_remove:
        logger.debug(f"Invalidated {len(keys_to_remove)} cache entries related to {path}")


# Higher-level helper functions for common patterns

async def test_sftp_connection(
    guild_id: str,
    host: str,
    port: int,
    username: str,
    password: str,
    test_path: Optional[str] = None
) -> Tuple[bool, Optional[str]]:
    """Test SFTP connection and optionally check access to a specific path
    
    Args:
        guild_id: Guild ID for connection isolation
        host: SFTP server hostname
        port: SFTP server port
        username: Login username
        password: Login password
        test_path: Optional path to check access to
    
    Returns:
        Tuple of (success, error_message)
    """
    try:
        async with SFTPContextManager(
            guild_id=guild_id,
            host=host,
            port=port,
            username=username,
            password=password
        ) as sftp:
            # Test basic connection
            await sftp.stat('.')
            
            # Test specific path if provided
            if test_path:
                try:
                    await sftp.stat(test_path)
                except asyncssh.SFTPNoSuchFile:
                    return False, f"Path not found: {test_path}"
            
            return True, None
            
    except Exception as e:
        error = map_library_error(
            e, 
            host=host, 
            port=port, 
            username=username, 
            operation="connect"
        )
        error.log()
        return False, format_error_for_user(error)

async def search_for_csv_files(
    guild_id: str,
    host: str,
    port: int,
    username: str,
    password: str,
    search_paths: List[str],
    max_files: int = 10
) -> List[Dict[str, Any]]:
    """Search multiple paths for CSV files and return the newest ones
    
    Args:
        guild_id: Guild ID for connection isolation
        host: SFTP server hostname
        port: SFTP server port
        username: Login username
        password: Login password
        search_paths: List of paths to search
        max_files: Maximum number of files to return
    
    Returns:
        List of file info dictionaries for the newest CSV files
    """
    all_files = []
    
    # Search each path
    for base_path in search_paths:
        try:
            # Find CSV files in this path
            files = await find_files(
                guild_id=guild_id,
                host=host,
                port=port,
                username=username,
                password=password,
                base_path=base_path,
                pattern="*.csv",
                recursive=True,
                max_depth=3,
                max_files=max_files * 2,  # Get more than we need for sorting
                sort_by_date=True
            )
            
            all_files.extend(files)
            
        except Exception as e:
            logger.warning(f"Error searching path {base_path}: {e}")
    
    # Sort all files by date, newest first
    all_files.sort(key=lambda x: x.get("mtime", 0), reverse=True)
    
    # Limit to max_files
    if max_files > 0 and len(all_files) > max_files:
        all_files = all_files[:max_files]
        
    return all_files