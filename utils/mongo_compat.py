"""
MongoDB Compatibility Module

This module provides compatibility utilities for MongoDB,
specifically focused on serialization and deserialization of MongoDB objects.
"""

import json
import logging
import datetime
from typing import Any, Dict, List, Optional, Union, Set, TypeVar, Type, cast

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Try to import bson
try:
    from bson import ObjectId
    from bson.json_util import dumps as bson_dumps, loads as bson_loads
    HAS_BSON = True
except ImportError:
    HAS_BSON = False
    logger.warning("Failed to import BSON. Using fallback ObjectId implementation.")
    
    # Create fallback ObjectId
    class ObjectId:
        """Fallback ObjectId implementation for when BSON is not available."""
        
        def __init__(self, id_str=None):
            self.id = id_str or "000000000000000000000000"
            
        def __str__(self):
            return self.id
            
        def __repr__(self):
            return f"ObjectId('{self.id}')"
            
        def __eq__(self, other):
            if isinstance(other, ObjectId):
                return self.id == other.id
            return False
            
        def __hash__(self):
            return hash(self.id)

# Custom JSON encoder for MongoDB objects
class MongoJSONEncoder(json.JSONEncoder):
    """
    Custom JSON encoder for MongoDB objects.
    
    This encoder handles MongoDB-specific types like ObjectId and datetime.
    """
    
    def default(self, obj: Any) -> Any:
        """
        Convert MongoDB objects to JSON serializable types.
        
        Args:
            obj: The object to convert
            
        Returns:
            A JSON serializable representation of the object
        """
        if isinstance(obj, ObjectId):
            return str(obj)
        elif isinstance(obj, datetime.datetime):
            return obj.isoformat()
        elif isinstance(obj, datetime.date):
            return obj.isoformat()
        elif isinstance(obj, set):
            return list(obj)
        return super().default(obj)

# Serialization functions
def serialize_document(document: Dict[str, Any]) -> Dict[str, Any]:
    """
    Serialize a MongoDB document for storage.
    
    Args:
        document: The document to serialize
        
    Returns:
        The serialized document
    """
    if document is None:
        return {}
        
    # Create a copy of the document to avoid modifying the original
    serialized = {}
    
    # Serialize each field
    for key, value in document.items():
        # Skip None values
        if value is None:
            continue
            
        # Serialize based on type
        if isinstance(value, dict):
            serialized[key] = serialize_document(value)
        elif isinstance(value, list):
            serialized[key] = [serialize_value(item) for item in value]
        else:
            serialized[key] = serialize_value(value)
            
    return serialized

def serialize_value(value: Any) -> Any:
    """
    Serialize a value for MongoDB storage.
    
    Args:
        value: The value to serialize
        
    Returns:
        The serialized value
    """
    if value is None:
        return None
    elif isinstance(value, dict):
        return serialize_document(value)
    elif isinstance(value, list):
        return [serialize_value(item) for item in value]
    elif isinstance(value, str) and value.startswith('ObjectId(') and value.endswith(')'):
        # Handle string representation of ObjectId
        id_str = value[9:-1].strip("'\"")
        return ObjectId(id_str)
    elif isinstance(value, (int, float, str, bool)):
        # Basic types need no conversion
        return value
    elif isinstance(value, ObjectId):
        # ObjectId is already supported by MongoDB
        return value
    elif isinstance(value, datetime.datetime):
        # Datetime is already supported by MongoDB
        return value
    elif isinstance(value, datetime.date):
        # Convert date to datetime
        return datetime.datetime.combine(value, datetime.time())
    elif isinstance(value, set):
        # Convert set to list
        return list(value)
    else:
        # Try to convert to string as fallback
        try:
            return str(value)
        except Exception:
            logger.warning(f"Could not serialize value of type {type(value)}")
            return None

def deserialize_document(document: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deserialize a MongoDB document from storage.
    
    Args:
        document: The document to deserialize
        
    Returns:
        The deserialized document
    """
    if document is None:
        return {}
        
    # Create a copy of the document to avoid modifying the original
    deserialized = {}
    
    # Deserialize each field
    for key, value in document.items():
        # Skip None values
        if value is None:
            continue
            
        # Special handling for _id field as ObjectId
        if key == '_id' and not isinstance(value, ObjectId):
            try:
                deserialized[key] = ObjectId(str(value))
                continue
            except Exception:
                pass
                
        # Deserialize based on type
        if isinstance(value, dict):
            deserialized[key] = deserialize_document(value)
        elif isinstance(value, list):
            deserialized[key] = [deserialize_value(item) for item in value]
        else:
            deserialized[key] = deserialize_value(value)
            
    return deserialized

def deserialize_value(value: Any) -> Any:
    """
    Deserialize a value from MongoDB storage.
    
    Args:
        value: The value to deserialize
        
    Returns:
        The deserialized value
    """
    if value is None:
        return None
    elif isinstance(value, dict):
        return deserialize_document(value)
    elif isinstance(value, list):
        return [deserialize_value(item) for item in value]
    elif isinstance(value, str) and len(value) == 24 and all(c in '0123456789abcdef' for c in value.lower()):
        # This might be an ObjectId stored as string
        try:
            return ObjectId(value)
        except Exception:
            return value
    elif isinstance(value, str) and 'T' in value and value.count('-') == 2:
        # This might be a datetime stored as ISO format string
        try:
            return datetime.datetime.fromisoformat(value)
        except Exception:
            return value
    else:
        # Return as is
        return value

# Convenience functions
def to_json(document: Dict[str, Any]) -> str:
    """
    Convert a MongoDB document to JSON.
    
    Args:
        document: The document to convert
        
    Returns:
        JSON string representation of the document
    """
    if HAS_BSON:
        try:
            # Try using bson's json_util
            return bson_dumps(document)
        except Exception:
            pass
            
    # Fallback to custom encoder
    return json.dumps(document, cls=MongoJSONEncoder)

def from_json(json_str: str) -> Dict[str, Any]:
    """
    Convert a JSON string to a MongoDB document.
    
    Args:
        json_str: The JSON string to convert
        
    Returns:
        MongoDB document from the JSON string
    """
    if HAS_BSON:
        try:
            # Try using bson's json_util
            return bson_loads(json_str)
        except Exception:
            pass
            
    # Fallback to regular json.loads and manual deserialization
    raw_doc = json.loads(json_str)
    return deserialize_document(raw_doc)

# Export for easy importing
__all__ = [
    'ObjectId', 'MongoJSONEncoder',
    'serialize_document', 'deserialize_document',
    'serialize_value', 'deserialize_value',
    'to_json', 'from_json'
]