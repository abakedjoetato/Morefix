"""
Safe MongoDB Compatibility Test

This module tests the compatibility of the safe_mongodb.py module with different
MongoDB connection patterns and versions.
"""

import asyncio
import logging
import os
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Import the modules to test
from utils.safe_mongodb import (
    set_database, 
    get_database, 
    SafeMongoDBResult, 
    SafeDocument
)

class MockCollection:
    """Mock MongoDB collection for testing"""
    
    def __init__(self, name):
        self.name = name
        self.data = {}
        
    async def find_one(self, query):
        """Mock find_one method"""
        if '_id' in query and query['_id'] in self.data:
            return self.data[query['_id']]
        return None
        
    async def find(self, query=None):
        """Mock find method that returns an async iterator"""
        # Always return all data for simplicity in this test
        self.cursor = list(self.data.values())
        self.index = 0
        return self
        
    async def count_documents(self, query=None):
        """Mock count_documents method"""
        return len(self.data)
        
    async def update_one(self, filter, update, upsert=False):
        """Mock update_one method"""
        result = MagicMock()
        _id = filter.get('_id')
        if _id in self.data or upsert:
            self.data[_id] = update.get('$set', {})
            self.data[_id]['_id'] = _id
            result.acknowledged = True
            result.matched_count = 1 if _id in self.data else 0
            result.modified_count = 1
            result.upserted_id = _id if _id not in self.data else None
        else:
            result.acknowledged = False
            result.matched_count = 0
            result.modified_count = 0
        return result
        
    async def delete_one(self, filter):
        """Mock delete_one method"""
        result = MagicMock()
        _id = filter.get('_id')
        if _id in self.data:
            del self.data[_id]
            result.acknowledged = True
            result.deleted_count = 1
        else:
            result.acknowledged = True
            result.deleted_count = 0
        return result
        
    # Define async iterator methods
    def __aiter__(self):
        return self
        
    async def __anext__(self):
        if self.index < len(self.cursor):
            result = self.cursor[self.index]
            self.index += 1
            return result
        raise StopAsyncIteration


class MockDatabaseDictStyle:
    """Mock MongoDB database with dictionary style access"""
    
    def __init__(self):
        self.collections = {}
        
    def __getitem__(self, name):
        if name not in self.collections:
            self.collections[name] = MockCollection(name)
        return self.collections[name]


class MockDatabasePropertyStyle:
    """Mock MongoDB database with property style access"""
    
    def __init__(self):
        self.users = MockCollection("users")
        self.guilds = MockCollection("guilds")
        self.documents = MockCollection("documents")


class MockDatabaseMethodStyle:
    """Mock MongoDB database with method style access"""
    
    def __init__(self):
        self._collections = {}
        
    def get_collection(self, name):
        if name not in self._collections:
            self._collections[name] = MockCollection(name)
        return self._collections[name]


class TestDocument(SafeDocument):
    """Test document model"""
    
    collection_name = "test_documents"
    
    def __init__(self, _id=None, name=None, value=None):
        super().__init__(_id)
        self.name = name
        self.value = value


class SafeMongoDBResultTest(unittest.TestCase):
    """Test the SafeMongoDBResult class"""
    
    def test_init_with_raw_result(self):
        """Test initializing with raw result"""
        raw_result = MagicMock()
        raw_result.acknowledged = True
        raw_result.inserted_id = "123"
        
        result = SafeMongoDBResult(raw_result)
        
        self.assertTrue(result.is_success())
        self.assertEqual(result.inserted_id(), "123")
        
    def test_init_with_manual_values(self):
        """Test initializing with manual values"""
        result = SafeMongoDBResult(success=True, data={"key": "value"})
        
        self.assertTrue(result.is_success())
        self.assertEqual(result.data(), {"key": "value"})
        
    def test_error_result(self):
        """Test creating an error result"""
        result = SafeMongoDBResult.error_result("Test error")
        
        self.assertFalse(result.is_success())
        self.assertEqual(result.error(), "Test error")
        
    def test_bool_conversion(self):
        """Test boolean conversion"""
        self.assertTrue(bool(SafeMongoDBResult(success=True)))
        self.assertFalse(bool(SafeMongoDBResult(success=False)))


class SafeDocumentTest(unittest.IsolatedAsyncioTestCase):
    """Test the SafeDocument class"""
    
    async def asyncSetUp(self):
        """Set up the test"""
        # Test with different database styles
        self.dict_style_db = MockDatabaseDictStyle()
        self.property_style_db = MockDatabasePropertyStyle()
        self.method_style_db = MockDatabaseMethodStyle()
        
    async def test_dict_style_db(self):
        """Test with dictionary style database"""
        set_database(self.dict_style_db)
        
        document = TestDocument(name="Test", value=42)
        self.assertTrue(await document.save())
        
        # Verify it can be retrieved
        retrieved = await TestDocument.get_by_id(document._id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.name, "Test")
        self.assertEqual(retrieved.value, 42)
        
    async def test_property_style_db(self):
        """Test with property style database"""
        set_database(self.property_style_db)
        
        # Test with a collection that exists as a property
        TestDocument.collection_name = "documents"
        
        document = TestDocument(name="Test", value=42)
        self.assertTrue(await document.save())
        
        # Verify it can be retrieved
        retrieved = await TestDocument.get_by_id(document._id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.name, "Test")
        self.assertEqual(retrieved.value, 42)
        
    async def test_method_style_db(self):
        """Test with method style database"""
        set_database(self.method_style_db)
        
        document = TestDocument(name="Test", value=42)
        self.assertTrue(await document.save())
        
        # Verify it can be retrieved
        retrieved = await TestDocument.get_by_id(document._id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.name, "Test")
        self.assertEqual(retrieved.value, 42)
        
    async def test_collection_operations(self):
        """Test all collection operations"""
        set_database(self.dict_style_db)
        
        # Test saving
        doc1 = TestDocument(_id="1", name="Doc 1", value=10)
        doc2 = TestDocument(_id="2", name="Doc 2", value=20)
        await doc1.save()
        await doc2.save()
        
        # Test find
        docs = await TestDocument.find({})
        self.assertEqual(len(docs), 2)
        
        # Test find_one
        doc = await TestDocument.find_one({"_id": "1"})
        self.assertEqual(doc.name, "Doc 1")
        
        # Test count
        count = await TestDocument.count()
        self.assertEqual(count, 2)
        
        # Test delete
        await doc1.delete()
        
        # Verify deletion
        count = await TestDocument.count()
        self.assertEqual(count, 1)
        
        # Test get_all
        docs = await TestDocument.get_all()
        self.assertEqual(len(docs), 1)
        
        # Make sure the right document remains
        self.assertEqual(docs[0].name, "Doc 2")


if __name__ == '__main__':
    unittest.main()