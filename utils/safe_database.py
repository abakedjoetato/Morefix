"""
Safe Database Access Utilities

This module provides utilities for safely accessing MongoDB data with proper
error handling, type checking, and consistent patterns.
"""

import logging
import asyncio
from typing import Any, Dict, List, Optional, Union, TypeVar, Generic, cast

logger = logging.getLogger(__name__)

# Type variables for generic function annotations
T = TypeVar('T')
D = TypeVar('D', bound=Dict[str, Any])

# For class-based pattern
class SafeDocument:
    """Wrapper for MongoDB documents with safe access methods"""
    
    def __init__(self, document: Optional[Dict[str, Any]] = None):
        self.document = document or {}
    
    def get(self, key: str, default: Any = None) -> Any:
        """Safely get a value from the document"""
        return safe_get(self.document, key, default)
    
    def get_nested(self, path: str, default: Any = None) -> Any:
        """Safely get a nested value from the document"""
        return safe_get_nested(self.document, path, default)
    
    def has_field(self, key: str) -> bool:
        """Check if document has a field"""
        return key in self.document
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return self.document

def safe_get(data: Optional[Dict[str, Any]], key: str, default: T = None) -> Optional[T]:
    """
    Safely get a value from a dictionary with proper error handling
    
    Args:
        data: Dictionary to retrieve value from
        key: Dictionary key to access
        default: Default value to return if key doesn't exist
        
    Returns:
        Value from the dictionary or default if key doesn't exist or dict is None
    """
    if data is None:
        return default
    
    try:
        return data.get(key, default)
    except (AttributeError, KeyError):
        logger.debug(f"Failed to access key '{key}' in dictionary")
        return default

def safe_get_nested(data: Optional[Dict[str, Any]], path: str, default: Any = None, 
                    delimiter: str = '.') -> Any:
    """
    Safely get a nested value from a dictionary using a dot-notation path
    
    Args:
        data: Dictionary to retrieve value from
        path: Dot-notation path to the value (e.g., 'user.profile.name')
        default: Default value to return if path doesn't exist
        delimiter: Delimiter to use for path segments (default: '.')
        
    Returns:
        Value from the nested path or default if path doesn't exist
    """
    if data is None:
        return default
    
    keys = path.split(delimiter)
    result = data
    
    try:
        for key in keys:
            if not isinstance(result, dict):
                return default
            
            result = result.get(key)
            if result is None:
                return default
        
        return result
    except (AttributeError, KeyError):
        logger.debug(f"Failed to access nested path '{path}' in dictionary")
        return default

def is_db_available(db):
    """
    Check if database connection is available and ready to use
    
    Args:
        db: MongoDB database instance
        
    Returns:
        bool: True if database is available, False otherwise
    """
    if db is None:
        return False
    
    try:
        # Lightweight check that doesn't require a server round-trip
        return hasattr(db, 'client') and hasattr(db, 'name')
    except (AttributeError, Exception) as e:
        logger.error(f"Database availability check failed: {e}")
        return False

async def get_document_safely(collection, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Safely retrieve a document from a MongoDB collection with error handling
    
    Args:
        collection: MongoDB collection to query
        query: Query dictionary to find the document
        
    Returns:
        Document dict or None if not found or error occurs
    """
    if collection is None:
        return None
    
    try:
        return await collection.find_one(query)
    except Exception as e:
        logger.error(f"Error retrieving document: {e}")
        return None

def document_exists(document: Optional[Dict[str, Any]]) -> bool:
    """
    Safely check if a document exists and is not empty
    
    Args:
        document: Document to check
        
    Returns:
        bool: True if document exists and is not empty, False otherwise
    """
    return document is not None and len(document) > 0

async def safely_update_document(collection, query: Dict[str, Any], 
                                update: Dict[str, Any], upsert: bool = False) -> bool:
    """
    Safely update a document in a MongoDB collection with error handling
    
    Args:
        collection: MongoDB collection to update
        query: Query to find the document to update
        update: Update operation to apply
        upsert: Whether to insert if document doesn't exist
        
    Returns:
        bool: True if update was successful, False otherwise
    """
    if collection is None:
        return False
    
    try:
        result = await collection.update_one(query, update, upsert=upsert)
        # Check if acknowledged and at least one document was modified
        return result.acknowledged and (result.modified_count > 0 or 
                                        (upsert and result.upserted_id is not None))
    except Exception as e:
        logger.error(f"Error updating document: {e}")
        return False

async def count_documents_safely(collection, query: Dict[str, Any]) -> int:
    """
    Safely count documents in a MongoDB collection with error handling
    
    Args:
        collection: MongoDB collection to query
        query: Query to count matching documents
        
    Returns:
        int: Count of matching documents or 0 if error occurs
    """
    if collection is None:
        return 0
    
    try:
        return await collection.count_documents(query)
    except Exception as e:
        logger.error(f"Error counting documents: {e}")
        return 0

async def find_documents_safely(collection, query: Dict[str, Any], 
                              limit: int = 0, sort=None) -> List[Dict[str, Any]]:
    """
    Safely find documents in a MongoDB collection with error handling
    
    Args:
        collection: MongoDB collection to query
        query: Query to find matching documents
        limit: Maximum number of documents to return (0 for no limit)
        sort: Sort specification
        
    Returns:
        List of matching documents or empty list if error occurs
    """
    if collection is None:
        return []
    
    try:
        cursor = collection.find(query)
        
        if sort is not None:
            cursor = cursor.sort(sort)
        
        if limit > 0:
            cursor = cursor.limit(limit)
        
        return await cursor.to_list(length=None)
    except Exception as e:
        logger.error(f"Error finding documents: {e}")
        return []

# Enhanced safe database access functions
async def safe_get_db(db_instance, db_name: Optional[str] = None):
    """
    Safely get a database instance with error handling
    
    Args:
        db_instance: MongoDB client instance
        db_name: Name of the database to access
        
    Returns:
        Database instance or None if error occurs
    """
    if db_instance is None:
        logger.warning("Database instance is None in safe_get_db")
        return None
        
    try:
        # Get the database by name if provided
        if db_name is not None:
            return db_instance[db_name]
            
        # Try common methods to get a default database
        if hasattr(db_instance, 'get_default_database'):
            return db_instance.get_default_database()
            
        if hasattr(db_instance, 'defaultDb') and db_instance.defaultDb is not None:
            return db_instance.defaultDb
        
        # Try to get the database name from the connection string
        if hasattr(db_instance, 'address') and '/' in db_instance.address:
            # Parse the connection string to extract database name
            db_name_from_uri = db_instance.address.split('/')[-1].split('?')[0]
            if db_name_from_uri:
                return db_instance[db_name_from_uri]
        
        # Last resort: return the instance itself if it appears to be a database
        if hasattr(db_instance, 'collection_names') or hasattr(db_instance, 'list_collection_names'):
            return db_instance
            
        logger.warning("Could not determine database from instance")
        return db_instance  # Assume it's already a database
    except Exception as e:
        logger.error(f"Error accessing database: {e}")
        return None

async def safe_get_collection(db, collection_name: str):
    """
    Safely get a collection from a database with error handling
    
    Args:
        db: MongoDB database instance
        collection_name: Name of the collection to access
        
    Returns:
        Collection instance or None if error occurs
    """
    if db is None:
        logger.warning(f"Database is None when accessing collection {collection_name}")
        return None
        
    if not collection_name:
        logger.warning("No collection name provided")
        return None
        
    try:
        # Check if db is a motor client instead of a database
        if hasattr(db, 'get_database'):
            # It's a client, try to get default database
            try:
                default_db_name = db.get_default_database().name
                db = db[default_db_name]
                logger.info(f"Using default database: {default_db_name}")
            except Exception as e:
                logger.error(f"Error getting default database: {e}")
                # Try a fallback name
                db = db.get_database('tower_temptation')
                logger.info("Using fallback database: tower_temptation")
        
        # Now get the collection
        return db[collection_name]
    except Exception as e:
        logger.error(f"Error accessing collection {collection_name}: {e}")
        return None

async def safe_find_one(collection, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Safely find a single document with error handling
    
    Args:
        collection: MongoDB collection
        query: Query to find the document
        
    Returns:
        Document dict or None if not found or error occurs
    """
    return await get_document_safely(collection, query)

async def safe_update_one(collection, query: Dict[str, Any], update: Dict[str, Any], 
                        upsert: bool = False) -> bool:
    """
    Safely update a document with error handling
    
    Args:
        collection: MongoDB collection
        query: Query to find the document
        update: Update operation
        upsert: Whether to insert if document doesn't exist
        
    Returns:
        True if successful, False otherwise
    """
    return await safely_update_document(collection, query, update, upsert=upsert)

async def safe_insert_one(collection, document: Dict[str, Any]) -> Optional[str]:
    """
    Safely insert a document with error handling
    
    Args:
        collection: MongoDB collection
        document: Document to insert
        
    Returns:
        ID of inserted document or None if error occurs
    """
    if collection is None:
        return None
    
    try:
        result = await collection.insert_one(document)
        return str(result.inserted_id) if result.inserted_id else None
    except Exception as e:
        logger.error(f"Error inserting document: {e}")
        return None

async def safe_count_documents(collection, query: Dict[str, Any]) -> int:
    """
    Safely count documents with error handling
    
    Args:
        collection: MongoDB collection
        query: Query to count matching documents
        
    Returns:
        Count of matching documents or 0 if error occurs
    """
    return await count_documents_safely(collection, query)

def safe_get_document_field(document: Optional[Dict[str, Any]], field: str, 
                           default: Any = None) -> Any:
    """
    Safely get a field from a document with error handling
    
    Args:
        document: Document dict
        field: Field name to access
        default: Default value if field doesn't exist
        
    Returns:
        Field value or default if not found
    """
    return safe_get(document, field, default)

def safe_document_to_dict(document: Any) -> Dict[str, Any]:
    """
    Safely convert a MongoDB document to a dictionary
    
    Args:
        document: MongoDB document or document-like object
        
    Returns:
        Dictionary representation of the document
    """
    if document is None:
        return {}
    
    if isinstance(document, dict):
        return document
    
    if hasattr(document, 'to_dict'):
        return document.to_dict()
        
    if hasattr(document, '__dict__'):
        return document.__dict__
    
    logger.warning(f"Unable to convert document of type {type(document)} to dict")
    return {}

def has_field(document: Optional[Dict[str, Any]], field: str) -> bool:
    """
    Check if a document has a field
    
    Args:
        document: Document dict
        field: Field name to check
        
    Returns:
        True if field exists, False otherwise
    """
    if document is None:
        return False
    
    return field in document

def get_field_with_type_check(data: Optional[Dict[str, Any]], key: str, 
                            expected_type: type, default: T) -> T:
    """
    Get a field from a dictionary with type checking
    
    Args:
        data: Dictionary to retrieve value from
        key: Dictionary key to access
        expected_type: Expected type of the value
        default: Default value to return if key doesn't exist or type doesn't match
        
    Returns:
        Value from the dictionary if it exists and has the expected type, default otherwise
    """
    if data is None:
        return default
    
    try:
        value = data.get(key)
        
        # If value doesn't exist, return default
        if value is None:
            return default
        
        # If value is not of expected type, log warning and return default
        if not isinstance(value, expected_type):
            logger.warning(f"Field '{key}' has unexpected type: {type(value)}, expected: {expected_type}")
            return default
        
        return value
    except Exception:
        return default