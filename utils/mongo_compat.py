"""
MongoDB Compatibility Utilities

This module provides compatibility utilities for working with MongoDB across different
versions and drivers, particularly focusing on BSON data types like DateTime.
"""

import logging
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Union, Type

logger = logging.getLogger(__name__)

# Common BSON type names for identification
_DATETIME_TYPE_NAMES = ["datetime", "ISODate", "date"]

def is_bson_datetime(value: Any) -> bool:
    """Check if a value is or represents a BSON datetime

    Args:
        value: The value to check

    Returns:
        bool: True if the value is or represents a BSON datetime
    """
    # Check for Python datetime 
    if isinstance(value, datetime):
        return True
        
    # Check for various MongoDB BSON datetime representations
    if isinstance(value, dict) and "$date" in value:
        return True
        
    # Check for class name hinting at datetime
    if hasattr(value, "__class__") and hasattr(value.__class__, "__name__"):
        class_name = value.__class__.__name__.lower()
        return any(dt_name in class_name for dt_name in _DATETIME_TYPE_NAMES)
        
    return False

def safe_convert_to_datetime(value: Any) -> datetime:
    """Convert a value to a Python datetime object with compatibility handling

    Args:
        value: The value to convert (BSON datetime, dict with $date, etc.)

    Returns:
        datetime: Converted Python datetime object
    """
    # If it's already a datetime, just return it
    if isinstance(value, datetime):
        return value
        
    # Handle dict representation with $date (common in extended JSON)
    if isinstance(value, dict) and "$date" in value:
        date_value = value["$date"]
        
        # Handle $date as milliseconds timestamp
        if isinstance(date_value, (int, float)):
            return datetime.fromtimestamp(date_value / 1000.0)
            
        # Handle $date as ISO string
        if isinstance(date_value, str):
            return datetime.fromisoformat(date_value.replace("Z", "+00:00"))
    
    # Attempt to extract timestamp if it has a timestamp attribute/method
    if hasattr(value, "timestamp"):
        if callable(value.timestamp):
            return datetime.fromtimestamp(value.timestamp())
        return datetime.fromtimestamp(value.timestamp)
    
    # Try extracting datetime representation from object attributes
    for attr in ["datetime", "date", "time", "value"]:
        if hasattr(value, attr):
            attr_value = getattr(value, attr)
            if isinstance(attr_value, datetime):
                return attr_value
            elif isinstance(attr_value, (int, float)):
                return datetime.fromtimestamp(attr_value / 1000.0)
    
    # Last resort, convert to string and parse
    try:
        if hasattr(value, "__str__"):
            str_value = str(value)
            return datetime.fromisoformat(str_value.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        pass
        
    # If all else fails, return current time and log warning
    logger.warning(f"Could not convert {value} ({type(value)}) to datetime, using current time instead")
    return datetime.now()

def safe_serialize_for_mongodb(data: Any) -> Any:
    """Safely serialize data for MongoDB storage, handling special types

    Args:
        data: The data to serialize

    Returns:
        Any: Properly serialized data for MongoDB storage
    """
    if data is None:
        return None
        
    # Handle common collection types
    if isinstance(data, list):
        return [safe_serialize_for_mongodb(item) for item in data]
        
    if isinstance(data, dict):
        return {k: safe_serialize_for_mongodb(v) for k, v in data.items()}
        
    # Handle datetime specifically
    if isinstance(data, datetime):
        return data  # MongoDB driver will handle this correctly
        
    # Handle objects with standard serialization methods
    if hasattr(data, "to_dict"):
        return safe_serialize_for_mongodb(data.to_dict())
        
    if hasattr(data, "__dict__"):
        return safe_serialize_for_mongodb(data.__dict__)
        
    # Return primitive types as-is (MongoDB can store them directly)
    if isinstance(data, (str, int, float, bool)):
        return data
        
    # Convert anything else to string
    return str(data)

def safe_deserialize_from_mongodb(data: Any) -> Any:
    """Safely deserialize data from MongoDB, handling special types

    Args:
        data: The data from MongoDB to deserialize

    Returns:
        Any: Properly deserialized data
    """
    if data is None:
        return None
        
    # Handle BSON datetime type
    if is_bson_datetime(data):
        return safe_convert_to_datetime(data)
        
    # Handle common collection types
    if isinstance(data, list):
        return [safe_deserialize_from_mongodb(item) for item in data]
        
    if isinstance(data, dict):
        # Special case for datetime extended JSON
        if "$date" in data and len(data) == 1:
            return safe_convert_to_datetime(data)
            
        # Regular dictionary processing
        return {k: safe_deserialize_from_mongodb(v) for k, v in data.items()}
        
    # Return primitive types as-is
    return data