"""
Logging setup for the Discord bot

This module provides consistent logging configuration for different components
of the Discord bot.
"""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler
import datetime

# Configure default log levels for different loggers
DEFAULT_LOG_LEVEL = logging.INFO
BOT_LOG_LEVEL = logging.INFO
DISCORD_LOG_LEVEL = logging.WARNING  # py-cord is quite verbose at INFO level
PYMONGO_LOG_LEVEL = logging.WARNING  # MongoDB driver can be quite verbose at INFO level

# Log file configuration
LOG_FILE = "bot.log"
MAX_LOG_SIZE = 5 * 1024 * 1024  # 5MB
BACKUP_COUNT = 3

# Log format
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Keep track of whether setup has been run
_setup_complete = False

def setup_logging():
    """
    Set up logging for the Discord bot
    
    This function sets up a consistent logging configuration for the bot, including:
    - Console output with colored logging
    - File output with rotation
    - Different log levels for different components
    
    Returns:
        bool: True if setup was completed, False if it was already done
    """
    global _setup_complete
    
    # Only run setup once
    if _setup_complete:
        return False
    
    # Create the logs directory if it doesn't exist
    log_dir = os.path.dirname(LOG_FILE)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Set up root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(DEFAULT_LOG_LEVEL)
    
    # Clear existing handlers to avoid duplicates on reloads
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create formatters
    console_formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
    file_formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(DEFAULT_LOG_LEVEL)
    
    # Create file handler with rotation
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=MAX_LOG_SIZE,
        backupCount=BACKUP_COUNT,
        encoding='utf-8'
    )
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(DEFAULT_LOG_LEVEL)
    
    # Add handlers to root logger
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    # Configure specific loggers
    configure_logger("discord", DISCORD_LOG_LEVEL)
    configure_logger("discord.http", DISCORD_LOG_LEVEL)
    configure_logger("discord.gateway", DISCORD_LOG_LEVEL)
    configure_logger("discord.client", DISCORD_LOG_LEVEL)
    configure_logger("pymongo", PYMONGO_LOG_LEVEL)
    configure_logger("motor", PYMONGO_LOG_LEVEL)
    
    # Configure our custom loggers
    configure_logger("bot", BOT_LOG_LEVEL)
    configure_logger("cogs", BOT_LOG_LEVEL)
    configure_logger("utils", BOT_LOG_LEVEL)
    
    # Log a startup message
    root_logger.info(f"Logging initialized at {datetime.datetime.now()}")
    
    _setup_complete = True
    return True

def configure_logger(name, level):
    """
    Configure a specific logger with a custom level
    
    Args:
        name: The name of the logger
        level: The logging level to set
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Explicitly enable propagation to parent loggers
    logger.propagate = True