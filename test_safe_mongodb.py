"""
Test utility for verifying the SafeDocument and MongoDB connection.

Run this script with:
python test_safe_mongodb.py
"""

import os
import sys
import asyncio
import logging
from datetime import datetime
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_safe_mongodb")

# Load environment variables
load_dotenv()

# Ensure MongoDB URI is set
MONGODB_URI = os.environ.get("MONGODB_URI")
if not MONGODB_URI:
    logger.error("MONGODB_URI environment variable is not set")
    sys.exit(1)

# Import our MongoDB utilities
from utils.safe_mongodb import set_database, SafeDocument
from utils.premium_mongodb_models import PremiumSubscription, ActivationCode

async def setup_mongodb():
    """Set up MongoDB connection"""
    try:
        # Import Motor and set up connection
        from motor.motor_asyncio import AsyncIOMotorClient
        
        # Create client and connect to database
        logger.info(f"Connecting to MongoDB at {MONGODB_URI[:20]}...")
        client = AsyncIOMotorClient(MONGODB_URI)
        db = client.get_default_database()
        
        # Set the global database instance
        set_database(db)
        logger.info("MongoDB connection established successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        return False

async def test_premium_subscription():
    """Test PremiumSubscription model"""
    logger.info("\n--- Testing PremiumSubscription ---")
    
    # Create a test subscription
    guild_id = "123456789"
    tier = 1
    activated_at = datetime.utcnow()
    
    logger.info(f"Creating test subscription for guild {guild_id}...")
    sub = PremiumSubscription(
        guild_id=guild_id,
        tier=tier,
        activated_at=activated_at
    )
    
    # Save to database
    save_result = await sub.save()
    logger.info(f"Save result: {save_result}")
    
    # Retrieve by guild ID
    logger.info(f"Retrieving subscription for guild {guild_id}...")
    retrieved_sub = await PremiumSubscription.get_by_guild_id(guild_id)
    
    if retrieved_sub:
        logger.info(f"Retrieved subscription: {retrieved_sub}")
        logger.info(f"Is active: {retrieved_sub.is_active}")
        
        # Test upgrade
        logger.info("Upgrading subscription to tier 2 with 30 days...")
        upgrade_result = await retrieved_sub.upgrade(2, 30)
        logger.info(f"Upgrade result: {upgrade_result}")
        
        # Retrieve again to verify upgrade
        logger.info(f"Retrieving subscription after upgrade...")
        updated_sub = await PremiumSubscription.get_by_guild_id(guild_id)
        if updated_sub:
            logger.info(f"Updated subscription: {updated_sub}")
            logger.info(f"New tier: {updated_sub.tier}")
            logger.info(f"Expires at: {updated_sub.expires_at}")
            
            # Test cancellation
            logger.info("Cancelling subscription...")
            cancel_result = await updated_sub.cancel()
            logger.info(f"Cancel result: {cancel_result}")
            
            # Verify cancellation
            cancelled_sub = await PremiumSubscription.get_by_guild_id(guild_id)
            if cancelled_sub:
                logger.info(f"Cancelled subscription: {cancelled_sub}")
                logger.info(f"Is active: {cancelled_sub.is_active}")
                
                # Delete for cleanup
                logger.info("Deleting test subscription...")
                delete_result = await cancelled_sub.delete()
                logger.info(f"Delete result: {delete_result}")
            else:
                logger.error("Could not retrieve cancelled subscription")
        else:
            logger.error("Could not retrieve updated subscription")
    else:
        logger.error("Could not retrieve subscription")

async def test_activation_code():
    """Test ActivationCode model"""
    logger.info("\n--- Testing ActivationCode ---")
    
    # Generate an activation code
    logger.info("Generating activation code...")
    code = await ActivationCode.generate_code(
        tier=2,
        duration_days=30,
        created_by="123456789"
    )
    
    if code:
        logger.info(f"Generated code: {code.code}")
        
        # Retrieve by code
        logger.info(f"Retrieving activation code...")
        retrieved_code = await ActivationCode.get_by_code(code.code)
        
        if retrieved_code:
            logger.info(f"Retrieved code: {retrieved_code}")
            
            # Mark as used
            logger.info("Marking code as used...")
            used_result = await retrieved_code.mark_as_used("987654321")
            logger.info(f"Used result: {used_result}")
            
            # Verify used status
            logger.info(f"Retrieving code after being used...")
            used_code = await ActivationCode.get_by_code(code.code)
            if used_code:
                logger.info(f"Used code: {used_code}")
                logger.info(f"Used by: {used_code.used_by}")
                logger.info(f"Used at: {used_code.used_at}")
                
                # Delete for cleanup
                logger.info("Deleting test activation code...")
                delete_result = await used_code.delete()
                logger.info(f"Delete result: {delete_result}")
            else:
                logger.error("Could not retrieve used code")
        else:
            logger.error("Could not retrieve activation code")
    else:
        logger.error("Could not generate activation code")

async def run_tests():
    """Run all tests"""
    # Set up MongoDB connection
    db_setup = await setup_mongodb()
    if not db_setup:
        logger.error("MongoDB setup failed, tests cannot run")
        return
    
    # Run tests
    await test_premium_subscription()
    await test_activation_code()
    
    logger.info("\n--- All tests completed ---")

if __name__ == "__main__":
    # Run the tests
    asyncio.run(run_tests())