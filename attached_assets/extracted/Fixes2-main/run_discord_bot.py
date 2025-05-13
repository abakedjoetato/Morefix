"""
Discord Bot Runner

This script starts the Discord bot with proper environment setup and error handling.
"""
import os
import sys
import logging
import traceback
from datetime import datetime
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('bot.log')
    ]
)
logger = logging.getLogger(__name__)

def main():
    """Main entry point for starting the Discord bot"""
    try:
        # Load environment variables
        load_dotenv()
        
        # Set log level from environment
        log_level = os.environ.get('LOG_LEVEL', 'INFO')
        numeric_level = getattr(logging, log_level.upper(), None)
        if isinstance(numeric_level, int):
            logging.getLogger().setLevel(numeric_level)
        
        logger.info(f"Starting Discord bot at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"Log level set to: {log_level}")
        
        # Check for dev mode
        dev_mode = os.environ.get('DISCORD_DEV_MODE', 'false').lower() == 'true'
        if dev_mode:
            logger.info("Running in DEVELOPMENT mode - Discord API connectivity disabled")
        
        # Check for SFTP mode
        sftp_enabled = os.environ.get('SFTP_ENABLED', 'false').lower() == 'true'
        logger.info(f"SFTP functionality is {'enabled' if sftp_enabled else 'disabled'}")
        
        # Run the bot by importing main module
        import main
        # The main module handles the actual bot startup
        
    except ImportError as e:
        logger.critical(f"Failed to import required modules: {e}")
        logger.critical(traceback.format_exc())
        sys.exit(1)
    except Exception as e:
        logger.critical(f"Failed to start Discord bot: {e}")
        logger.critical(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()