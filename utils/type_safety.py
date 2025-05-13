"""
Type Safety Utilities

This module provides type safety utilities to ensure safe type conversions
and function calls across different Python versions.
"""

import inspect
import logging
import traceback
from typing import Any, Dict, List, Optional, Tuple, Union, TypeVar, Callable, Type, cast, get_type_hints

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

T = TypeVar('T')

def safe_cast(value: Any, target_type: Type[T], default: Optional[T] = None) -> Optional[T]:
    """
    Safely cast a value to a target type.
    
    Args:
        value: The value to cast
        target_type: The type to cast to
        default: The default value to return if casting fails
        
    Returns:
        The cast value or the default
    """
    if value is None:
        return default
        
    try:
        if target_type == bool and isinstance(value, str):
            # Handle boolean string conversion specially
            return cast(T, value.lower() in ('true', 'yes', 'y', '1', 'on'))
            
        return target_type(value)
    except Exception as e:
        logger.debug(f"Error casting {value} to {target_type}: {e}")
        return default

def safe_str(value: Any, default: str = "") -> str:
    """
    Safely convert a value to a string.
    
    Args:
        value: The value to convert
        default: The default value to return if conversion fails
        
    Returns:
        The string value or the default
    """
    if value is None:
        return default
        
    try:
        return str(value)
    except Exception as e:
        logger.debug(f"Error converting {value} to string: {e}")
        return default

def safe_int(value: Any, default: int = 0) -> int:
    """
    Safely convert a value to an integer.
    
    Args:
        value: The value to convert
        default: The default value to return if conversion fails
        
    Returns:
        The integer value or the default
    """
    if value is None:
        return default
        
    try:
        if isinstance(value, bool):
            return int(value)
        elif isinstance(value, str):
            # Try to handle common prefixes
            value = value.strip().lower()
            if value.startswith('0x'):
                return int(value, 16)
            elif value.startswith('0b'):
                return int(value, 2)
            elif value.startswith('0o'):
                return int(value, 8)
            else:
                return int(float(value))
        else:
            return int(value)
    except Exception as e:
        logger.debug(f"Error converting {value} to int: {e}")
        return default

def safe_float(value: Any, default: float = 0.0) -> float:
    """
    Safely convert a value to a float.
    
    Args:
        value: The value to convert
        default: The default value to return if conversion fails
        
    Returns:
        The float value or the default
    """
    if value is None:
        return default
        
    try:
        if isinstance(value, bool):
            return float(value)
        elif isinstance(value, str):
            return float(value.strip())
        else:
            return float(value)
    except Exception as e:
        logger.debug(f"Error converting {value} to float: {e}")
        return default

def safe_bool(value: Any, default: bool = False) -> bool:
    """
    Safely convert a value to a boolean.
    
    Args:
        value: The value to convert
        default: The default value to return if conversion fails
        
    Returns:
        The boolean value or the default
    """
    if value is None:
        return default
        
    try:
        if isinstance(value, str):
            return value.lower() in ('true', 'yes', 'y', '1', 'on')
        else:
            return bool(value)
    except Exception as e:
        logger.debug(f"Error converting {value} to bool: {e}")
        return default

def safe_list(value: Any, default: Optional[List[Any]] = None) -> List[Any]:
    """
    Safely convert a value to a list.
    
    Args:
        value: The value to convert
        default: The default value to return if conversion fails
        
    Returns:
        The list value or the default
    """
    if default is None:
        default = []
        
    if value is None:
        return default
        
    try:
        if isinstance(value, list):
            return value
        elif isinstance(value, tuple):
            return list(value)
        elif isinstance(value, dict):
            return list(value.items())
        elif isinstance(value, (str, bytes)):
            # Don't convert strings to lists of characters
            return [value]
        else:
            # Try to convert to list if iterable
            try:
                return list(value)
            except:
                return [value]
    except Exception as e:
        logger.debug(f"Error converting {value} to list: {e}")
        return default

def safe_dict(value: Any, default: Optional[Dict[Any, Any]] = None) -> Dict[Any, Any]:
    """
    Safely convert a value to a dictionary.
    
    Args:
        value: The value to convert
        default: The default value to return if conversion fails
        
    Returns:
        The dictionary value or the default
    """
    if default is None:
        default = {}
        
    if value is None:
        return default
        
    try:
        if isinstance(value, dict):
            return value
        elif hasattr(value, '_asdict'):  # namedtuple support
            return value._asdict()
        elif hasattr(value, '__dict__'):  # class instance support
            return value.__dict__
        elif isinstance(value, (list, tuple)):
            # Try to convert list of pairs to dict
            try:
                return dict(value)
            except:
                return {i: v for i, v in enumerate(value)}
        else:
            # If all else fails, try direct conversion
            return dict(value)
    except Exception as e:
        logger.debug(f"Error converting {value} to dict: {e}")
        return default

def safe_function_call(func: Callable[..., T], *args, default: Optional[T] = None, **kwargs) -> Optional[T]:
    """
    Safely call a function with error handling.
    
    Args:
        func: The function to call
        *args: Positional arguments to pass to the function
        default: The default value to return if the function call fails
        **kwargs: Keyword arguments to pass to the function
        
    Returns:
        The function result or the default
    """
    if func is None:
        return default
        
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logger.error(f"Error calling function {func.__name__}: {e}")
        logger.debug(traceback.format_exc())
        return default

def validate_type(value: Any, expected_type: Type[T]) -> bool:
    """
    Validate that a value is of the expected type.
    
    Args:
        value: The value to validate
        expected_type: The expected type
        
    Returns:
        Whether the value is of the expected type
    """
    if value is None:
        return expected_type is type(None)
        
    try:
        if expected_type is Any:
            return True
            
        # Handle Union types
        try:
            origin = getattr(expected_type, '__origin__', None)
            if origin is Union:
                args = getattr(expected_type, '__args__', ())
                return any(validate_type(value, arg) for arg in args)
        except:
            pass
            
        # Handle List, Dict, etc.
        try:
            if expected_type == List:
                return isinstance(value, list)
            elif expected_type == Dict:
                return isinstance(value, dict)
            elif expected_type == Tuple:
                return isinstance(value, tuple)
        except:
            pass
            
        return isinstance(value, expected_type)
    except Exception as e:
        logger.debug(f"Error validating type: {e}")
        return False

def validate_func_args(func: Callable, *args, **kwargs) -> Tuple[bool, Optional[str]]:
    """
    Validate function arguments against the function's signature.
    
    Args:
        func: The function to validate arguments for
        *args: Positional arguments to validate
        **kwargs: Keyword arguments to validate
        
    Returns:
        A tuple of (is_valid, error_message)
    """
    if func is None:
        return False, "Function is None"
        
    try:
        sig = inspect.signature(func)
        try:
            # This will raise if the arguments don't match the signature
            sig.bind(*args, **kwargs)
            return True, None
        except Exception as bind_err:
            return False, str(bind_err)
    except Exception as e:
        logger.debug(f"Error validating function arguments: {e}")
        return False, f"Error validating function arguments: {e}"