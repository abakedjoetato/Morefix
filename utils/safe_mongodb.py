"""
Safe MongoDB interaction utilities for the Tower of Temptation bot.

This module provides safer MongoDB document handling with proper error handling,
type validation, and compatibility with both Motor and PyMongo APIs.
"""

import logging
import uuid
from typing import Dict, Any, List, Optional, Union, TypeVar, Generic, Type, cast

# These import statements will be dynamically attempted at runtime to handle
# different MongoDB installation patterns
try:
    from pymongo.database import Database
    from pymongo.collection import Collection
    from pymongo.results import InsertOneResult, UpdateResult, DeleteResult
    from pymongo.errors import PyMongoError
except ImportError:
    # Define stub classes to allow type checking without hard dependency
    class Database: pass
    class Collection: pass
    class InsertOneResult: pass
    class UpdateResult: pass
    class DeleteResult: pass
    class PyMongoError(Exception): pass

logger = logging.getLogger(__name__)

# Type variable for generic document classes
T = TypeVar('T', bound='SafeDocument')

# Singleton MongoDB database connection
_db_instance = None

def set_database(db_instance: Database) -> None:
    """Set the global MongoDB database instance
    
    Args:
        db_instance: MongoDB database instance
    """
    global _db_instance
    _db_instance = db_instance
    
def get_database() -> Optional[Database]:
    """Get the global MongoDB database instance
    
    Returns:
        The MongoDB database instance or None if not set
    """
    return _db_instance

class SafeMongoDBResult:
    """Wrapper class for MongoDB operation results with safer access methods"""
    
    def __init__(self, 
                raw_result: Union[InsertOneResult, UpdateResult, DeleteResult, Any] = None,
                success: bool = None,
                data: Any = None,
                error_message: str = None,
                exception: Exception = None):
        """Initialize with a raw MongoDB result
        
        Args:
            raw_result: Raw result from MongoDB operation
            success: Whether the operation was successful (manual override)
            data: Result data (for compatibility)
            error_message: Error message if operation failed
            exception: Exception if operation failed
        """
        self._raw_result = raw_result
        self._success = success
        self._data = data
        self._error_message = error_message
        self._exception = exception
        
    @property
    def acknowledged(self) -> bool:
        """Whether the operation was acknowledged
        
        Returns:
            bool: True if acknowledged, False otherwise
        """
        if hasattr(self._raw_result, 'acknowledged'):
            return bool(self._raw_result.acknowledged)
        return False
        
    @property
    def inserted_id(self) -> Optional[str]:
        """Get the ID of the inserted document
        
        Returns:
            Optional[str]: Inserted document ID or None
        """
        if hasattr(self._raw_result, 'inserted_id'):
            return str(self._raw_result.inserted_id)
        return None
        
    @property
    def modified_count(self) -> int:
        """Get the number of modified documents
        
        Returns:
            int: Number of modified documents
        """
        if hasattr(self._raw_result, 'modified_count'):
            return int(self._raw_result.modified_count)
        return 0
        
    @property
    def matched_count(self) -> int:
        """Get the number of matched documents
        
        Returns:
            int: Number of matched documents
        """
        if hasattr(self._raw_result, 'matched_count'):
            return int(self._raw_result.matched_count)
        return 0
        
    @property
    def deleted_count(self) -> int:
        """Get the number of deleted documents
        
        Returns:
            int: Number of deleted documents
        """
        if hasattr(self._raw_result, 'deleted_count'):
            return int(self._raw_result.deleted_count)
        return 0
        
    @property
    def upserted_id(self) -> Optional[str]:
        """Get the ID of the upserted document
        
        Returns:
            Optional[str]: Upserted document ID or None
        """
        if hasattr(self._raw_result, 'upserted_id') and self._raw_result.upserted_id:
            return str(self._raw_result.upserted_id)
        return None
        
    def is_success(self) -> bool:
        """Check if the operation was successful
        
        Returns:
            bool: True if successful, False otherwise
        """
        # Different ways to determine success depending on operation type
        if hasattr(self._raw_result, 'acknowledged'):
            if not self._raw_result.acknowledged:
                return False
                
        # Insert operations
        if hasattr(self._raw_result, 'inserted_id'):
            return self._raw_result.inserted_id is not None
            
        # Update operations
        if hasattr(self._raw_result, 'modified_count') or hasattr(self._raw_result, 'matched_count'):
            modified = getattr(self._raw_result, 'modified_count', 0)
            matched = getattr(self._raw_result, 'matched_count', 0)
            upserted = hasattr(self._raw_result, 'upserted_id') and self._raw_result.upserted_id is not None
            return modified > 0 or upserted or matched > 0
            
        # Delete operations
        if hasattr(self._raw_result, 'deleted_count'):
            return self._raw_result.deleted_count > 0
            
        # Fallback for unknown result types
        return True
        
    def __str__(self) -> str:
        """String representation"""
        return f"SafeMongoDBResult({str(self._raw_result)})"
        
    def __repr__(self) -> str:
        """Detailed representation"""
        return f"SafeMongoDBResult({repr(self._raw_result)})"
        
    # Compatibility methods for older pattern with .success and .error properties
    
    @property
    def success(self) -> bool:
        """Whether the operation was successful
        
        Returns:
            bool: True if successful, False otherwise
        """
        if self._success is not None:
            return self._success
        return self.is_success()
    
    @property
    def data(self) -> Any:
        """Get the operation data
        
        Returns:
            Any: Operation data
        """
        if self._data is not None:
            return self._data
        return self._raw_result
    
    @property
    def error(self) -> Optional[str]:
        """Get the error message if operation failed
        
        Returns:
            Optional[str]: Error message or None if successful
        """
        if self._error_message:
            return self._error_message
        if self._exception:
            return str(self._exception)
        if not self.success:
            return "Unknown error occurred"
        return None
        
    @property
    def result(self) -> Any:
        """Alias for data property for backward compatibility
        
        Returns:
            Any: Operation result data
        """
        return self.data
        
    # Factory methods for creating results
    
    @classmethod
    def success_result(cls, data: Any = None) -> 'SafeMongoDBResult':
        """Create a success result
        
        Args:
            data: Operation result data
            
        Returns:
            SafeMongoDBResult: Success result
        """
        return cls(success=True, data=data)
    
    @classmethod
    def error_result(cls, error_message: str = None, exception: Exception = None) -> 'SafeMongoDBResult':
        """Create an error result
        
        Args:
            error_message: Error message
            exception: Exception that occurred
            
        Returns:
            SafeMongoDBResult: Error result
        """
        return cls(success=False, error_message=error_message, exception=exception)
        
    def __bool__(self) -> bool:
        """Allow direct boolean checks: `if result:`
        
        Returns:
            bool: True if successful, False otherwise
        """
        return self.success

class SafeDocument:
    """Base class for MongoDB document models with safe operations"""
    
    # Collection name to be overridden by subclasses
    collection_name = "documents"
    
    def __init__(self, _id: Optional[str] = None):
        """Initialize document with optional ID
        
        Args:
            _id: MongoDB document ID
        """
        self._id = _id or str(uuid.uuid4())
        
    @classmethod
    def get_database(cls) -> Database:
        """Get the MongoDB database
        
        Returns:
            Database: MongoDB database instance
            
        Raises:
            RuntimeError: If database is not initialized
        """
        db = get_database()
        if db is None:
            raise RuntimeError("MongoDB database not initialized. Call set_database() first.")
        return db
        
    @classmethod
    def get_collection(cls, db: Optional[Database] = None) -> Collection:
        """Get the MongoDB collection for this document type with safer access pattern
        
        Args:
            db: Optional database instance (uses default if None)
            
        Returns:
            Collection: MongoDB collection
            
        Raises:
            RuntimeError: If database is not initialized
        """
        if db is None:
            db = cls.get_database()
            
        # Try different access patterns for compatibility with different MongoDB drivers
        try:
            # First try dictionary-style access (common in Motor)
            if hasattr(db, '__getitem__'):
                return db[cls.collection_name]
        except (TypeError, KeyError, AttributeError):
            pass
            
        # Try property or method access (common in some PyMongo versions)
        if hasattr(db, cls.collection_name):
            collection = getattr(db, cls.collection_name)
            if callable(collection):
                return collection()
            return collection
            
        # Try get_collection method (common in both)
        if hasattr(db, 'get_collection'):
            return db.get_collection(cls.collection_name)
            
        # Fall back to dictionary-style access and let it raise appropriate error if it fails
        return db[cls.collection_name]
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert document to dictionary for MongoDB storage
        
        Returns:
            Dict[str, Any]: Document as dictionary
        """
        # Import here to avoid circular imports
        from utils.mongo_compat import safe_serialize_for_mongodb
        
        # Get all instance attributes
        result = {}
        for key, value in self.__dict__.items():
            # Skip private attributes
            if key.startswith('_') and key != '_id':
                continue
                
            # Include all other attributes with serialization handling
            result[key] = safe_serialize_for_mongodb(value)
            
        return result
        
    @classmethod
    def from_dict(cls: Type[T], data: Dict[str, Any]) -> T:
        """Create document from dictionary
        
        Args:
            data: Dictionary containing document data
            
        Returns:
            Document instance
        """
        # Import here to avoid circular imports
        from utils.mongo_compat import safe_deserialize_from_mongodb
        
        # Handle None data
        if data is None:
            return cls()
            
        # Create a copy of data to avoid modifying the original
        processed_data = {}
        
        # Process the data with MongoDB compatibility handling
        for key, value in data.items():
            processed_data[key] = safe_deserialize_from_mongodb(value)
            
        # Create the object with the processed data
        return cls(**processed_data)
        
    async def save(self) -> bool:
        """Save document to MongoDB
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            db = self.get_database()
            collection = self.get_collection(db)
            
            document_dict = self.to_dict()
            
            # Use upsert to insert or update
            result = await collection.update_one(
                {"_id": self._id},
                {"$set": document_dict},
                upsert=True
            )
            
            safe_result = SafeMongoDBResult(result)
            return safe_result.is_success()
            
        except Exception as e:
            logger.error(f"Error saving document to {self.collection_name}: {e}")
            return False
            
    async def delete(self) -> bool:
        """Delete document from MongoDB
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            db = self.get_database()
            collection = self.get_collection(db)
            
            result = await collection.delete_one({"_id": self._id})
            
            safe_result = SafeMongoDBResult(result)
            return safe_result.is_success()
            
        except Exception as e:
            logger.error(f"Error deleting document from {self.collection_name}: {e}")
            return False
            
    @classmethod
    async def get_by_id(cls: Type[T], doc_id: str) -> Optional[T]:
        """Get document by ID
        
        Args:
            doc_id: Document ID
            
        Returns:
            Optional[T]: Document instance or None if not found
        """
        if not doc_id:
            return None
            
        try:
            db = cls.get_database()
            collection = cls.get_collection(db)
            
            result = await collection.find_one({"_id": doc_id})
            if result:
                return cls.from_dict(result)
            return None
        except Exception as e:
            logger.error(f"Error getting document by ID from {cls.collection_name}: {e}")
            return None
            
    @classmethod
    async def get_all(cls: Type[T]) -> List[T]:
        """Get all documents from collection
        
        Returns:
            List[T]: List of document instances
        """
        try:
            db = cls.get_database()
            collection = cls.get_collection(db)
            
            cursor = collection.find({})
            documents = []
            
            async for document in cursor:
                documents.append(cls.from_dict(document))
                
            return documents
        except Exception as e:
            logger.error(f"Error getting all documents from {cls.collection_name}: {e}")
            return []
            
    @classmethod
    async def find(cls: Type[T], query: Dict[str, Any]) -> List[T]:
        """Find documents matching query
        
        Args:
            query: MongoDB query
            
        Returns:
            List[T]: List of document instances
        """
        try:
            db = cls.get_database()
            collection = cls.get_collection(db)
            
            cursor = collection.find(query)
            documents = []
            
            async for document in cursor:
                documents.append(cls.from_dict(document))
                
            return documents
        except Exception as e:
            logger.error(f"Error finding documents in {cls.collection_name}: {e}")
            return []
            
    @classmethod
    async def find_one(cls: Type[T], query: Dict[str, Any]) -> Optional[T]:
        """Find one document matching query
        
        Args:
            query: MongoDB query
            
        Returns:
            Optional[T]: Document instance or None if not found
        """
        try:
            db = cls.get_database()
            collection = cls.get_collection(db)
            
            result = await collection.find_one(query)
            if result:
                return cls.from_dict(result)
            return None
        except Exception as e:
            logger.error(f"Error finding one document in {cls.collection_name}: {e}")
            return None
            
    @classmethod
    async def count(cls, query: Dict[str, Any] = None) -> int:
        """Count documents matching query
        
        Args:
            query: MongoDB query (default: all documents)
            
        Returns:
            int: Number of matching documents
        """
        query = query or {}
        
        try:
            db = cls.get_database()
            collection = cls.get_collection(db)
            
            return await collection.count_documents(query)
        except Exception as e:
            logger.error(f"Error counting documents in {cls.collection_name}: {e}")
            return 0
            
    def __str__(self) -> str:
        """String representation"""
        class_name = self.__class__.__name__
        return f"{class_name}(_id={self._id})"
        
    def __repr__(self) -> str:
        """Detailed representation"""
        class_name = self.__class__.__name__
        attributes = ", ".join(f"{k}={repr(v)}" for k, v in self.__dict__.items())
        return f"{class_name}({attributes})"