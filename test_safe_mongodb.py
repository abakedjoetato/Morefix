"""
Test script for safe_mongodb.py functionality
"""

import logging
import asyncio
from utils.safe_mongodb import SafeDocument, SafeMongoDBResult

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

async def test_safe_document():
    """Test the SafeDocument class"""
    logger.info("Testing SafeDocument...")
    
    # Test initialization with empty data
    doc1 = SafeDocument()
    logger.info(f"Empty doc: {doc1}")
    
    # Test initialization with data
    doc2 = SafeDocument({"name": "Test", "value": 123, "is_active": True})
    logger.info(f"Doc with data: {doc2}")
    
    # Test helper methods
    logger.info(f"get_str: {doc2.get_str('name')}")
    logger.info(f"get_int: {doc2.get_int('value')}")
    logger.info(f"get_bool: {doc2.get_bool('is_active')}")
    logger.info(f"get_list (default): {doc2.get_list('items')}")
    logger.info(f"get_dict (default): {doc2.get_dict('metadata')}")
    
    return True

async def test_safe_mongodb_result():
    """Test the SafeMongoDBResult class"""
    logger.info("Testing SafeMongoDBResult...")
    
    # Test success result
    success = SafeMongoDBResult.success_result({"data": "test"})
    logger.info(f"Success result: {success}")
    logger.info(f"Success bool: {bool(success)}")
    logger.info(f"Success data: {success.data}")
    
    # Test error result
    error = SafeMongoDBResult.error_result("Test error", 404, "test_collection")
    logger.info(f"Error result: {error}")
    logger.info(f"Error bool: {bool(error)}")
    logger.info(f"Error message: {error.error}")
    
    return True

async def main():
    """Run all tests"""
    try:
        logger.info("Starting safe_mongodb tests...")
        
        # Run tests
        await test_safe_document()
        await test_safe_mongodb_result()
        
        logger.info("All tests completed successfully!")
    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())