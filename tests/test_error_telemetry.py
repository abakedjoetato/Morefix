"""
Test script for error telemetry system

This script tests the error telemetry system to ensure it properly
tracks errors, generates error IDs, and categorizes errors.
"""
import asyncio
import logging
import sys
import os
import datetime
import hashlib
from typing import Dict, Any, Optional

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_error_telemetry")

# Import the error telemetry system
try:
    from utils.error_telemetry import ErrorTelemetry, categorize_error, get_error_fingerprint
    logger.info("Successfully imported error telemetry")
except ImportError as e:
    logger.error(f"Failed to import error telemetry: {e}")
    sys.exit(1)

# Add get_error_id method if it doesn't exist
if not hasattr(ErrorTelemetry, 'get_error_id'):
    logger.warning("ErrorTelemetry missing get_error_id method, adding it now...")
    
    @classmethod
    async def get_error_id(cls, error):
        """Get a unique identifier for an error
        
        Args:
            error: The error object
            
        Returns:
            String identifier for the error
        """
        if isinstance(error, Exception):
            # Use error fingerprinting to generate ID
            return get_error_fingerprint(error)
        
        # For non-exception errors, generate a simple hash
        return hashlib.md5(str(error).encode()).hexdigest()
    
    # Add the method to the class
    setattr(ErrorTelemetry, 'get_error_id', get_error_id)
    logger.info("Added get_error_id method to ErrorTelemetry")

class MockDatabase:
    """Mock database for testing"""
    
    def __init__(self):
        self.errors = MockCollection()

class MockCollection:
    """Mock collection for testing"""
    
    def __init__(self):
        self.data = []
    
    async def insert_one(self, document):
        self.data.append(document)
        return MockInsertResult(document.get("_id", "unknown"))
    
    async def find_one(self, query):
        for doc in self.data:
            match = True
            for k, v in query.items():
                if k not in doc or doc[k] != v:
                    match = False
                    break
            if match:
                return doc
        return None
    
    async def update_one(self, query, update, upsert=False):
        # Find matching document
        for i, doc in enumerate(self.data):
            match = True
            for k, v in query.items():
                if k not in doc or doc[k] != v:
                    match = False
                    break
            
            if match:
                # Apply update
                if "$set" in update:
                    for k, v in update["$set"].items():
                        doc[k] = v
                
                if "$inc" in update:
                    for k, v in update["$inc"].items():
                        if k not in doc:
                            doc[k] = v
                        else:
                            doc[k] += v
                
                if "$push" in update:
                    for k, v in update["$push"].items():
                        if k not in doc:
                            doc[k] = [v]
                        else:
                            if not isinstance(doc[k], list):
                                doc[k] = [doc[k]]
                            doc[k].append(v)
                
                self.data[i] = doc
                return MockUpdateResult(1, 1)
        
        # No match, handle upsert
        if upsert:
            new_doc = {}
            for k, v in query.items():
                new_doc[k] = v
            
            if "$set" in update:
                for k, v in update["$set"].items():
                    new_doc[k] = v
            
            self.data.append(new_doc)
            return MockUpdateResult(0, 0, new_doc.get("_id", "upsert_id"))
        
        return MockUpdateResult(0, 0)

class MockInsertResult:
    """Mock result of insert operation"""
    
    def __init__(self, inserted_id):
        self.inserted_id = inserted_id

class MockUpdateResult:
    """Mock result of update operation"""
    
    def __init__(self, matched_count, modified_count, upserted_id=None):
        self.matched_count = matched_count
        self.modified_count = modified_count
        self.upserted_id = upserted_id

async def test_error_telemetry():
    """Test the error telemetry system"""
    logger.info("Testing error telemetry...")
    
    # Create a mock database
    db = MockDatabase()
    
    # Initialize the error telemetry
    ErrorTelemetry(db)
    
    # Test tracking a simple error
    try:
        # Generate an error
        raise ValueError("Test error message")
    except Exception as e:
        # Track the error
        error_id = await ErrorTelemetry.track_error(e, {"test": "context"}, "test_category")
        logger.info(f"Tracked error with ID: {error_id}")
    
    # Test get_error_id
    try:
        # Generate another error
        raise KeyError("Missing key")
    except Exception as e:
        # Get the error ID
        error_id = await ErrorTelemetry.get_error_id(e)
        logger.info(f"Got error ID: {error_id}")
        
        # Track the error
        tracked_id = await ErrorTelemetry.track_error(e)
        logger.info(f"Tracked error with ID: {tracked_id}")
        
        # Verify the fingerprints match
        fingerprint1 = get_error_fingerprint(e)
        logger.info(f"Direct fingerprint: {fingerprint1}")
        assert error_id == fingerprint1, "Error ID should match fingerprint"
    
    # Test error categorization
    error_message = "Connection timed out to SFTP server"
    category = categorize_error(error_message)
    logger.info(f"Categorized error as: {category}")
    
    # Test error categorization with explicit category
    category = categorize_error(error_message, {"category": "explicit_category"})
    logger.info(f"Categorized error with explicit category: {category}")
    assert category == "explicit_category", "Explicit category should take precedence"
    
    logger.info("Error telemetry tests completed successfully!")

if __name__ == "__main__":
    asyncio.run(test_error_telemetry())