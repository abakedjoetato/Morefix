"""
Main module for the Discord bot.
This file directly runs the bot without any web server components.
"""

import os
import sys
import logging
import asyncio
import discord
from bot import Bot
import traceback
from dotenv import load_dotenv

# Set up logging from our custom module
from utils.logging_setup import setup_logging
setup_logging()

logger = logging.getLogger("main")

# Load environment variables
load_dotenv()

# Apply comprehensive compatibility patches for py-cord 2.6.1
logger.info("Applying comprehensive py-cord 2.6.1 compatibility patches...")
try:
    # Import and apply all compatibility patches from our centralized layer
    from utils.discord_compat import patch_all, PYCORD_VERSION
    patch_success = patch_all()
    logger.info(f"Discord patches applied: {patch_success}, detected version: {PYCORD_VERSION}")
    
    # Set up database connection (will be used by SafeDocument)
    from utils.safe_mongodb import set_database
    
    # Apply MongoDB connection to the global instance
    async def setup_mongodb():
        mongodb_uri = os.environ.get("MONGODB_URI")
        if not mongodb_uri:
            logger.error("MONGODB_URI not set in environment variables")
            return False
            
        try:
            # Import Motor and set up connection
            from motor.motor_asyncio import AsyncIOMotorClient
            
            # Create client and connect to database
            client = AsyncIOMotorClient(mongodb_uri)
            db = client.get_default_database()
            
            # Set the global database instance
            set_database(db)
            logger.info("MongoDB connection established successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            logger.error(traceback.format_exc())
            return False
    
    # We'll call setup_mongodb later in the startup process
    
except Exception as e:
    logger.error(f"Failed to apply compatibility patches: {e}")
    logger.error(traceback.format_exc())
    # Continue anyway - some features might still work

# List of required environment variables
REQUIRED_ENVS = [
    "DISCORD_TOKEN",
    "MONGODB_URI",
]

def check_environment():
    """Check if all required environment variables are present."""
    logger.info("Checking environment variables...")
    missing = []
    
    for env in REQUIRED_ENVS:
        if not os.environ.get(env):
            missing.append(env)
    
    if missing:
        logger.critical(f"Missing required environment variables: {', '.join(missing)}")
        return False
    
    logger.info("All required environment variables are present")
    return True

# Bot instance that will be used throughout the application
bot = None

async def load_extensions(bot_instance):
    """Load all cog extensions."""
    # List of cogs to load - core functionality
    cogs = [
        "cogs.admin",
        "cogs.general"
    ]
    
    # Optional cogs - won't fail if missing
    optional_cogs = [
        "cogs.bounties",
        # "cogs.new_csv_processor",  # Has issues with ServerIdentity import
        # "cogs.economy",          # Has dependency on premium system, re-enable later
        "cogs.events",             # Fixed - Added CSV_FIELDS and EVENT_PATTERNS to config
        "cogs.factions",           # Fixed - Fixed premium_tier_required import path
        "cogs.guild_settings",
        "cogs.killfeed",     # Fixed hybrid_group command compatibility
        "cogs.log_processor",  # Fixed Choice class to support subscriptability
        "cogs.player_links",
        # For now, let's keep these disabled until further testing
        "cogs.premium_new_updated", # Fixed - Updated premium features with compatibility layers
        "cogs.stats_fixed",   # Fixed - Renamed stats command to avoid name conflict
        "cogs.stats_premium_fix_compat", # Fixed - Premium verification functionality 
        "cogs.help",          # Fixed - Renamed commands method to commands_command
        "cogs.setup_fixed",   # Fixed - Added compatibility with py-cord 2.6.1 guild_only
        "cogs.rivalries_fixed" # Fixed - Added compatibility with py-cord 2.6.1 app_commands
    ]
    
    # Cogs with known issues that need to be fixed or are redundant
    # These are kept here for documentation, but we won't try to load them
    problematic_cogs = [
        # "cogs.help",            # Fixed - Renamed commands method to commands_command
        # "cogs.log_processor",   # Fixed - Choice class now supports subscriptability
        # "cogs.events",          # Fixed - Added CSV_FIELDS and EVENT_PATTERNS to config
        # "cogs.factions",        # Fixed - Fixed premium_tier_required import path
        "cogs.premium_new",       # Fixed - Updated as premium_new_updated with proper indentation
        "cogs.premium_new_fixed", # Fixed - Dependencies issues resolved and using updated premium_new_updated
        "cogs.rivalries",         # Fixed - Added compatibility with py-cord 2.6.1 app_commands
        "cogs.setup",             # Fixed - Added compatibility with py-cord 2.6.1 guild_only
        "cogs.stats",             # Fixed - Command name conflict fixed by renaming to game_stats
        "cogs.stats_premium_fix"  # Fixed - Reimplemented as stats_premium_fix_compat with setup function
    ]
    
    # Load required cogs
    for cog in cogs:
        try:
            await bot_instance.load_extension_async(cog)
        except Exception as e:
            logger.error(f"Failed to load required extension {cog}: {e}")
            logger.error(traceback.format_exc())
            return False
    
    # Load optional cogs
    for cog in optional_cogs:
        try:
            await bot_instance.load_extension_async(cog)
        except Exception as e:
            logger.error(f"Optional extension not available: {cog}: {e}")
    
    # Log the problematic cogs that we're intentionally not loading
    for cog in problematic_cogs:
        logger.warning(f"Skipping known problematic cog: {cog}")
    
    return True

async def start_bot():
    """Initialize and start the bot."""
    global bot
    
    if not check_environment():
        return False
    
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        logger.critical("DISCORD_TOKEN environment variable not set")
        return False
    
    # Check if we're in development mode (no Discord API connection)
    dev_mode = os.environ.get("DISCORD_DEV_MODE", "false").lower() == "true"
    
    try:
        # Check if bot instance already exists
        if bot is not None:
            logger.info("Bot instance already exists, not creating a new one")
            return True
        
        # Set up MongoDB first (for SafeDocument)
        mongodb_success = await setup_mongodb()
        if not mongodb_success:
            logger.critical("Failed to initialize MongoDB connection. Bot cannot start!")
            return False
        
        # Create bot instance
        bot = Bot(production=not dev_mode)
        
        # Initialize database in bot as well (for backwards compatibility)
        db_success = await bot.init_db()
        if not db_success:
            logger.critical("Failed to initialize database. Bot cannot start!")
            return False
        
        # Load extensions
        extensions_loaded = await load_extensions(bot)
        if not extensions_loaded:
            logger.critical("Failed to load required extensions. Bot cannot start!")
            return False
        
        # If in development mode, don't connect to Discord
        if dev_mode:
            logger.info("Bot initialized in DEVELOPMENT mode - not connecting to Discord API")
            # For development mode, we'll just simulate the bot running by waiting indefinitely
            logger.info("Simulating bot running in development mode")
            # Just sleep for a while to simulate the bot running, then return
            await asyncio.sleep(5)
            return True
        else:
            # Start the bot with real Discord connection
            logger.info("Starting bot with Discord connection...")
            await bot.start(token)
        
    except Exception as e:
        logger.critical(f"Failed to start bot: {e}")
        logger.critical(traceback.format_exc())
        return False
    
    return True

# This is a simple heartbeat function to keep the Replit alive
def heartbeat():
    """Periodically log a heartbeat message to show the bot is still running."""
    import time
    
    while True:
        logger.info("Discord bot heartbeat - still running")
        time.sleep(300)  # Log every 5 minutes

# Run when script is executed directly
if __name__ == "__main__":
    # Run Discord bot directly
    try:
        # Print a clear message indicating this is running without a web server
        print("=" * 60)
        print("  TOWER OF TEMPTATION BOT")
        print("  Running in direct execution mode without any web server")
        print("=" * 60)
        
        # Start heartbeat in a separate thread
        import threading
        heartbeat_thread = threading.Thread(target=heartbeat, daemon=True)
        heartbeat_thread.start()
        
        # Run the bot
        asyncio.run(start_bot())
    except KeyboardInterrupt:
        print("Bot stopped by user")
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
        logger.critical(traceback.format_exc())