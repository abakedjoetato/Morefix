"""
Main entry point for running the Discord bot with enhanced compatibility

This script launches the Discord bot using the enhanced app version
which includes better error handling and compatibility with py-cord 2.6.1.
"""

import os
import logging
import sys
from app_enhanced import start_discord_bot

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot.log')
    ]
)

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("Starting Discord bot via enhanced app...")
    
    # Run the bot with the enhanced launcher
    start_discord_bot()