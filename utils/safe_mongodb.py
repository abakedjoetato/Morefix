"""
Safe MongoDB Operations

This module provides safe MongoDB operations with structured result types
and error handling.
"""

import logging
import traceback
from typing import Any, Dict, Generic, List, Optional, TypeVar, Union

logger = logging.getLogger(__name__)

# Type variable for the result type
T = TypeVar('T')

class SafeDocument(Dict[str, Any]):
    """
    A safe document wrapper for MongoDB documents
    
    This provides type-safe access to document fields with default values
    for missing fields.
    """
    
    def get_str(self, key: str, default: str = "") -> str:
        """
        Get a string value from the document
        
        Args:
            key: The key to get
            default: Default value if the key is missing or not a string
            
        Returns:
            The string value or default
        """
        value = self.get(key)
        if value is None:
            return default
        try:
            return str(value)
        except Exception:
            return default
    
    def get_int(self, key: str, default: int = 0) -> int:
        """
        Get an integer value from the document
        
        Args:
            key: The key to get
            default: Default value if the key is missing or not an integer
            
        Returns:
            The integer value or default
        """
        value = self.get(key)
        if value is None:
            return default
        try:
            return int(value)
        except Exception:
            return default
    
    def get_float(self, key: str, default: float = 0.0) -> float:
        """
        Get a float value from the document
        
        Args:
            key: The key to get
            default: Default value if the key is missing or not a float
            
        Returns:
            The float value or default
        """
        value = self.get(key)
        if value is None:
            return default
        try:
            return float(value)
        except Exception:
            return default
    
    def get_bool(self, key: str, default: bool = False) -> bool:
        """
        Get a boolean value from the document
        
        Args:
            key: The key to get
            default: Default value if the key is missing or not a boolean
            
        Returns:
            The boolean value or default
        """
        value = self.get(key)
        if value is None:
            return default
        try:
            return bool(value)
        except Exception:
            return default
    
    def get_list(self, key: str, default: Optional[List[Any]] = None) -> List[Any]:
        """
        Get a list value from the document
        
        Args:
            key: The key to get
            default: Default value if the key is missing or not a list
            
        Returns:
            The list value or default
        """
        if default is None:
            default = []
            
        value = self.get(key)
        if value is None:
            return default
        
        if isinstance(value, list):
            return value
        try:
            # Try to convert to list if possible
            return list(value)
        except Exception:
            return default
    
    def get_dict(self, key: str, default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Get a dictionary value from the document
        
        Args:
            key: The key to get
            default: Default value if the key is missing or not a dictionary
            
        Returns:
            The dictionary value or default
        """
        if default is None:
            default = {}
            
        value = self.get(key)
        if value is None:
            return default
        
        if isinstance(value, dict):
            return value
        return default

class SafeMongoDBResult(Generic[T]):
    """
    A safe result wrapper for MongoDB operations
    
    This provides a structured way to handle successful operations
    and errors consistently.
    
    Attributes:
        success: Whether the operation was successful
        result: The result of the operation (if successful)
        error: The error message (if not successful)
        error_type: The type of error
    """
    
    def __init__(
        self,
        success: bool = False,
        result: Optional[T] = None,
        error: Optional[str] = None,
        error_type: Optional[str] = None
    ):
        """
        Initialize a SafeMongoDBResult
        
        Args:
            success: Whether the operation was successful
            result: The result of the operation (if successful)
            error: The error message (if not successful)
            error_type: The type of error
        """
        self.success = success
        self.result = result
        self.error = error
        self.error_type = error_type or "general"
    
    @classmethod
    def success_result(cls, result: T) -> 'SafeMongoDBResult[T]':
        """
        Create a successful result
        
        Args:
            result: The result data
            
        Returns:
            A successful SafeMongoDBResult
        """
        return cls(success=True, result=result)
    
    @classmethod
    def error_result(cls, error: str, error_type: str = "general") -> 'SafeMongoDBResult[T]':
        """
        Create an error result
        
        Args:
            error: The error message
            error_type: The type of error
            
        Returns:
            An error SafeMongoDBResult
        """
        return cls(success=False, error=error, error_type=error_type)
    
    def __bool__(self) -> bool:
        """
        Boolean conversion for direct use in if statements
        
        Returns:
            The success state
        """
        return self.success

async def safe_mongo_operation(operation, operation_type: str = "general") -> SafeMongoDBResult:
    """
    Execute a MongoDB operation safely with error handling
    
    Args:
        operation: The async operation to execute
        operation_type: The type of operation for error logging
        
    Returns:
        SafeMongoDBResult with the operation result or error
    """
    try:
        result = await operation
        return SafeMongoDBResult.success_result(result)
    except Exception as e:
        error_message = str(e)
        logger.error(f"MongoDB {operation_type} operation failed: {error_message}")
        logger.debug(traceback.format_exc())
        return SafeMongoDBResult.error_result(error_message, operation_type)