#!/usr/bin/env python3
"""
Main entry point for the Tower of Temptation Discord Bot

This script initializes and runs the Discord bot with proper error handling
and environment setup.
"""

import os
import sys
import asyncio
import logging
import traceback
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("bot.run")

# Load environment variables from .env file if it exists
if os.path.exists(".env"):
    load_dotenv()
    logger.info("Loaded environment variables from .env file")

# Check required environment variables
if not os.environ.get("DISCORD_TOKEN"):
    logger.error("DISCORD_TOKEN environment variable not set")
    print("Error: DISCORD_TOKEN environment variable not set.")
    print("Please set it with: export DISCORD_TOKEN=your_discord_bot_token")
    sys.exit(1)

if not os.environ.get("MONGODB_URI"):
    logger.error("MONGODB_URI environment variable not set")
    print("Error: MONGODB_URI environment variable not set.")
    print("Please set it with: export MONGODB_URI=your_mongodb_connection_string")
    sys.exit(1)

# Import bot after environment variables are loaded
try:
    from bot import Bot
    logger.info("Successfully imported Bot")
except ImportError as e:
    logger.error(f"Failed to import Bot: {e}")
    print(f"Error: Failed to import Bot: {e}")
    sys.exit(1)

async def main():
    """Main function to set up and run the bot"""
    
    logger.info("Initializing bot...")
    
    # Initialize the bot
    bot = Bot()
    
    # Register signal handlers for graceful shutdown
    try:
        import signal
        
        def handle_exit(sig, frame):
            """Handle exit signals"""
            logger.info(f"Received signal {sig}, shutting down...")
            asyncio.create_task(bot.close())
        
        signal.signal(signal.SIGINT, handle_exit)
        signal.signal(signal.SIGTERM, handle_exit)
        logger.info("Registered signal handlers for graceful shutdown")
    except (ImportError, NotImplementedError):
        logger.warning("Could not register signal handlers")
    
    # Start the bot
    try:
        logger.info("Starting bot...")
        await bot.start(os.environ["DISCORD_TOKEN"])
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        traceback.print_exc()
        sys.exit(1)
    finally:
        # Ensure bot is closed properly
        if bot and not bot.is_closed():
            await bot.close()
        
        logger.info("Bot has shut down")

if __name__ == "__main__":
    # Run the bot
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by keyboard interrupt")
    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
        traceback.print_exc()
        sys.exit(1)