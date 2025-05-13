"""
Logging Setup Module

This module configures the logging system for the Discord bot.
It sets up logging levels, formatters, and handlers.
"""

import os
import logging
import logging.handlers
import sys
from typing import Optional

def setup_logging(log_level: Optional[str] = None, log_file: Optional[str] = None):
    """
    Set up logging configuration.
    
    Args:
        log_level: Logging level (default: from env var or INFO)
        log_file: Log file path (default: from env var or bot.log)
    """
    # Get log level from environment or parameter
    log_level = log_level or os.environ.get("LOG_LEVEL", "INFO")
    
    # Get numeric log level
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        print(f"Invalid log level: {log_level}, defaulting to INFO")
        numeric_level = logging.INFO
        
    # Get log file path
    log_file = log_file or os.environ.get("LOG_FILE", "bot.log")
    
    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Remove existing handlers (in case this is called multiple times)
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create formatters
    file_formatter = logging.Formatter(
        '%(asctime)s [%(name)s:%(levelname)s] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    console_formatter = logging.Formatter(
        '%(asctime)s,%(msecs)f [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(numeric_level)
    
    # Create file handler
    try:
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=5 * 1024 * 1024,  # 5 MB
            backupCount=5
        )
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(numeric_level)
        
        # Add handlers to root logger
        root_logger.addHandler(file_handler)
    except (IOError, PermissionError) as e:
        print(f"Warning: Could not create log file at {log_file}: {e}")
        print("Logging to console only")
    
    # Always add console handler
    root_logger.addHandler(console_handler)
    
    # Adjust logging for specific libraries 
    logging.getLogger('discord').setLevel(logging.WARNING)
    logging.getLogger('discord.http').setLevel(logging.WARNING)
    logging.getLogger('websockets').setLevel(logging.WARNING)
    logging.getLogger('chardet').setLevel(logging.WARNING)
    
    # Log startup message
    root_logger.info(f"Logging initialized at level {log_level}")