"""
Discord Bot Launcher

This module provides a launcher for the Discord bot with proper integration
and compatibility across different Discord library versions.
"""

import os
import sys
import logging
import asyncio
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Import bot integration
try:
    from bot_integration import create_bot, setup_bot
except ImportError as e:
    logger.error(f"Failed to import bot integration: {e}")
    logger.error("Please ensure bot_integration.py exists and all dependencies are installed.")
    sys.exit(1)

async def main(token: Optional[str] = None) -> None:
    """
    Main function to start the bot.
    
    Args:
        token: Discord bot token (overrides environment variable)
    """
    # Get token from arguments or environment
    token = token or os.environ.get('DISCORD_TOKEN')
    
    if not token:
        logger.error("No Discord token provided. Please set the DISCORD_TOKEN environment variable.")
        sys.exit(1)
    
    # Create and set up the bot
    try:
        bot = create_bot(token)
        await setup_bot(bot)
    except Exception as e:
        logger.error(f"Error setting up bot: {e}")
        sys.exit(1)
    
    # Start the bot
    try:
        await bot.start()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Error running bot: {e}")
    finally:
        # Ensure the bot is closed properly
        try:
            await bot.close()
        except Exception as e:
            logger.error(f"Error closing bot: {e}")

if __name__ == "__main__":
    # Get token from command line if provided
    token = None
    if len(sys.argv) > 1:
        token = sys.argv[1]
    
    # Run the bot
    asyncio.run(main(token))