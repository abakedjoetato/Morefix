"""
Safe MongoDB Operations

This module provides safe MongoDB operations with proper error handling
and type safety. It's designed to work with both pymongo and motor
with identical interfaces.
"""

import logging
import traceback
from typing import Any, Dict, List, Optional, Tuple, Union, TypeVar, cast, Generic, Type

# Type hints
from pymongo.collection import Collection
from pymongo.cursor import Cursor
from pymongo.results import (
    InsertOneResult,
    UpdateResult,
    DeleteResult
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

T = TypeVar('T')

# Global database connection
_database = None

def set_database(db):
    """Set the global database connection."""
    global _database
    _database = db

def get_database():
    """Get the global database connection."""
    return _database

class SafeMongoDBResult(Generic[T]):
    """
    A result wrapper for MongoDB operations that includes error handling.
    
    Attributes:
        success: Whether the operation was successful
        data: The data returned by the operation, if successful
        error: The error that occurred, if any
        status_code: A status code for the operation (e.g., 200 for success)
    """
    
    def __init__(self, success: bool = True, data: Optional[T] = None, 
                 error: Optional[Exception] = None, status_code: int = 200,
                 raw_result: Optional[Any] = None):
        """
        Initialize the result.
        
        Args:
            success: Whether the operation was successful
            data: The data returned by the operation
            error: The error that occurred
            status_code: A status code for the operation
            raw_result: The raw result from the MongoDB operation
        """
        self.success = success
        self.data = data
        self.error = error
        self.status_code = status_code
        self.raw_result = raw_result
        
    @property
    def is_success(self) -> bool:
        """Whether the operation was successful."""
        return self.success and self.error is None
        
    @property
    def acknowledged(self) -> bool:
        """Whether the operation was acknowledged by the server."""
        if not self.raw_result:
            return False
        return getattr(self.raw_result, 'acknowledged', False)
        
    @property
    def inserted_id(self) -> Optional[Any]:
        """The ID of the inserted document."""
        if not self.raw_result:
            return None
        return getattr(self.raw_result, 'inserted_id', None)
        
    @property
    def matched_count(self) -> int:
        """The number of documents matched by the query."""
        if not self.raw_result:
            return 0
        return getattr(self.raw_result, 'matched_count', 0)
        
    @property
    def modified_count(self) -> int:
        """The number of documents modified by the operation."""
        if not self.raw_result:
            return 0
        return getattr(self.raw_result, 'modified_count', 0)
        
    @property
    def deleted_count(self) -> int:
        """The number of documents deleted by the operation."""
        if not self.raw_result:
            return 0
        return getattr(self.raw_result, 'deleted_count', 0)
        
    @property
    def upserted_id(self) -> Optional[Any]:
        """The ID of the upserted document."""
        if not self.raw_result:
            return None
        return getattr(self.raw_result, 'upserted_id', None)
        
    @classmethod
    def success_result(cls, data: Optional[T] = None, raw_result: Optional[Any] = None) -> 'SafeMongoDBResult[T]':
        """Create a success result."""
        return cls(success=True, data=data, raw_result=raw_result)
        
    @classmethod
    def error_result(cls, error: Optional[Exception] = None, 
                     status_code: int = 500) -> 'SafeMongoDBResult[T]':
        """Create an error result."""
        return cls(success=False, error=error, status_code=status_code)
        
    def __bool__(self) -> bool:
        """Convert to boolean."""
        return self.success

class SafeDocument:
    """
    A base class for MongoDB documents with helper methods.
    
    This class provides helper methods for working with MongoDB documents,
    including serialization, deserialization, and CRUD operations.
    """
    
    collection_name = None
    
    @classmethod
    def get_collection(cls) -> Collection:
        """Get the collection for this document type."""
        if _database is None:
            raise RuntimeError("Database not initialized. Call set_database first.")
            
        if cls.collection_name is None:
            raise NotImplementedError("Collection name not specified.")
            
        return _database[cls.collection_name]
        
    @classmethod
    async def get_by_id(cls, id, **kwargs) -> SafeMongoDBResult:
        """Get a document by ID."""
        return await safe_find_one(cls.get_collection(), {'_id': id}, **kwargs)
        
    @classmethod
    async def find_one(cls, filter, **kwargs) -> SafeMongoDBResult:
        """Find a single document."""
        return await safe_find_one(cls.get_collection(), filter, **kwargs)
        
    @classmethod
    async def find(cls, filter, **kwargs) -> SafeMongoDBResult:
        """Find documents."""
        return await safe_find(cls.get_collection(), filter, **kwargs)
        
    @classmethod
    async def count(cls, filter=None, **kwargs) -> SafeMongoDBResult:
        """Count documents."""
        return await safe_count(cls.get_collection(), filter, **kwargs)
        
    @classmethod
    async def get_all(cls, **kwargs) -> SafeMongoDBResult:
        """Get all documents."""
        return await safe_find(cls.get_collection(), {}, **kwargs)
        
    @classmethod
    async def insert_one(cls, document, **kwargs) -> SafeMongoDBResult:
        """Insert a document."""
        return await safe_insert_one(cls.get_collection(), document, **kwargs)
        
    @classmethod
    async def update_one(cls, filter, update, **kwargs) -> SafeMongoDBResult:
        """Update a document."""
        return await safe_update_one(cls.get_collection(), filter, update, **kwargs)
        
    @classmethod
    async def delete_one(cls, filter, **kwargs) -> SafeMongoDBResult:
        """Delete a document."""
        return await safe_delete_one(cls.get_collection(), filter, **kwargs)
        
    def __getattr__(self, name):
        """Get an attribute dynamically."""
        # This allows accessing document fields as attributes
        if name in self.__dict__:
            return self.__dict__[name]
        raise AttributeError(f"{self.__class__.__name__} has no attribute {name}")

def get_collection(collection_name: str) -> Collection:
    """
    Get a MongoDB collection by name.
    
    Args:
        collection_name: The name of the collection
        
    Returns:
        The collection
        
    Raises:
        RuntimeError: If the database is not initialized
    """
    if _database is None:
        raise RuntimeError("Database not initialized. Call set_database first.")
        
    return _database[collection_name]

async def safe_find_one(collection: Collection, filter: Dict, 
                        projection: Optional[Dict] = None, 
                        **kwargs) -> SafeMongoDBResult:
    """
    Safely find a single document in a collection.
    
    Args:
        collection: The collection to search
        filter: The filter to apply
        projection: The projection to apply
        **kwargs: Additional arguments to pass to find_one
        
    Returns:
        A SafeMongoDBResult with the found document
    """
    try:
        # Check if collection's find_one is async or not
        find_one_method = collection.find_one
        if hasattr(find_one_method, '__await__'):
            # Async Motor version
            if projection:
                result = await find_one_method(filter, projection, **kwargs)
            else:
                result = await find_one_method(filter, **kwargs)
        else:
            # Sync PyMongo version
            if projection:
                result = find_one_method(filter, projection, **kwargs)
            else:
                result = find_one_method(filter, **kwargs)
                
        return SafeMongoDBResult.success_result(data=result)
    except Exception as e:
        logger.error(f"Error finding document: {e}")
        logger.debug(traceback.format_exc())
        return SafeMongoDBResult.error_result(error=e)

async def safe_find(collection: Collection, filter: Dict, 
                    projection: Optional[Dict] = None, 
                    **kwargs) -> SafeMongoDBResult:
    """
    Safely find documents in a collection.
    
    Args:
        collection: The collection to search
        filter: The filter to apply
        projection: The projection to apply
        **kwargs: Additional arguments to pass to find
        
    Returns:
        A SafeMongoDBResult with the found documents as a list
    """
    try:
        # Check if collection's find is async or not
        find_method = collection.find
        cursor = None
        
        if projection:
            cursor = find_method(filter, projection, **kwargs)
        else:
            cursor = find_method(filter, **kwargs)
            
        # Check if cursor is async or not
        if hasattr(cursor, 'to_list') and hasattr(cursor.to_list, '__await__'):
            # Async Motor version
            result = await cursor.to_list(length=None)
        else:
            # Sync PyMongo version
            result = list(cursor)
            
        return SafeMongoDBResult.success_result(data=result)
    except Exception as e:
        logger.error(f"Error finding documents: {e}")
        logger.debug(traceback.format_exc())
        return SafeMongoDBResult.error_result(error=e)

async def safe_insert_one(collection: Collection, document: Dict, 
                           **kwargs) -> SafeMongoDBResult:
    """
    Safely insert a document into a collection.
    
    Args:
        collection: The collection to insert into
        document: The document to insert
        **kwargs: Additional arguments to pass to insert_one
        
    Returns:
        A SafeMongoDBResult with the insertion result
    """
    try:
        # Check if collection's insert_one is async or not
        insert_one_method = collection.insert_one
        if hasattr(insert_one_method, '__await__'):
            # Async Motor version
            result = await insert_one_method(document, **kwargs)
        else:
            # Sync PyMongo version
            result = insert_one_method(document, **kwargs)
            
        return SafeMongoDBResult.success_result(data=result.inserted_id, raw_result=result)
    except Exception as e:
        logger.error(f"Error inserting document: {e}")
        logger.debug(traceback.format_exc())
        return SafeMongoDBResult.error_result(error=e)

async def safe_update_one(collection: Collection, filter: Dict, update: Dict, 
                           **kwargs) -> SafeMongoDBResult:
    """
    Safely update a document in a collection.
    
    Args:
        collection: The collection to update
        filter: The filter to apply
        update: The update to apply
        **kwargs: Additional arguments to pass to update_one
        
    Returns:
        A SafeMongoDBResult with the update result
    """
    try:
        # Check if collection's update_one is async or not
        update_one_method = collection.update_one
        if hasattr(update_one_method, '__await__'):
            # Async Motor version
            result = await update_one_method(filter, update, **kwargs)
        else:
            # Sync PyMongo version
            result = update_one_method(filter, update, **kwargs)
            
        return SafeMongoDBResult.success_result(
            data={
                'matched_count': result.matched_count,
                'modified_count': result.modified_count,
                'upserted_id': result.upserted_id
            }, 
            raw_result=result
        )
    except Exception as e:
        logger.error(f"Error updating document: {e}")
        logger.debug(traceback.format_exc())
        return SafeMongoDBResult.error_result(error=e)

async def safe_delete_one(collection: Collection, filter: Dict, 
                           **kwargs) -> SafeMongoDBResult:
    """
    Safely delete a document from a collection.
    
    Args:
        collection: The collection to delete from
        filter: The filter to apply
        **kwargs: Additional arguments to pass to delete_one
        
    Returns:
        A SafeMongoDBResult with the deletion result
    """
    try:
        # Check if collection's delete_one is async or not
        delete_one_method = collection.delete_one
        if hasattr(delete_one_method, '__await__'):
            # Async Motor version
            result = await delete_one_method(filter, **kwargs)
        else:
            # Sync PyMongo version
            result = delete_one_method(filter, **kwargs)
            
        return SafeMongoDBResult.success_result(
            data={'deleted_count': result.deleted_count}, 
            raw_result=result
        )
    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        logger.debug(traceback.format_exc())
        return SafeMongoDBResult.error_result(error=e)

async def safe_count(collection: Collection, filter: Optional[Dict] = None, 
                      **kwargs) -> SafeMongoDBResult:
    """
    Safely count documents in a collection.
    
    Args:
        collection: The collection to count
        filter: The filter to apply
        **kwargs: Additional arguments to pass to count_documents
        
    Returns:
        A SafeMongoDBResult with the count
    """
    try:
        # Handle None filter
        if filter is None:
            filter = {}
            
        # Check if collection's count_documents is async or not
        count_method = collection.count_documents
        if hasattr(count_method, '__await__'):
            # Async Motor version
            result = await count_method(filter, **kwargs)
        else:
            # Sync PyMongo version
            result = count_method(filter, **kwargs)
            
        return SafeMongoDBResult.success_result(data=result)
    except Exception as e:
        logger.error(f"Error counting documents: {e}")
        logger.debug(traceback.format_exc())
        return SafeMongoDBResult.error_result(error=e)