"""
SFTP Exceptions for Tower of Temptation PvP Statistics Bot

This module defines custom exceptions for SFTP operations to provide:
1. Detailed error information
2. Proper error categorization
3. Recovery suggestions
4. Consistent error handling patterns
"""
import logging
from typing import Optional, Dict, Any, List

# Configure module-specific logger
logger = logging.getLogger(__name__)

class SFTPError(Exception):
    """Base exception for all SFTP-related errors"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """Initialize with message and optional details
        
        Args:
            message: Human-readable error message
            details: Optional dictionary with error details for logging
        """
        self.message = message
        self.details = details or {}
        super().__init__(message)
        
    def log(self, level: int = logging.ERROR):
        """Log this exception with standard format
        
        Args:
            level: Logging level to use
        """
        if self.details:
            detail_str = ', '.join(f"{k}={v}" for k, v in self.details.items())
            logger.log(level, f"{self.__class__.__name__}: {self.message} - {detail_str}")
        else:
            logger.log(level, f"{self.__class__.__name__}: {self.message}")
            
    def get_user_message(self) -> str:
        """Get a user-friendly error message
        
        Returns:
            Human-readable message suitable for displaying to users
        """
        return self.message
    
    def get_recovery_suggestion(self) -> Optional[str]:
        """Get a suggestion for recovering from this error
        
        Returns:
            Recovery suggestion string or None if no suggestion available
        """
        return None


class SFTPConnectionError(SFTPError):
    """Error establishing an SFTP connection"""
    
    def __init__(self, message: str, host: str, port: int, details: Optional[Dict[str, Any]] = None):
        """Initialize with connection information
        
        Args:
            message: Human-readable error message
            host: Host that failed to connect
            port: Port used for connection attempt
            details: Optional dictionary with additional error details
        """
        super().__init__(message, details)
        self.host = host
        self.port = port
        
    def get_user_message(self) -> str:
        """Get a user-friendly connection error message"""
        return f"Could not connect to server at {self.host}:{self.port}: {self.message}"
    
    def get_recovery_suggestion(self) -> str:
        """Get a suggestion for recovering from connection errors"""
        return (
            "Please check that:\n"
            "1. The server address and port are correct\n"
            "2. The server is online and accepting connections\n"
            "3. Your firewall allows outbound connections to this server\n"
            "4. Your network connection is stable"
        )


class SFTPAuthenticationError(SFTPError):
    """Error authenticating with an SFTP server"""
    
    def __init__(self, message: str, host: str, username: str, details: Optional[Dict[str, Any]] = None):
        """Initialize with authentication information
        
        Args:
            message: Human-readable error message
            host: Host where authentication failed
            username: Username used for authentication
            details: Optional dictionary with additional error details
        """
        super().__init__(message, details)
        self.host = host
        self.username = username
        
    def get_user_message(self) -> str:
        """Get a user-friendly authentication error message"""
        return f"Authentication failed for user '{self.username}' on server {self.host}: {self.message}"
    
    def get_recovery_suggestion(self) -> str:
        """Get a suggestion for recovering from authentication errors"""
        return (
            "Please check that:\n"
            "1. The username is correct\n"
            "2. The password is correct\n"
            "3. The account has SFTP access permissions\n"
            "4. The account is not locked or disabled"
        )


class SFTPFileError(SFTPError):
    """Error accessing a file via SFTP"""
    
    def __init__(self, message: str, path: str, operation: str, details: Optional[Dict[str, Any]] = None):
        """Initialize with file operation information
        
        Args:
            message: Human-readable error message
            path: Path to the file that caused the error
            operation: Operation that was attempted (read, write, etc.)
            details: Optional dictionary with additional error details
        """
        super().__init__(message, details)
        self.path = path
        self.operation = operation
        
    def get_user_message(self) -> str:
        """Get a user-friendly file error message"""
        return f"File operation '{self.operation}' failed for path '{self.path}': {self.message}"
    
    def get_recovery_suggestion(self) -> str:
        """Get a suggestion for recovering from file errors"""
        suggestions = {
            "read": (
                "Please check that:\n"
                "1. The file exists\n"
                "2. You have permission to read this file\n"
                "3. The file is not currently locked by another process"
            ),
            "write": (
                "Please check that:\n"
                "1. You have permission to write to this location\n"
                "2. There is sufficient disk space\n"
                "3. The file is not currently locked by another process"
            ),
            "delete": (
                "Please check that:\n"
                "1. You have permission to delete this file\n"
                "2. The file is not currently locked by another process"
            ),
            "list": (
                "Please check that:\n"
                "1. The directory exists\n"
                "2. You have permission to access this directory"
            )
        }
        
        return suggestions.get(self.operation.lower(), 
                             "Please check file permissions and that the path exists")


class SFTPDirectoryError(SFTPError):
    """Error accessing a directory via SFTP"""
    
    def __init__(self, message: str, path: str, operation: str, details: Optional[Dict[str, Any]] = None):
        """Initialize with directory operation information
        
        Args:
            message: Human-readable error message
            path: Path to the directory that caused the error
            operation: Operation that was attempted (list, create, etc.)
            details: Optional dictionary with additional error details
        """
        super().__init__(message, details)
        self.path = path
        self.operation = operation
        
    def get_user_message(self) -> str:
        """Get a user-friendly directory error message"""
        return f"Directory operation '{self.operation}' failed for path '{self.path}': {self.message}"
    
    def get_recovery_suggestion(self) -> str:
        """Get a suggestion for recovering from directory errors"""
        suggestions = {
            "list": (
                "Please check that:\n"
                "1. The directory exists\n"
                "2. You have permission to list this directory"
            ),
            "create": (
                "Please check that:\n"
                "1. You have permission to create directories in this location\n"
                "2. The parent directory exists\n"
                "3. There is sufficient disk space"
            ),
            "delete": (
                "Please check that:\n"
                "1. You have permission to delete this directory\n"
                "2. The directory is empty or you have permission to delete its contents\n"
                "3. The directory is not currently in use"
            )
        }
        
        return suggestions.get(self.operation.lower(), 
                             "Please check directory permissions and that the path exists")


class SFTPTimeoutError(SFTPError):
    """Error when an SFTP operation times out"""
    
    def __init__(self, message: str, operation: str, timeout_seconds: int, details: Optional[Dict[str, Any]] = None):
        """Initialize with timeout information
        
        Args:
            message: Human-readable error message
            operation: Operation that timed out
            timeout_seconds: Timeout setting in seconds
            details: Optional dictionary with additional error details
        """
        super().__init__(message, details)
        self.operation = operation
        self.timeout_seconds = timeout_seconds
        
    def get_user_message(self) -> str:
        """Get a user-friendly timeout error message"""
        return f"Operation '{self.operation}' timed out after {self.timeout_seconds} seconds: {self.message}"
    
    def get_recovery_suggestion(self) -> str:
        """Get a suggestion for recovering from timeout errors"""
        return (
            "Please check that:\n"
            "1. The server is not under heavy load\n"
            "2. Your network connection is stable\n"
            "3. The operation is not too large (e.g., transferring a very large file)\n"
            "You may want to try again later when the server is less busy."
        )


class SFTPResourceError(SFTPError):
    """Error due to insufficient resources (connections, memory, etc.)"""
    
    def __init__(self, message: str, resource_type: str, details: Optional[Dict[str, Any]] = None):
        """Initialize with resource information
        
        Args:
            message: Human-readable error message
            resource_type: Type of resource that was exhausted
            details: Optional dictionary with additional error details
        """
        super().__init__(message, details)
        self.resource_type = resource_type
        
    def get_user_message(self) -> str:
        """Get a user-friendly resource error message"""
        return f"Resource issue with {self.resource_type}: {self.message}"
    
    def get_recovery_suggestion(self) -> str:
        """Get a suggestion for recovering from resource errors"""
        suggestions = {
            "connections": (
                "The system has reached the maximum number of SFTP connections.\n"
                "Please wait a moment and try again, or close some other connections first."
            ),
            "memory": (
                "The system does not have enough memory to complete this operation.\n"
                "Try with a smaller file or when the system is under less load."
            ),
            "disk": (
                "There is not enough disk space to complete this operation.\n"
                "Free up some disk space and try again."
            )
        }
        
        return suggestions.get(self.resource_type.lower(), 
                             "Please try again later when system resources are available")


class SFTPConfigurationError(SFTPError):
    """Error due to invalid configuration"""
    
    def __init__(self, message: str, config_item: str, details: Optional[Dict[str, Any]] = None):
        """Initialize with configuration information
        
        Args:
            message: Human-readable error message
            config_item: Configuration item that caused the error
            details: Optional dictionary with additional error details
        """
        super().__init__(message, details)
        self.config_item = config_item
        
    def get_user_message(self) -> str:
        """Get a user-friendly configuration error message"""
        return f"Configuration error with {self.config_item}: {self.message}"
    
    def get_recovery_suggestion(self) -> str:
        """Get a suggestion for recovering from configuration errors"""
        return (
            f"Please check the configuration for '{self.config_item}' and ensure it is correctly set."
        )


def format_error_for_user(error: Exception) -> str:
    """Format an exception as a user-friendly message
    
    Args:
        error: Exception to format
        
    Returns:
        Formatted user-friendly error message
    """
    if isinstance(error, SFTPError):
        message = error.get_user_message()
        suggestion = error.get_recovery_suggestion()
        
        if suggestion:
            return f"{message}\n\n{suggestion}"
        return message
    
    # Handle other exception types
    return f"An error occurred: {str(error)}"


def map_library_error(error: Exception, **context) -> SFTPError:
    """Map library-specific errors to our custom exceptions
    
    Args:
        error: Original exception from library (paramiko, asyncssh, etc.)
        **context: Context information for the new exception
        
    Returns:
        Appropriate SFTPError subclass instance
    """
    # Extract common context values
    host = context.get('host', 'unknown')
    port = context.get('port', 0)
    username = context.get('username', 'unknown')
    path = context.get('path', 'unknown')
    operation = context.get('operation', 'unknown')
    
    # Paramiko/asyncssh errors
    error_str = str(error).lower()
    error_type = type(error).__name__
    
    # Handle connection errors
    if any(x in error_str for x in ['connection refused', 'network unreachable', 'timed out', 'no route to host']):
        return SFTPConnectionError(
            f"Connection failed: {error}",
            host=host,
            port=port,
            details={'original_error': error_type, **context}
        )
        
    # Handle authentication errors
    if any(x in error_str for x in ['authentication', 'auth', 'password', 'permission denied']):
        return SFTPAuthenticationError(
            f"Authentication failed: {error}",
            host=host,
            username=username,
            details={'original_error': error_type, **context}
        )
        
    # Handle file errors
    if any(x in error_str for x in ['file', 'no such file', 'permission denied']) and 'path' in context:
        return SFTPFileError(
            f"File operation failed: {error}",
            path=path,
            operation=operation,
            details={'original_error': error_type, **context}
        )
        
    # Handle directory errors
    if any(x in error_str for x in ['directory', 'no such directory', 'permission denied']) and 'path' in context:
        return SFTPDirectoryError(
            f"Directory operation failed: {error}",
            path=path,
            operation=operation,
            details={'original_error': error_type, **context}
        )
        
    # Handle timeout errors
    if 'timeout' in error_str:
        return SFTPTimeoutError(
            f"Operation timed out: {error}",
            operation=operation,
            timeout_seconds=context.get('timeout', 0),
            details={'original_error': error_type, **context}
        )
        
    # Default to base error for unknown types
    return SFTPError(
        f"SFTP operation failed: {error}",
        details={'original_error': error_type, **context}
    )