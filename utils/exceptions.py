"""
Custom Exceptions and Error Handling

This module defines custom exception types for the bot to provide more
precise error handling and user-friendly error messages.
"""

import logging
from typing import Optional, Dict, Any, Union

logger = logging.getLogger(__name__)

class BotBaseException(Exception):
    """Base exception class for all bot-related exceptions"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """
        Initialize the exception with a message and optional details.
        
        Args:
            message: User-friendly error message
            details: Additional details for logging and debugging
        """
        self.message = message
        self.details = details or {}
        super().__init__(message)

class DatabaseError(BotBaseException):
    """Exception raised for database-related errors"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None, 
                operation: Optional[str] = None, collection: Optional[str] = None):
        """
        Initialize the database exception.
        
        Args:
            message: User-friendly error message
            details: Additional details for logging and debugging
            operation: The database operation that failed
            collection: The collection being accessed
        """
        self.operation = operation
        self.collection = collection
        
        # Extend details with operation info
        full_details = details or {}
        if operation:
            full_details['operation'] = operation
        if collection:
            full_details['collection'] = collection
        
        super().__init__(message, full_details)

class PremiumFeatureError(BotBaseException):
    """Exception raised for premium feature access issues"""
    
    def __init__(self, message: str, feature: str, 
                required_tier: Union[int, str], guild_tier: Union[int, str], 
                details: Optional[Dict[str, Any]] = None):
        """
        Initialize the premium feature exception.
        
        Args:
            message: User-friendly error message
            feature: The premium feature that was accessed
            required_tier: The tier required for the feature
            guild_tier: The guild's current tier
            details: Additional details for logging and debugging
        """
        self.feature = feature
        self.required_tier = required_tier
        self.guild_tier = guild_tier
        
        # Extend details with premium info
        full_details = details or {}
        full_details.update({
            'feature': feature,
            'required_tier': required_tier,
            'guild_tier': guild_tier
        })
        
        super().__init__(message, full_details)

class CommandError(BotBaseException):
    """Exception raised for command-related errors"""
    
    def __init__(self, message: str, command_name: Optional[str] = None, 
                user_id: Optional[Union[str, int]] = None,
                guild_id: Optional[Union[str, int]] = None,
                details: Optional[Dict[str, Any]] = None):
        """
        Initialize the command exception.
        
        Args:
            message: User-friendly error message
            command_name: The name of the command that failed
            user_id: The ID of the user who executed the command
            guild_id: The ID of the guild where the command was executed
            details: Additional details for logging and debugging
        """
        self.command_name = command_name
        self.user_id = str(user_id) if user_id else None
        self.guild_id = str(guild_id) if guild_id else None
        
        # Extend details with command info
        full_details = details or {}
        if command_name:
            full_details['command_name'] = command_name
        if user_id:
            full_details['user_id'] = str(user_id)
        if guild_id:
            full_details['guild_id'] = str(guild_id)
        
        super().__init__(message, full_details)

class ConfigurationError(BotBaseException):
    """Exception raised for configuration-related errors"""
    
    def __init__(self, message: str, config_key: Optional[str] = None, 
                details: Optional[Dict[str, Any]] = None):
        """
        Initialize the configuration exception.
        
        Args:
            message: User-friendly error message
            config_key: The configuration key that's problematic
            details: Additional details for logging and debugging
        """
        self.config_key = config_key
        
        # Extend details with config info
        full_details = details or {}
        if config_key:
            full_details['config_key'] = config_key
        
        super().__init__(message, full_details)

class ExternalServiceError(BotBaseException):
    """Exception raised for external service-related errors"""
    
    def __init__(self, message: str, service_name: str, 
                operation: Optional[str] = None,
                details: Optional[Dict[str, Any]] = None):
        """
        Initialize the external service exception.
        
        Args:
            message: User-friendly error message
            service_name: The name of the external service (e.g., 'SFTP')
            operation: The operation that failed
            details: Additional details for logging and debugging
        """
        self.service_name = service_name
        self.operation = operation
        
        # Extend details with service info
        full_details = details or {}
        full_details['service_name'] = service_name
        if operation:
            full_details['operation'] = operation
        
        super().__init__(message, full_details)

def format_user_error_message(exception: Exception) -> str:
    """
    Format an exception into a user-friendly error message.
    
    Args:
        exception: The exception to format
        
    Returns:
        str: A formatted error message suitable for displaying to users
    """
    # Handle our custom exceptions with special formatting
    if isinstance(exception, PremiumFeatureError):
        return (
            f"⚠️ **Premium Feature Required**\n"
            f"The feature '{exception.feature}' requires the "
            f"`{exception.required_tier}` tier, but your server has the "
            f"`{exception.guild_tier}` tier.\n"
            f"Use `/premium info` to learn more about upgrading."
        )
    
    elif isinstance(exception, DatabaseError):
        return (
            f"⚠️ **Database Error**\n"
            f"{exception.message}\n"
            f"Please try again later. If the issue persists, contact support."
        )
    
    elif isinstance(exception, CommandError):
        return (
            f"⚠️ **Command Error**\n"
            f"{exception.message}"
        )
    
    elif isinstance(exception, ConfigurationError):
        return (
            f"⚠️ **Configuration Error**\n"
            f"{exception.message}"
        )
    
    elif isinstance(exception, ExternalServiceError):
        return (
            f"⚠️ **{exception.service_name} Service Error**\n"
            f"{exception.message}\n"
            f"Please try again later. If the issue persists, contact support."
        )
    
    elif isinstance(exception, BotBaseException):
        return (
            f"⚠️ **Error**\n"
            f"{exception.message}"
        )
    
    # Handle generic exceptions
    else:
        return (
            f"⚠️ **Unexpected Error**\n"
            f"An error occurred: {str(exception)}\n"
            f"Please try again later. If the issue persists, contact support."
        )

def log_exception(exception: Exception, 
                 context: Optional[Dict[str, Any]] = None,
                 level: int = logging.ERROR) -> None:
    """
    Log an exception with context details.
    
    Args:
        exception: The exception to log
        context: Additional context information
        level: Logging level (default: ERROR)
    """
    # Prepare context dictionary
    ctx = context or {}
    
    # Extract details from our custom exceptions
    if isinstance(exception, BotBaseException) and exception.details:
        ctx.update(exception.details)
    
    # Format the log message
    log_message = f"Exception: {type(exception).__name__}: {str(exception)}"
    if ctx:
        log_message += f" | Context: {ctx}"
    
    # Log at the specified level
    logger.log(level, log_message, exc_info=True)