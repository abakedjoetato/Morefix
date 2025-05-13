"""
Safe MongoDB Module

This module provides safe operations for MongoDB with proper error handling
and compatibility between different MongoDB/Motor versions.
"""

import logging
import sys
import types
import asyncio
import inspect
from typing import Any, Dict, List, Optional, Tuple, Union, TypeVar, Generic, cast
from dataclasses import dataclass, field

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global variables
_mongodb_client = None
_mongodb_db = None

# Type variables
T = TypeVar('T')
R = TypeVar('R')

# Try to import motor and pymongo
try:
    import motor
    import motor.motor_asyncio
    import pymongo
    from pymongo.results import InsertOneResult, UpdateResult, DeleteResult
    from pymongo.cursor import Cursor
    from bson import ObjectId
    HAS_MOTOR = True
except ImportError:
    HAS_MOTOR = False
    logger.error("Failed to import Motor or PyMongo. MongoDB functionality will not be available.")
    # Create mock modules if motor is not available
    motor = types.ModuleType('motor')
    motor.motor_asyncio = types.ModuleType('motor.motor_asyncio')
    pymongo = types.ModuleType('pymongo')
    pymongo.results = types.ModuleType('pymongo.results')
    pymongo.cursor = types.ModuleType('pymongo.cursor')
    
    # Create essential mock classes
    class MockObjectId:
        def __init__(self, id_str=None):
            self.id = id_str or "000000000000000000000000"
            
        def __str__(self):
            return self.id
            
        def __repr__(self):
            return f"ObjectId('{self.id}')"
            
    class MockResult:
        def __init__(self, acknowledged=True, **kwargs):
            self.acknowledged = acknowledged
            for key, value in kwargs.items():
                setattr(self, key, value)
                
    # Add mock classes to modules
    setattr(pymongo.results, 'InsertOneResult', MockResult)
    setattr(pymongo.results, 'UpdateResult', MockResult)
    setattr(pymongo.results, 'DeleteResult', MockResult)
    
    # Create ObjectId class
    ObjectId = MockObjectId

# Import MongoDB compatibility utilities if available
try:
    from utils.mongo_compat import serialize_document, deserialize_document
    HAS_COMPAT = True
except ImportError:
    HAS_COMPAT = False
    
    # Create simple serialization functions as fallback
    def serialize_document(document: Dict[str, Any]) -> Dict[str, Any]:
        """Simple document serialization fallback."""
        return document
        
    def deserialize_document(document: Dict[str, Any]) -> Dict[str, Any]:
        """Simple document deserialization fallback."""
        return document

class SafeMongoDBResult(Generic[T]):
    """
    A safe wrapper for MongoDB operation results with proper error handling.
    
    This class provides a consistent interface for accessing MongoDB operation
    results across different versions and operation types.
    
    Attributes:
        success: Whether the operation was successful
        error: The error that occurred during the operation (if any)
        result: The raw operation result
        value: The value of the operation (e.g., inserted_id, modified_count)
    """
    
    def __init__(self, 
                result: Optional[Any] = None, 
                error: Optional[Exception] = None,
                value: Optional[Any] = None):
        """
        Initialize a SafeMongoDBResult.
        
        Args:
            result: The raw operation result
            error: The error that occurred during the operation
            value: The value of the operation
        """
        self.success = error is None
        self.error = error
        self.result = result
        self._value = value
        
        # Determine result type and extract appropriate value if not provided
        if self.success and result is not None and value is None:
            if hasattr(result, 'inserted_id'):
                self._value = result.inserted_id
            elif hasattr(result, 'modified_count'):
                self._value = result.modified_count
            elif hasattr(result, 'deleted_count'):
                self._value = result.deleted_count
            elif hasattr(result, 'upserted_id'):
                self._value = result.upserted_id
            elif isinstance(result, list):
                self._value = result
            elif isinstance(result, dict):
                self._value = result
            else:
                self._value = result
    
    @property
    def value(self) -> Any:
        """Get the value of the operation."""
        return self._value
        
    @property
    def inserted_id(self) -> Any:
        """Get the inserted document ID (for insert operations)."""
        if hasattr(self.result, 'inserted_id'):
            return self.result.inserted_id
        return None
        
    @property
    def modified_count(self) -> int:
        """Get the number of modified documents (for update operations)."""
        if hasattr(self.result, 'modified_count'):
            return self.result.modified_count
        return 0
        
    @property
    def deleted_count(self) -> int:
        """Get the number of deleted documents (for delete operations)."""
        if hasattr(self.result, 'deleted_count'):
            return self.result.deleted_count
        return 0
        
    @property
    def upserted_id(self) -> Any:
        """Get the upserted document ID (for update operations with upsert)."""
        if hasattr(self.result, 'upserted_id'):
            return self.result.upserted_id
        return None
        
    @property
    def acknowledged(self) -> bool:
        """Get whether the operation was acknowledged by the server."""
        if hasattr(self.result, 'acknowledged'):
            return self.result.acknowledged
        return self.success
        
    def __bool__(self) -> bool:
        """Convert to boolean (True if successful)."""
        return self.success
        
    def __len__(self) -> int:
        """Get the length of the result (for list results)."""
        if isinstance(self._value, list):
            return len(self._value)
        elif hasattr(self._value, '__len__'):
            return len(self._value)
        return 0
        
    def __getitem__(self, key: Any) -> Any:
        """Get an item from the result value."""
        if isinstance(self._value, (list, dict)):
            return self._value[key]
        elif hasattr(self._value, '__getitem__'):
            return self._value[key]
        raise TypeError(f"Result value of type {type(self._value)} does not support indexing")
        
    def __iter__(self):
        """Iterate over the result value."""
        if isinstance(self._value, (list, dict)):
            return iter(self._value)
        elif hasattr(self._value, '__iter__'):
            return iter(self._value)
        raise TypeError(f"Result value of type {type(self._value)} is not iterable")
    
    def __str__(self) -> str:
        """Convert to string."""
        if self.success:
            return f"Success: {self._value}"
        return f"Error: {self.error}"
        
    def __repr__(self) -> str:
        """Convert to representation string."""
        if self.success:
            return f"SafeMongoDBResult(success=True, value={self._value!r})"
        return f"SafeMongoDBResult(success=False, error={self.error!r})"
    
    # Make SafeMongoDBResult awaitable by implementing __await__
    def __await__(self):
        """Make SafeMongoDBResult awaitable."""
        # Just return a completed future with self
        future = asyncio.get_event_loop().create_future()
        future.set_result(self)
        return future.__await__()

@dataclass
class SafeDocument:
    """
    A safe wrapper for MongoDB documents with attribute-style access.
    
    This class provides a consistent interface for accessing MongoDB document
    fields as attributes, with proper error handling and fallback values.
    
    Attributes:
        data: The raw document data
    """
    
    data: Dict[str, Any] = field(default_factory=dict)
    
    def __getattr__(self, name: str) -> Any:
        """Get an attribute from the document."""
        if name in self.data:
            return self.data[name]
        return None
        
    def __setattr__(self, name: str, value: Any) -> None:
        """Set an attribute in the document."""
        if name == 'data':
            super().__setattr__(name, value)
        else:
            self.data[name] = value
            
    def __getitem__(self, key: str) -> Any:
        """Get an item from the document."""
        return self.data.get(key)
        
    def __setitem__(self, key: str, value: Any) -> None:
        """Set an item in the document."""
        self.data[key] = value
        
    def __contains__(self, key: str) -> bool:
        """Check if the document contains a key."""
        return key in self.data
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from the document with a default."""
        return self.data.get(key, default)
        
    def keys(self) -> List[str]:
        """Get the keys in the document."""
        return list(self.data.keys())
        
    def values(self) -> List[Any]:
        """Get the values in the document."""
        return list(self.data.values())
        
    def items(self) -> List[Tuple[str, Any]]:
        """Get the items in the document."""
        return list(self.data.items())
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to a dictionary."""
        return self.data
        
    def __str__(self) -> str:
        """Convert to string."""
        return str(self.data)
        
    def __repr__(self) -> str:
        """Convert to representation string."""
        return f"SafeDocument({self.data!r})"

# Setup functions
def setup_mongodb(connection_string: str, database_name: str, **kwargs) -> bool:
    """
    Set up MongoDB client and database.
    
    Args:
        connection_string: MongoDB connection string
        database_name: Database name
        **kwargs: Additional arguments for the MongoDB client
        
    Returns:
        Whether the setup was successful
    """
    global _mongodb_client, _mongodb_db
    
    if not HAS_MOTOR:
        logger.error("Motor is not available. MongoDB functionality will not be available.")
        return False
        
    try:
        _mongodb_client = motor.motor_asyncio.AsyncIOMotorClient(connection_string, **kwargs)
        _mongodb_db = _mongodb_client[database_name]
        return True
    except Exception as e:
        logger.error(f"Failed to set up MongoDB: {e}")
        return False

def get_client() -> Any:
    """
    Get the MongoDB client.
    
    Returns:
        The MongoDB client or None if not set up
    """
    global _mongodb_client
    return _mongodb_client

def get_database() -> Any:
    """
    Get the MongoDB database.
    
    Returns:
        The MongoDB database or None if not set up
    """
    global _mongodb_db
    return _mongodb_db

def get_collection(collection_name: str) -> Any:
    """
    Get a MongoDB collection.
    
    Args:
        collection_name: Name of the collection
        
    Returns:
        The MongoDB collection or None if not set up
    """
    global _mongodb_db
    
    if _mongodb_db is None:
        logger.error("MongoDB database not set up. Call setup_mongodb first.")
        return None
        
    try:
        return _mongodb_db[collection_name]
    except Exception as e:
        logger.error(f"Failed to get collection {collection_name}: {e}")
        return None

# Safe MongoDB operations
async def find_one_document(collection_name: str, 
                           filter: Dict[str, Any],
                           projection: Optional[Dict[str, Any]] = None,
                           **kwargs) -> SafeMongoDBResult:
    """
    Find a single document in a collection safely.
    
    Args:
        collection_name: Name of the collection
        filter: Filter to apply
        projection: Projection to apply
        **kwargs: Additional arguments for find_one
        
    Returns:
        SafeMongoDBResult with the found document or error
    """
    collection = get_collection(collection_name)
    if collection is None:
        return SafeMongoDBResult(error=ValueError(f"Collection {collection_name} not found"))
        
    try:
        # Serialize filter if compatibility module is available
        if HAS_COMPAT:
            filter = serialize_document(filter)
            if projection:
                projection = serialize_document(projection)
                
        # Find the document
        document = await collection.find_one(filter, projection, **kwargs)
        
        # Deserialize document if compatibility module is available
        if document and HAS_COMPAT:
            document = deserialize_document(document)
            
        return SafeMongoDBResult(result=document, value=document)
    except Exception as e:
        logger.error(f"Error finding document in {collection_name}: {e}")
        return SafeMongoDBResult(error=e)

async def find_documents(collection_name: str,
                        filter: Dict[str, Any],
                        projection: Optional[Dict[str, Any]] = None,
                        **kwargs) -> SafeMongoDBResult:
    """
    Find documents in a collection safely.
    
    Args:
        collection_name: Name of the collection
        filter: Filter to apply
        projection: Projection to apply
        **kwargs: Additional arguments for find
        
    Returns:
        SafeMongoDBResult with the found documents or error
    """
    collection = get_collection(collection_name)
    if collection is None:
        return SafeMongoDBResult(error=ValueError(f"Collection {collection_name} not found"))
        
    try:
        # Serialize filter if compatibility module is available
        if HAS_COMPAT:
            filter = serialize_document(filter)
            if projection:
                projection = serialize_document(projection)
                
        # Find the documents
        cursor = collection.find(filter, projection, **kwargs)
        
        # Try to get documents with different to_list methods
        try:
            # Try the new to_list method with length parameter
            documents = await cursor.to_list(length=None)
        except (TypeError, AttributeError):
            try:
                # Try the old to_list method
                documents = await cursor.to_list()
            except Exception:
                # Fallback to manual iteration
                documents = []
                async for doc in cursor:
                    documents.append(doc)
                    
        # Deserialize documents if compatibility module is available
        if HAS_COMPAT:
            documents = [deserialize_document(doc) for doc in documents]
            
        return SafeMongoDBResult(result=documents, value=documents)
    except Exception as e:
        logger.error(f"Error finding documents in {collection_name}: {e}")
        return SafeMongoDBResult(error=e)

async def insert_document(collection_name: str,
                         document: Dict[str, Any],
                         **kwargs) -> SafeMongoDBResult:
    """
    Insert a document into a collection safely.
    
    Args:
        collection_name: Name of the collection
        document: Document to insert
        **kwargs: Additional arguments for insert_one
        
    Returns:
        SafeMongoDBResult with the inserted ID or error
    """
    collection = get_collection(collection_name)
    if collection is None:
        return SafeMongoDBResult(error=ValueError(f"Collection {collection_name} not found"))
        
    try:
        # Serialize document if compatibility module is available
        if HAS_COMPAT:
            document = serialize_document(document)
            
        # Insert the document
        result = await collection.insert_one(document, **kwargs)
        return SafeMongoDBResult(result=result)
    except Exception as e:
        logger.error(f"Error inserting document into {collection_name}: {e}")
        return SafeMongoDBResult(error=e)

async def update_document(collection_name: str,
                         filter: Dict[str, Any],
                         update: Dict[str, Any],
                         **kwargs) -> SafeMongoDBResult:
    """
    Update a document in a collection safely.
    
    Args:
        collection_name: Name of the collection
        filter: Filter to apply
        update: Update to apply
        **kwargs: Additional arguments for update_one
        
    Returns:
        SafeMongoDBResult with the update result or error
    """
    collection = get_collection(collection_name)
    if collection is None:
        return SafeMongoDBResult(error=ValueError(f"Collection {collection_name} not found"))
        
    try:
        # Serialize filter and update if compatibility module is available
        if HAS_COMPAT:
            filter = serialize_document(filter)
            update = serialize_document(update)
            
        # Ensure update has operators
        if not any(key.startswith('$') for key in update):
            update = {'$set': update}
            
        # Update the document
        result = await collection.update_one(filter, update, **kwargs)
        return SafeMongoDBResult(result=result)
    except Exception as e:
        logger.error(f"Error updating document in {collection_name}: {e}")
        return SafeMongoDBResult(error=e)

async def delete_document(collection_name: str,
                         filter: Dict[str, Any],
                         **kwargs) -> SafeMongoDBResult:
    """
    Delete a document from a collection safely.
    
    Args:
        collection_name: Name of the collection
        filter: Filter to apply
        **kwargs: Additional arguments for delete_one
        
    Returns:
        SafeMongoDBResult with the delete result or error
    """
    collection = get_collection(collection_name)
    if collection is None:
        return SafeMongoDBResult(error=ValueError(f"Collection {collection_name} not found"))
        
    try:
        # Serialize filter if compatibility module is available
        if HAS_COMPAT:
            filter = serialize_document(filter)
            
        # Delete the document
        result = await collection.delete_one(filter, **kwargs)
        return SafeMongoDBResult(result=result)
    except Exception as e:
        logger.error(f"Error deleting document from {collection_name}: {e}")
        return SafeMongoDBResult(error=e)

async def count_documents(collection_name: str,
                         filter: Optional[Dict[str, Any]] = None,
                         **kwargs) -> SafeMongoDBResult:
    """
    Count documents in a collection safely.
    
    Args:
        collection_name: Name of the collection
        filter: Filter to apply
        **kwargs: Additional arguments for count_documents
        
    Returns:
        SafeMongoDBResult with the count or error
    """
    collection = get_collection(collection_name)
    if collection is None:
        return SafeMongoDBResult(error=ValueError(f"Collection {collection_name} not found"))
        
    try:
        # Serialize filter if compatibility module is available
        filter = filter or {}
        if HAS_COMPAT:
            filter = serialize_document(filter)
            
        # Count the documents
        count = await collection.count_documents(filter, **kwargs)
        return SafeMongoDBResult(result=count, value=count)
    except Exception as e:
        logger.error(f"Error counting documents in {collection_name}: {e}")
        return SafeMongoDBResult(error=e)

# Helper function to create a success result
def success_result(value: Optional[Any] = None,
                  result: Optional[Any] = None) -> SafeMongoDBResult:
    """
    Create a successful SafeMongoDBResult.
    
    Args:
        value: The value of the operation
        result: The raw operation result
        
    Returns:
        SafeMongoDBResult with success
    """
    return SafeMongoDBResult(result=result, value=value)

# Helper function to create an error result
def error_result(error: Optional[Exception] = None,
                message: Optional[str] = None) -> SafeMongoDBResult:
    """
    Create an error SafeMongoDBResult.
    
    Args:
        error: The error that occurred during the operation
        message: Error message if error is not provided
        
    Returns:
        SafeMongoDBResult with error
    """
    if error is None and message is not None:
        error = Exception(message)
    elif error is None:
        error = Exception("Unknown error")
        
    return SafeMongoDBResult(error=error)

# Export for easy importing
__all__ = [
    'setup_mongodb', 'get_client', 'get_database', 'get_collection',
    'find_one_document', 'find_documents', 'insert_document',
    'update_document', 'delete_document', 'count_documents',
    'SafeMongoDBResult', 'SafeDocument',
    'success_result', 'error_result'
]