"""
Safe MongoDB result handling

This module provides utility classes and functions for safely handling MongoDB
operations with consistent error patterns.
"""

import logging
import traceback
from typing import Any, Callable, Dict, List, Optional, Generic, TypeVar, Union, cast

import motor.motor_asyncio
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
from pymongo.errors import PyMongoError

logger = logging.getLogger(__name__)

# Type variable for result types
T = TypeVar('T')

class SafeMongoDBResult(Generic[T]):
    """
    A result container for MongoDB operations
    
    This provides a consistent way to handle MongoDB operation results with
    success/error patterns.
    """
    
    def __init__(
        self,
        success: bool,
        data: Optional[T] = None,
        error: Optional[str] = None,
        error_code: Optional[int] = None,
        collection_name: Optional[str] = None
    ):
        """
        Initialize a MongoDB result
        
        Args:
            success: Whether the operation was successful
            data: The result data if successful
            error: Error message if unsuccessful
            error_code: Error code if unsuccessful
            collection_name: Name of the collection that was operated on
        """
        self.success = success
        self.data = data
        self.error = error
        self.error_code = error_code
        self.collection_name = collection_name
        
    @property
    def result(self) -> Optional[T]:
        """
        Get the result data
        
        This is an alias for the data property for compatibility with older code.
        
        Returns:
            The result data or None if unsuccessful
        """
        return self.data
        
    def __bool__(self) -> bool:
        """
        Convert to boolean
        
        Returns:
            True if successful, False otherwise
        """
        return self.success
        
    def __str__(self) -> str:
        """
        Convert to string
        
        Returns:
            String representation of the result
        """
        if self.success:
            return f"Success: {self.data}"
        else:
            return f"Error: {self.error} (code: {self.error_code})"

def safe_db_result(
    func: Optional[Callable] = None,
    *,
    collection_name: Optional[str] = None,
    default_value: Any = None
):
    """
    Decorator for safely executing MongoDB operations
    
    Args:
        func: The function to decorate
        collection_name: Name of the collection to include in error messages
        default_value: Default value to return if operation fails
        
    Returns:
        The decorated function
    """
    def decorator(func: Callable) -> Callable:
        async def wrapper(*args, **kwargs) -> SafeMongoDBResult:
            try:
                result = await func(*args, **kwargs)
                return SafeMongoDBResult(
                    success=True,
                    data=result,
                    collection_name=collection_name
                )
            except PyMongoError as e:
                error_code = getattr(e, 'code', None)
                logger.error(f"MongoDB error in {collection_name or func.__name__}: {e}")
                logger.debug(traceback.format_exc())
                return SafeMongoDBResult(
                    success=False,
                    data=default_value,
                    error=str(e),
                    error_code=error_code,
                    collection_name=collection_name
                )
            except Exception as e:
                logger.error(f"Unexpected error in {collection_name or func.__name__}: {e}")
                logger.debug(traceback.format_exc())
                return SafeMongoDBResult(
                    success=False,
                    data=default_value,
                    error=str(e),
                    collection_name=collection_name
                )
                
        return wrapper
        
    # Allow use as either @safe_db_result or @safe_db_result(collection_name="x")
    if func is None:
        return decorator
    else:
        return decorator(func)

class SafeMongoDBClient:
    """
    A wrapper around AsyncIOMotorClient with safer operation handling
    
    This class provides methods that return SafeMongoDBResult objects for
    consistent error handling.
    """
    
    def __init__(self, uri: str, db_name: Optional[str] = None):
        """
        Initialize the MongoDB client
        
        Args:
            uri: MongoDB connection URI
            db_name: Default database name
        """
        self.uri = uri
        self.db_name = db_name
        self.client: Optional[AsyncIOMotorClient] = None
        self.db: Optional[AsyncIOMotorDatabase] = None
        
    async def connect(self) -> SafeMongoDBResult[bool]:
        """
        Connect to the MongoDB server
        
        Returns:
            SafeMongoDBResult with success/error status
        """
        try:
            self.client = AsyncIOMotorClient(self.uri)
            
            # Test the connection with a ping
            await self.client.admin.command('ping')
            
            # Set the default database if provided
            if self.db_name:
                self.db = self.client[self.db_name]
                
            return SafeMongoDBResult(success=True, data=True)
        except PyMongoError as e:
            error_code = getattr(e, 'code', None)
            logger.error(f"MongoDB connection error: {e}")
            return SafeMongoDBResult(
                success=False,
                data=False,
                error=str(e),
                error_code=error_code
            )
        except Exception as e:
            logger.error(f"Unexpected connection error: {e}")
            return SafeMongoDBResult(
                success=False,
                data=False,
                error=str(e)
            )
            
    def get_database(self, db_name: Optional[str] = None) -> AsyncIOMotorDatabase:
        """
        Get a database from the client
        
        Args:
            db_name: Database name (defaults to self.db_name if not provided)
            
        Returns:
            The database object
            
        Raises:
            RuntimeError: If not connected
        """
        if self.client is None:
            raise RuntimeError("Not connected to MongoDB")
            
        if db_name:
            return self.client[db_name]
        elif self.db:
            return self.db
        else:
            raise RuntimeError("No database name provided")
            
    def get_collection(
        self,
        collection_name: str,
        db_name: Optional[str] = None
    ) -> AsyncIOMotorCollection:
        """
        Get a collection from the database
        
        Args:
            collection_name: Collection name
            db_name: Database name (defaults to self.db_name if not provided)
            
        Returns:
            The collection object
            
        Raises:
            RuntimeError: If not connected
        """
        db = self.get_database(db_name)
        return db[collection_name]
        
    @safe_db_result
    async def find_one(
        self,
        collection_name: str,
        query: Dict[str, Any],
        db_name: Optional[str] = None
    ) -> Any:
        """
        Find a single document in a collection
        
        Args:
            collection_name: Collection name
            query: Query to match the document
            db_name: Database name (defaults to self.db_name if not provided)
            
        Returns:
            The document if found
        """
        collection = self.get_collection(collection_name, db_name)
        result = await collection.find_one(query)
        return result
        
    @safe_db_result
    async def find(
        self,
        collection_name: str,
        query: Dict[str, Any],
        db_name: Optional[str] = None,
        sort: Optional[List[tuple]] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Find documents in a collection
        
        Args:
            collection_name: Collection name
            query: Query to match the documents
            db_name: Database name (defaults to self.db_name if not provided)
            sort: Sort specification
            limit: Maximum number of documents to return
            
        Returns:
            List of documents
        """
        collection = self.get_collection(collection_name, db_name)
        cursor = collection.find(query)
        
        if sort:
            cursor = cursor.sort(sort)
            
        if limit:
            cursor = cursor.limit(limit)
            
        return await cursor.to_list(length=limit if limit else None)
        
    @safe_db_result
    async def insert_one(
        self,
        collection_name: str,
        document: Dict[str, Any],
        db_name: Optional[str] = None
    ) -> str:
        """
        Insert a document into a collection
        
        Args:
            collection_name: Collection name
            document: Document to insert
            db_name: Database name (defaults to self.db_name if not provided)
            
        Returns:
            ID of the inserted document
        """
        collection = self.get_collection(collection_name, db_name)
        result = await collection.insert_one(document)
        return str(result.inserted_id)
        
    @safe_db_result
    async def update_one(
        self,
        collection_name: str,
        query: Dict[str, Any],
        update: Dict[str, Any],
        db_name: Optional[str] = None,
        upsert: bool = False
    ) -> bool:
        """
        Update a document in a collection
        
        Args:
            collection_name: Collection name
            query: Query to match the document
            update: Update to apply
            db_name: Database name (defaults to self.db_name if not provided)
            upsert: Whether to insert if not found
            
        Returns:
            True if a document was modified
        """
        collection = self.get_collection(collection_name, db_name)
        result = await collection.update_one(query, update, upsert=upsert)
        return result.modified_count > 0 or (upsert and result.upserted_id is not None)
        
    @safe_db_result
    async def delete_one(
        self,
        collection_name: str,
        query: Dict[str, Any],
        db_name: Optional[str] = None
    ) -> bool:
        """
        Delete a document from a collection
        
        Args:
            collection_name: Collection name
            query: Query to match the document
            db_name: Database name (defaults to self.db_name if not provided)
            
        Returns:
            True if a document was deleted
        """
        collection = self.get_collection(collection_name, db_name)
        result = await collection.delete_one(query)
        return result.deleted_count > 0
        
    @safe_db_result
    async def count_documents(
        self,
        collection_name: str,
        query: Dict[str, Any],
        db_name: Optional[str] = None
    ) -> int:
        """
        Count documents in a collection
        
        Args:
            collection_name: Collection name
            query: Query to match the documents
            db_name: Database name (defaults to self.db_name if not provided)
            
        Returns:
            Number of documents
        """
        collection = self.get_collection(collection_name, db_name)
        return await collection.count_documents(query)
        
    def close(self):
        """Close the MongoDB connection"""
        if self.client:
            self.client.close()
            self.client = None
            self.db = None