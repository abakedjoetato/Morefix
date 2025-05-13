"""
Discord Bot Launcher

This script launches the Tower of Temptation Discord bot with all compatibility layers.
"""

import os
import logging
import asyncio
from typing import Dict, Any, Optional

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

# Import compatibility integration
from bot_integration import (
    setup_mongodb,
    setup_discord,
    register_command,
    register_cog,
    run_bot,
    get_bot_info
)

async def setup_and_run():
    """Set up the bot and run it."""
    # Check for required environment variables
    mongodb_uri = os.environ.get('MONGODB_URI')
    discord_token = os.environ.get('DISCORD_TOKEN')
    
    if not mongodb_uri:
        logger.error("MONGODB_URI environment variable is required.")
        return False
        
    if not discord_token:
        logger.error("DISCORD_TOKEN environment variable is required.")
        return False
        
    # Set up MongoDB
    mongodb_success = setup_mongodb(
        connection_string=mongodb_uri,
        database_name=os.environ.get('MONGODB_DATABASE', 'toweroftemptation')
    )
    
    if not mongodb_success:
        logger.error("Failed to set up MongoDB. Check your connection string.")
        return False
        
    # Set up Discord
    discord_success = setup_discord(
        token=discord_token,
        intents=None  # Will use default intents from intent_helpers
    )
    
    if not discord_success:
        logger.error("Failed to set up Discord. Check your token.")
        return False
        
    # Import and register cogs
    try:
        # Import dynamically to avoid circular imports
        import importlib
        import pathlib
        
        cogs_path = pathlib.Path('cogs')
        if cogs_path.exists() and cogs_path.is_dir():
            for cog_file in cogs_path.glob('*.py'):
                # Skip __init__.py and other special files
                if cog_file.name.startswith('__'):
                    continue
                    
                cog_name = cog_file.stem
                try:
                    # Import the cog module
                    cog_module = importlib.import_module(f'cogs.{cog_name}')
                    
                    # Look for classes that might be cogs (end with 'Cog')
                    for attr_name in dir(cog_module):
                        if attr_name.endswith('Cog'):
                            cog_class = getattr(cog_module, attr_name)
                            if isinstance(cog_class, type):
                                # Register the cog
                                register_cog(cog_class)
                                logger.info(f"Registered cog: {attr_name}")
                except Exception as e:
                    logger.error(f"Error loading cog {cog_name}: {e}")
    except Exception as e:
        logger.error(f"Error loading cogs: {e}")
        
    # Log bot info
    bot_info = get_bot_info()
    logger.info(f"Bot info: {bot_info}")
    
    # Run the bot
    await run_bot()
    return True

def main():
    """Main entry point."""
    try:
        asyncio.run(setup_and_run())
    except KeyboardInterrupt:
        logger.info("Bot shutdown by user")
    except Exception as e:
        logger.error(f"Error running bot: {e}", exc_info=True)

if __name__ == "__main__":
    main()