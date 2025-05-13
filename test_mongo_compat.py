"""
MongoDB Compatibility Utilities Test

This module tests the MongoDB compatibility utilities in the mongo_compat.py module.
"""

import unittest
import json
from datetime import datetime, timezone
from unittest.mock import MagicMock

from utils.mongo_compat import (
    is_bson_datetime,
    safe_convert_to_datetime,
    safe_serialize_for_mongodb,
    safe_deserialize_from_mongodb
)

class DateTimeBSONMock:
    """Mock class for BSON datetime type"""
    
    def __init__(self, dt=None):
        self.datetime = dt or datetime.now()
        
    def __str__(self):
        return str(self.datetime.isoformat())


class TestMongoDBCompat(unittest.TestCase):
    """Test the MongoDB compatibility utilities"""
    
    def setUp(self):
        """Set up the test with various datetime formats"""
        # Python native datetime
        self.py_datetime = datetime(2025, 5, 13, 12, 34, 56, tzinfo=timezone.utc)
        
        # MongoDB extended JSON format ($date)
        self.json_date_ms = {"$date": 1747071296000}  # Milliseconds since epoch
        self.json_date_str = {"$date": "2025-05-13T12:34:56Z"}
        
        # Mock BSON datetime type with a class that has a datetime attribute
        self.bson_datetime = DateTimeBSONMock(self.py_datetime)
        
        # Complex data with nested datetime values
        self.complex_data = {
            "name": "Test Document",
            "created_at": self.py_datetime,
            "updated_at": self.json_date_str,
            "metadata": {
                "timestamp": self.bson_datetime
            },
            "tags": ["test", "mongodb", "compatibility"]
        }
        
    def test_is_bson_datetime(self):
        """Test the is_bson_datetime function"""
        # Python datetime should be detected
        self.assertTrue(is_bson_datetime(self.py_datetime))
        
        # MongoDB extended JSON format should be detected
        self.assertTrue(is_bson_datetime(self.json_date_ms))
        self.assertTrue(is_bson_datetime(self.json_date_str))
        
        # Mock BSON datetime should be detected
        self.assertTrue(is_bson_datetime(self.bson_datetime))
        
        # These should not be detected as datetimes
        self.assertFalse(is_bson_datetime("2025-05-13"))
        self.assertFalse(is_bson_datetime(1747071296000))
        self.assertFalse(is_bson_datetime({"key": "value"}))
        
    def test_safe_convert_to_datetime(self):
        """Test the safe_convert_to_datetime function"""
        # Python datetime should remain unchanged
        self.assertEqual(
            safe_convert_to_datetime(self.py_datetime),
            self.py_datetime
        )
        
        # Extended JSON formats should be converted to datetime
        json_ms_dt = safe_convert_to_datetime(self.json_date_ms)
        self.assertIsInstance(json_ms_dt, datetime)
        self.assertEqual(json_ms_dt.year, 2025)
        self.assertEqual(json_ms_dt.month, 5)
        self.assertEqual(json_ms_dt.day, 13)
        
        json_str_dt = safe_convert_to_datetime(self.json_date_str)
        self.assertIsInstance(json_str_dt, datetime)
        self.assertEqual(json_str_dt.year, 2025)
        self.assertEqual(json_str_dt.month, 5)
        self.assertEqual(json_str_dt.day, 13)
        
        # Mock BSON datetime should be converted to datetime
        bson_dt = safe_convert_to_datetime(self.bson_datetime)
        self.assertIsInstance(bson_dt, datetime)
        self.assertEqual(bson_dt, self.py_datetime)
    
    def test_safe_serialize_for_mongodb(self):
        """Test the safe_serialize_for_mongodb function"""
        # Simple types should remain unchanged
        self.assertEqual(safe_serialize_for_mongodb("test"), "test")
        self.assertEqual(safe_serialize_for_mongodb(123), 123)
        self.assertEqual(safe_serialize_for_mongodb(True), True)
        
        # Python datetime should remain unchanged (MongoDB driver handles datetime)
        self.assertEqual(safe_serialize_for_mongodb(self.py_datetime), self.py_datetime)
        
        # Complex data should be properly serialized
        serialized = safe_serialize_for_mongodb(self.complex_data)
        
        # Verify the structure remains the same
        self.assertIsInstance(serialized, dict)
        self.assertEqual(serialized["name"], "Test Document")
        self.assertEqual(serialized["tags"], ["test", "mongodb", "compatibility"])
        
        # Verify datetimes are properly handled
        self.assertEqual(serialized["created_at"], self.py_datetime)
        
        # Nested data should be properly serialized
        self.assertIsInstance(serialized["metadata"], dict)
        
    def test_safe_deserialize_from_mongodb(self):
        """Test the safe_deserialize_from_mongodb function"""
        # Deserialize our complex data
        deserialized = safe_deserialize_from_mongodb(self.complex_data)
        
        # Verify the structure remains the same
        self.assertIsInstance(deserialized, dict)
        self.assertEqual(deserialized["name"], "Test Document")
        self.assertEqual(deserialized["tags"], ["test", "mongodb", "compatibility"])
        
        # Verify all datetime types are converted to Python datetime
        self.assertIsInstance(deserialized["created_at"], datetime)
        self.assertIsInstance(deserialized["updated_at"], datetime)
        self.assertIsInstance(deserialized["metadata"]["timestamp"], datetime)
        
        # Verify the values are correct
        self.assertEqual(deserialized["created_at"].year, 2025)
        self.assertEqual(deserialized["created_at"].month, 5)
        self.assertEqual(deserialized["created_at"].day, 13)


if __name__ == '__main__':
    unittest.main()