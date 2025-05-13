"""
Safe MongoDB operations with proper error handling

This module provides classes and functions for safely interacting with
MongoDB including error handling, type checking, and result wrapping.
"""

import logging
from typing import Any, Dict, List, Optional, Union, TypeVar, Generic, cast
import asyncio

logger = logging.getLogger(__name__)

T = TypeVar('T')

class SafeMongoDBResult:
    """
    A safe result wrapper for MongoDB operations.
    
    Provides a standard interface for checking success/failure
    and accessing results or error information.
    """
    
    def __init__(
        self, 
        success: bool = False, 
        data: Any = None, 
        error_message: str = None, 
        exception: Exception = None
    ):
        self._success = success
        self._data = data
        self._error_message = error_message
        self._exception = exception
    
    @property
    def success(self) -> bool:
        """Whether the operation was successful"""
        return self._success
    
    @property
    def data(self) -> Any:
        """The operation result data"""
        return self._data
    
    def error_message(self) -> Optional[str]:
        """Error message if operation failed"""
        if self._error_message:
            return self._error_message
        if self._exception:
            return str(self._exception)
        if not self._success:
            return "Unknown error occurred"
        return None
    
    def error(self) -> Optional[Exception]:
        """The underlying exception if one occurred"""
        return self._exception
    
    @classmethod
    def success_result(cls, data: Any = None) -> 'SafeMongoDBResult':
        """Create a success result"""
        return cls(success=True, data=data)
    
    @classmethod
    def error_result(
        cls, 
        error_message: str = None, 
        exception: Exception = None
    ) -> 'SafeMongoDBResult':
        """Create an error result"""
        return cls(
            success=False, 
            error_message=error_message, 
            exception=exception
        )
    
    def __bool__(self) -> bool:
        """Allow direct boolean checks: `if result:`"""
        return self._success

class SafeDocument:
    """
    A safe wrapper around MongoDB documents with helpful accessors.
    
    Provides convenient methods for safely accessing document fields
    with proper type checking and error handling.
    """
    
    def __init__(self, document: Optional[Dict[str, Any]] = None):
        """
        Initialize the document wrapper.
        
        Args:
            document: MongoDB document
        """
        self._document = document or {}
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Safely get a field value with error handling.
        
        Args:
            key: Document field key
            default: Default value if field doesn't exist
            
        Returns:
            Field value or default
        """
        try:
            return self._document.get(key, default)
        except Exception:
            return default
    
    def get_nested(self, path: str, default: Any = None) -> Any:
        """
        Safely get a nested field value using dot notation.
        
        Args:
            path: Dot-notation path (e.g., 'user.address.street')
            default: Default value if path doesn't exist
            
        Returns:
            Nested field value or default
        """
        current = self._document
        keys = path.split('.')
        
        try:
            for key in keys:
                if not isinstance(current, dict):
                    return default
                
                current = current.get(key)
                if current is None:
                    return default
            
            return current
        except Exception:
            return default
    
    def get_int(self, key: str, default: int = 0) -> int:
        """
        Get an integer field with type validation.
        
        Args:
            key: Document field key
            default: Default value if field doesn't exist or isn't an int
            
        Returns:
            Integer field value or default
        """
        try:
            value = self.get(key)
            if value is None:
                return default
            
            if isinstance(value, bool):  # Handle bool case separately
                return 1 if value else 0
            
            return int(value)
        except (ValueError, TypeError):
            return default
    
    def get_float(self, key: str, default: float = 0.0) -> float:
        """
        Get a float field with type validation.
        
        Args:
            key: Document field key
            default: Default value if field doesn't exist or isn't a float
            
        Returns:
            Float field value or default
        """
        try:
            value = self.get(key)
            if value is None:
                return default
            
            return float(value)
        except (ValueError, TypeError):
            return default
    
    def get_bool(self, key: str, default: bool = False) -> bool:
        """
        Get a boolean field with type validation.
        
        Args:
            key: Document field key
            default: Default value if field doesn't exist or isn't a bool
            
        Returns:
            Boolean field value or default
        """
        value = self.get(key)
        
        if value is None:
            return default
        
        if isinstance(value, bool):
            return value
        
        # Handle common string representations
        if isinstance(value, str):
            lower_val = value.lower()
            if lower_val in ('true', 'yes', '1', 'y'):
                return True
            if lower_val in ('false', 'no', '0', 'n'):
                return False
        
        # Handle numeric values
        if isinstance(value, (int, float)):
            return bool(value)
        
        return default
    
    def get_list(self, key: str, default: List = None) -> List:
        """
        Get a list field with type validation.
        
        Args:
            key: Document field key
            default: Default value if field doesn't exist or isn't a list
            
        Returns:
            List field value or default
        """
        if default is None:
            default = []
        
        value = self.get(key)
        
        if value is None:
            return default
        
        if isinstance(value, list):
            return value
        
        # Try to convert to list if possible
        try:
            if isinstance(value, (str, bytes, dict)):
                return list(value)
        except Exception:
            pass
        
        return default
    
    def get_dict(self, key: str, default: Dict = None) -> Dict:
        """
        Get a dictionary field with type validation.
        
        Args:
            key: Document field key
            default: Default value if field doesn't exist or isn't a dict
            
        Returns:
            Dict field value or default
        """
        if default is None:
            default = {}
        
        value = self.get(key)
        
        if value is None:
            return default
        
        if isinstance(value, dict):
            return value
        
        return default
    
    def has_field(self, key: str) -> bool:
        """
        Check if a field exists in the document.
        
        Args:
            key: Document field key
            
        Returns:
            True if field exists, False otherwise
        """
        return key in self._document
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary.
        
        Returns:
            The wrapped document as a dictionary
        """
        return self._document
    
    def __getitem__(self, key: str) -> Any:
        """
        Dictionary-style access to fields.
        
        Args:
            key: Document field key
            
        Returns:
            Field value or None
        """
        return self.get(key)

async def safe_mongodb_operation(operation_func, error_result=None):
    """
    Safely execute a MongoDB operation with error handling.
    
    Args:
        operation_func: Async function to execute
        error_result: Value to return on error
        
    Returns:
        Operation result or error_result
    """
    try:
        return await operation_func()
    except Exception as e:
        logger.error(f"MongoDB operation error: {e}")
        return error_result