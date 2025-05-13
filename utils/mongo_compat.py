"""
MongoDB Compatibility Module

This module provides compatibility functions for working with MongoDB documents,
including serialization, deserialization, and ObjectId handling.
"""

import json
import logging
import datetime
from typing import Any, Dict, List, Optional, Tuple, Union, TypeVar, cast

# Import safely to handle different pymongo versions
try:
    from bson import ObjectId, json_util
    from bson.json_util import dumps as bson_dumps
    from bson.json_util import loads as bson_loads
except ImportError:
    # Fallbacks for missing bson module
    # Define a minimal compatible ObjectId class
    class ObjectId:
        def __init__(self, id_str=None):
            self.id_str = id_str or "000000000000000000000000"
            
        def __str__(self):
            return self.id_str
            
        def __repr__(self):
            return f"ObjectId('{self.id_str}')"
            
    # Minimal json_util replacements
    bson_dumps = json.dumps
    bson_loads = json.loads

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MongoJSONEncoder(json.JSONEncoder):
    """JSON encoder that can handle MongoDB-specific types."""
    
    def default(self, obj):
        # Handle ObjectId
        if isinstance(obj, ObjectId):
            return str(obj)
            
        # Handle datetime
        if isinstance(obj, datetime.datetime):
            return {
                "$date": obj.isoformat()
            }
            
        # Let the parent class handle it
        return super().default(obj)

def is_objectid(value: Any) -> bool:
    """
    Check if a value is an ObjectId.
    
    Args:
        value: The value to check
        
    Returns:
        Whether the value is an ObjectId
    """
    if value is None:
        return False
        
    return isinstance(value, ObjectId)

def to_object_id(id_value: Any) -> Optional[Any]:
    """
    Convert a value to an ObjectId.
    
    Args:
        id_value: The value to convert
        
    Returns:
        The ObjectId or None if conversion fails
    """
    if id_value is None:
        return None
        
    if is_objectid(id_value):
        return id_value
        
    try:
        return ObjectId(str(id_value))
    except Exception as e:
        logger.debug(f"Error converting to ObjectId: {e}")
        return None

def is_bson_datetime(value: Any) -> bool:
    """
    Check if a value is a BSON datetime.
    
    Args:
        value: The value to check
        
    Returns:
        Whether the value is a BSON datetime
    """
    if not isinstance(value, dict):
        return False
        
    return "$date" in value and len(value) == 1

def safe_convert_to_datetime(value: Any) -> Optional[datetime.datetime]:
    """
    Safely convert a value to a datetime.
    
    Args:
        value: The value to convert
        
    Returns:
        The datetime or None if conversion fails
    """
    if value is None:
        return None
        
    if isinstance(value, datetime.datetime):
        return value
        
    if isinstance(value, dict) and "$date" in value:
        try:
            date_str = value["$date"]
            if isinstance(date_str, str):
                return datetime.datetime.fromisoformat(date_str)
        except Exception as e:
            logger.debug(f"Error converting to datetime: {e}")
            
    if isinstance(value, str):
        try:
            return datetime.datetime.fromisoformat(value)
        except Exception as e:
            logger.debug(f"Error converting string to datetime: {e}")
            
    if isinstance(value, (int, float)):
        try:
            return datetime.datetime.fromtimestamp(value)
        except Exception as e:
            logger.debug(f"Error converting timestamp to datetime: {e}")
            
    return None

def handle_datetime(value: Any) -> Any:
    """
    Handle datetime values for MongoDB compatibility.
    
    Args:
        value: The value to handle
        
    Returns:
        The handled value
    """
    if isinstance(value, datetime.datetime):
        return value
        
    return safe_convert_to_datetime(value)

def serialize_document(document: Dict[str, Any], convert_objectids: bool = True) -> Dict[str, Any]:
    """
    Serialize a document for MongoDB storage.
    
    Args:
        document: The document to serialize
        convert_objectids: Whether to convert string IDs to ObjectIds
        
    Returns:
        The serialized document
    """
    if document is None:
        return {}
        
    result = {}
    
    for key, value in document.items():
        # Handle ObjectId fields specially
        if key == "_id" and convert_objectids and value is not None and not is_objectid(value):
            result[key] = to_object_id(value)
        # Handle nested dictionaries
        elif isinstance(value, dict):
            result[key] = serialize_document(value, convert_objectids)
        # Handle lists
        elif isinstance(value, list):
            result[key] = [
                serialize_document(item, convert_objectids) if isinstance(item, dict) else item
                for item in value
            ]
        # Handle datetime
        elif isinstance(value, datetime.datetime):
            result[key] = value
        # Other values pass through
        else:
            result[key] = value
            
    return result

def deserialize_document(document: Dict[str, Any], convert_objectids: bool = True) -> Dict[str, Any]:
    """
    Deserialize a document from MongoDB storage.
    
    Args:
        document: The document to deserialize
        convert_objectids: Whether to convert ObjectIds to strings
        
    Returns:
        The deserialized document
    """
    if document is None:
        return {}
        
    result = {}
    
    for key, value in document.items():
        # Handle ObjectId fields specially
        if convert_objectids and is_objectid(value):
            result[key] = str(value)
        # Handle BSON datetime
        elif is_bson_datetime(value):
            result[key] = safe_convert_to_datetime(value)
        # Handle nested dictionaries
        elif isinstance(value, dict):
            result[key] = deserialize_document(value, convert_objectids)
        # Handle lists
        elif isinstance(value, list):
            result[key] = [
                deserialize_document(item, convert_objectids) if isinstance(item, dict) else item
                for item in value
            ]
        # Other values pass through
        else:
            result[key] = value
            
    return result

def filter_document(document: Dict[str, Any], fields: List[str]) -> Dict[str, Any]:
    """
    Filter a document to include only specified fields.
    
    Args:
        document: The document to filter
        fields: The fields to include
        
    Returns:
        The filtered document
    """
    if document is None:
        return {}
        
    return {
        key: value for key, value in document.items()
        if key in fields
    }

def safe_serialize_for_mongodb(data: Any) -> Any:
    """
    Safely serialize data for MongoDB storage.
    
    Args:
        data: The data to serialize
        
    Returns:
        The serialized data
    """
    if data is None:
        return None
        
    try:
        if isinstance(data, dict):
            return serialize_document(data)
        elif isinstance(data, list):
            return [serialize_document(item) if isinstance(item, dict) else item for item in data]
        else:
            # Attempt to serialize through JSON
            json_str = json.dumps(data, cls=MongoJSONEncoder)
            parsed = json.loads(json_str)
            return serialize_document(parsed) if isinstance(parsed, dict) else parsed
    except Exception as e:
        logger.error(f"Error serializing for MongoDB: {e}")
        # Return the original data as a fallback
        return data

def safe_deserialize_from_mongodb(data: Any) -> Any:
    """
    Safely deserialize data from MongoDB storage.
    
    Args:
        data: The data to deserialize
        
    Returns:
        The deserialized data
    """
    if data is None:
        return None
        
    try:
        if isinstance(data, dict):
            return deserialize_document(data)
        elif isinstance(data, list):
            return [deserialize_document(item) if isinstance(item, dict) else item for item in data]
        else:
            # Try to serialize and then deserialize through bson
            if bson_dumps and bson_loads:
                json_str = bson_dumps(data)
                parsed = bson_loads(json_str)
                return deserialize_document(parsed) if isinstance(parsed, dict) else parsed
            else:
                # Fallback to regular JSON
                json_str = json.dumps(data, cls=MongoJSONEncoder)
                return json.loads(json_str)
    except Exception as e:
        logger.error(f"Error deserializing from MongoDB: {e}")
        # Return the original data as a fallback
        return data