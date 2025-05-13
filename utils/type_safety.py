"""
Type Safety Module for Discord API Compatibility

This module provides utilities for safely working with types across
different versions of Python and Discord libraries.
"""

import inspect
import logging
import re
import traceback
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar, Union, cast, get_type_hints

# Setup logger
logger = logging.getLogger(__name__)

# Type variables for return typing
T = TypeVar('T')

def safe_cast(value: Any, target_type: Any, default: Optional[T] = None) -> Union[Any, T]:
    """
    Safely cast a value to a target type.
    
    Args:
        value: Value to cast
        target_type: Type to cast to
        default: Default value to return if casting fails
        
    Returns:
        Cast value, or default if casting fails
    """
    if value is None:
        return default
        
    try:
        # Handle built-in types
        if target_type in (str, int, float, bool):
            return target_type(value)
            
        # Handle list type
        if getattr(target_type, "__origin__", None) is list:
            item_type = getattr(target_type, "__args__", [Any])[0]
            if isinstance(value, list):
                return [safe_cast(item, item_type, item) for item in value]
            else:
                return default
                
        # Handle dict type
        if getattr(target_type, "__origin__", None) is dict:
            key_type = getattr(target_type, "__args__", [Any, Any])[0]
            value_type = getattr(target_type, "__args__", [Any, Any])[1]
            if isinstance(value, dict):
                return {
                    safe_cast(k, key_type, k): safe_cast(v, value_type, v)
                    for k, v in value.items()
                }
            else:
                return default
                
        # Handle union type
        if getattr(target_type, "__origin__", None) is Union:
            for union_type in getattr(target_type, "__args__", []):
                try:
                    return safe_cast(value, union_type)
                except (ValueError, TypeError):
                    continue
                    
            return default
            
        # Handle instance check
        if isinstance(value, target_type):
            return value
            
        # Handle custom casting if possible
        if hasattr(target_type, "from_dict") and isinstance(value, dict):
            return target_type.from_dict(value)
            
        # Handle direct casting
        return target_type(value)
    except (ValueError, TypeError) as e:
        logger.debug(f"Failed to cast {value} to {target_type}: {e}")
        return default

def safe_str(value: Any, max_length: int = 2000) -> str:
    """
    Safely convert a value to a string.
    
    Args:
        value: Value to convert
        max_length: Maximum string length
        
    Returns:
        String representation of the value
    """
    if value is None:
        return ""
        
    try:
        result = str(value)
        
        # Truncate if necessary
        if len(result) > max_length:
            return result[:max_length - 3] + "..."
            
        return result
    except Exception as e:
        logger.error(f"Failed to convert {value} to string: {e}")
        return ""

def safe_int(value: Any, default: int = 0) -> int:
    """
    Safely convert a value to an integer.
    
    Args:
        value: Value to convert
        default: Default value
        
    Returns:
        Integer representation of the value
    """
    if value is None:
        return default
        
    try:
        # Handle special cases
        if isinstance(value, bool):
            return 1 if value else 0
            
        # Handle string
        if isinstance(value, str):
            value = value.strip()
            
            # Handle empty string
            if not value:
                return default
                
        return int(value)
    except (ValueError, TypeError):
        logger.debug(f"Failed to convert {value} to int")
        return default

def safe_float(value: Any, default: float = 0.0) -> float:
    """
    Safely convert a value to a float.
    
    Args:
        value: Value to convert
        default: Default value
        
    Returns:
        Float representation of the value
    """
    if value is None:
        return default
        
    try:
        # Handle special cases
        if isinstance(value, bool):
            return 1.0 if value else 0.0
            
        # Handle string
        if isinstance(value, str):
            value = value.strip()
            
            # Handle empty string
            if not value:
                return default
                
        return float(value)
    except (ValueError, TypeError):
        logger.debug(f"Failed to convert {value} to float")
        return default

def safe_bool(value: Any, default: bool = False) -> bool:
    """
    Safely convert a value to a boolean.
    
    Args:
        value: Value to convert
        default: Default value
        
    Returns:
        Boolean representation of the value
    """
    if value is None:
        return default
        
    # Handle special cases
    if isinstance(value, str):
        value = value.strip().lower()
        
        # Handle empty string
        if not value:
            return default
            
        # Handle common string values
        if value in ("true", "t", "yes", "y", "1"):
            return True
            
        if value in ("false", "f", "no", "n", "0"):
            return False
            
    # Handle numeric values
    if isinstance(value, (int, float)):
        return bool(value)
        
    try:
        return bool(value)
    except (ValueError, TypeError):
        logger.debug(f"Failed to convert {value} to bool")
        return default

def safe_list(value: Any, item_type: Any = Any, default: Optional[List] = None) -> List:
    """
    Safely convert a value to a list.
    
    Args:
        value: Value to convert
        item_type: Type of list items
        default: Default value
        
    Returns:
        List representation of the value
    """
    if default is None:
        default = []
        
    if value is None:
        return default.copy()
        
    try:
        # Handle string
        if isinstance(value, str):
            value = value.strip()
            
            # Handle empty string
            if not value:
                return default.copy()
                
            # Handle JSON-like string
            if (value.startswith("[") and value.endswith("]")) or \
               (value.startswith("{") and value.endswith("}")):
                try:
                    import json
                    value = json.loads(value)
                except Exception:
                    pass
                    
        # Handle dictionary
        if isinstance(value, dict):
            value = list(value.items())
            
        # Handle iterable
        if hasattr(value, "__iter__") and not isinstance(value, (str, bytes, dict)):
            result = list(value)
            
            # Cast items if needed
            if item_type is not Any:
                result = [safe_cast(item, item_type) for item in result]
                
            return result
            
        # Handle scalar
        return [safe_cast(value, item_type) if item_type is not Any else value]
    except Exception as e:
        logger.debug(f"Failed to convert {value} to list: {e}")
        return default.copy()

def safe_dict(value: Any, default: Optional[Dict] = None) -> Dict:
    """
    Safely convert a value to a dictionary.
    
    Args:
        value: Value to convert
        default: Default value
        
    Returns:
        Dictionary representation of the value
    """
    if default is None:
        default = {}
        
    if value is None:
        return default.copy()
        
    try:
        # Handle string
        if isinstance(value, str):
            value = value.strip()
            
            # Handle empty string
            if not value:
                return default.copy()
                
            # Handle JSON-like string
            if (value.startswith("{") and value.endswith("}")) or \
               (value.startswith("[") and value.endswith("]")):
                try:
                    import json
                    value = json.loads(value)
                except Exception:
                    pass
                    
        # Handle dictionary
        if isinstance(value, dict):
            return dict(value)
            
        # Handle list of pairs
        if isinstance(value, list):
            try:
                return dict(value)
            except (ValueError, TypeError):
                pass
                
        # Handle object with attributes
        if hasattr(value, "__dict__"):
            return {
                k: v for k, v in value.__dict__.items()
                if not k.startswith("_")
            }
            
        # Handle object with to_dict method
        if hasattr(value, "to_dict") and callable(value.to_dict):
            return value.to_dict()
            
        logger.debug(f"Failed to convert {value} to dict")
        return default.copy()
    except Exception as e:
        logger.debug(f"Failed to convert {value} to dict: {e}")
        return default.copy()

def get_exception_info() -> Tuple[str, str, str]:
    """
    Get information about the current exception.
    
    Returns:
        Tuple of (exception type, exception message, traceback)
    """
    # Get the exception info
    exc_type, exc_value, exc_traceback = traceback.exc_info()
    
    # Get the exception type name
    type_name = exc_type.__name__ if exc_type else "Unknown"
    
    # Get the exception message
    message = str(exc_value) if exc_value else "No message"
    
    # Get the traceback
    tb = traceback.format_exception(exc_type, exc_value, exc_traceback)
    tb_str = "".join(tb)
    
    return type_name, message, tb_str

def safe_function_call(
    func: Callable,
    *args,
    default_return: Any = None,
    log_error: bool = True,
    **kwargs
) -> Any:
    """
    Safely call a function with proper error handling.
    
    Args:
        func: Function to call
        *args: Positional arguments
        default_return: Default return value if the function raises an exception
        log_error: Whether to log errors
        **kwargs: Keyword arguments
        
    Returns:
        Function result, or default_return if the function raises an exception
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        if log_error:
            logger.error(f"Error calling {func.__name__}: {e}")
        return default_return

def validate_type(value: Any, expected_type: Any) -> bool:
    """
    Validate that a value matches an expected type.
    
    Args:
        value: Value to validate
        expected_type: Expected type
        
    Returns:
        True if the value matches the expected type, False otherwise
    """
    # Handle None
    if value is None:
        return expected_type is type(None) or \
               getattr(expected_type, "__origin__", None) is Union and \
               type(None) in getattr(expected_type, "__args__", [])
               
    # Handle any type
    if expected_type is Any:
        return True
        
    # Handle union type
    if getattr(expected_type, "__origin__", None) is Union:
        return any(validate_type(value, t) for t in getattr(expected_type, "__args__", []))
        
    # Handle list type
    if getattr(expected_type, "__origin__", None) is list:
        if not isinstance(value, list):
            return False
            
        # If list is empty, we can't validate item types
        if not value:
            return True
            
        # Get the expected item type
        item_type = getattr(expected_type, "__args__", [Any])[0]
        
        # Check each item
        return all(validate_type(item, item_type) for item in value)
        
    # Handle dict type
    if getattr(expected_type, "__origin__", None) is dict:
        if not isinstance(value, dict):
            return False
            
        # If dict is empty, we can't validate item types
        if not value:
            return True
            
        # Get the expected key and value types
        key_type = getattr(expected_type, "__args__", [Any, Any])[0]
        value_type = getattr(expected_type, "__args__", [Any, Any])[1]
        
        # Check each key and value
        return all(
            validate_type(k, key_type) and validate_type(v, value_type)
            for k, v in value.items()
        )
        
    # Handle instance check
    return isinstance(value, expected_type)

def validate_func_args(
    func: Callable,
    *args,
    **kwargs
) -> bool:
    """
    Validate that arguments match a function's parameter types.
    
    Args:
        func: Function to validate arguments for
        *args: Positional arguments
        **kwargs: Keyword arguments
        
    Returns:
        True if the arguments match the function's parameter types, False otherwise
    """
    try:
        # Get the function's parameter specifications
        sig = inspect.signature(func)
        
        # Get the function's type hints
        hints = get_type_hints(func)
        
        # Create a mapping of parameters to arguments
        bound_args = sig.bind(*args, **kwargs)
        
        # Validate each argument
        for param_name, param in sig.parameters.items():
            # Skip parameters without type hints
            if param_name not in hints:
                continue
                
            # Skip parameters not provided in the arguments
            if param_name not in bound_args.arguments:
                # If the parameter has a default value, it's okay
                if param.default is not inspect.Parameter.empty:
                    continue
                    
                # If the parameter is variadic, it's okay
                if param.kind in (
                    inspect.Parameter.VAR_POSITIONAL,
                    inspect.Parameter.VAR_KEYWORD
                ):
                    continue
                    
                # Otherwise, a required parameter is missing
                return False
                
            # Get the argument value
            arg_value = bound_args.arguments[param_name]
            
            # Get the expected type
            expected_type = hints[param_name]
            
            # Validate the type
            if not validate_type(arg_value, expected_type):
                return False
                
        return True
    except Exception as e:
        logger.debug(f"Error validating arguments for {func.__name__}: {e}")
        return False