"""
MongoDB Types for LSP Compatibility

This module provides type definitions for MongoDB classes to fix LSP errors
in the compatibility layer. These types are not meant to be used directly,
but rather to provide type hints for the LSP.
"""

from typing import Any, Dict, List, Optional, Union, TypeVar, Generic, Iterator, AsyncIterator

T = TypeVar('T')
_DocumentType = TypeVar('_DocumentType', bound=Dict[str, Any])

class InsertOneResult:
    """Type definition for InsertOneResult."""
    
    def __init__(self, acknowledged: bool = True, inserted_id: Any = None):
        self.acknowledged = acknowledged
        self.inserted_id = inserted_id

class UpdateResult:
    """Type definition for UpdateResult."""
    
    def __init__(
        self,
        acknowledged: bool = True,
        matched_count: int = 0,
        modified_count: int = 0,
        upserted_id: Any = None
    ):
        self.acknowledged = acknowledged
        self.matched_count = matched_count
        self.modified_count = modified_count
        self.upserted_id = upserted_id

class DeleteResult:
    """Type definition for DeleteResult."""
    
    def __init__(self, acknowledged: bool = True, deleted_count: int = 0):
        self.acknowledged = acknowledged
        self.deleted_count = deleted_count

class Collection(Generic[_DocumentType]):
    """Type definition for Collection."""
    
    def __init__(self, database: Any, name: str):
        self.database = database
        self.name = name
    
    async def find_one(self, filter: Dict[str, Any], **kwargs) -> Optional[_DocumentType]:
        """
        Find a single document.
        
        Args:
            filter: Query document
            **kwargs: Additional arguments
            
        Returns:
            Document or None
        """
        # Stub implementation for type checking
        return {} if filter else None  # type: ignore
    
    async def find(self, filter: Dict[str, Any], **kwargs) -> AsyncIterator[_DocumentType]:
        """
        Find documents.
        
        Args:
            filter: Query document
            **kwargs: Additional arguments
            
        Returns:
            Cursor
        """
        # Stub implementation for type checking
        if False:  # This will never execute but helps with type checking
            yield {}  # type: ignore
        return
    
    async def insert_one(self, document: Dict[str, Any], **kwargs) -> InsertOneResult:
        """
        Insert a single document.
        
        Args:
            document: Document to insert
            **kwargs: Additional arguments
            
        Returns:
            InsertOneResult instance
        """
        # Stub implementation for type checking
        return InsertOneResult(True, None)
    
    async def update_one(self, filter: Dict[str, Any], update: Dict[str, Any], **kwargs) -> UpdateResult:
        """
        Update a single document.
        
        Args:
            filter: Query document
            update: Update document
            **kwargs: Additional arguments
            
        Returns:
            UpdateResult instance
        """
        # Stub implementation for type checking
        return UpdateResult(True, 0, 0, None)
    
    async def delete_one(self, filter: Dict[str, Any], **kwargs) -> DeleteResult:
        """
        Delete a single document.
        
        Args:
            filter: Query document
            **kwargs: Additional arguments
            
        Returns:
            DeleteResult instance
        """
        # Stub implementation for type checking
        return DeleteResult(True, 0)
    
    async def count_documents(self, filter: Dict[str, Any], **kwargs) -> int:
        """
        Count documents.
        
        Args:
            filter: Query document
            **kwargs: Additional arguments
            
        Returns:
            Document count
        """
        # Stub implementation for type checking
        return 0

class Database(Generic[_DocumentType]):
    """Type definition for Database."""
    
    def __init__(self, client: Any, name: str):
        self.client = client
        self.name = name
    
    def __getitem__(self, name: str) -> Collection[_DocumentType]:
        """
        Get a collection.
        
        Args:
            name: Collection name
            
        Returns:
            Collection instance
        """
        # Stub implementation for type checking
        return Collection(self, name)
    
    def get_collection(self, name: str) -> Collection[_DocumentType]:
        """
        Get a collection.
        
        Args:
            name: Collection name
            
        Returns:
            Collection instance
        """
        # Stub implementation for type checking
        return Collection(self, name)