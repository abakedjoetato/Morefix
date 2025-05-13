"""
Replit Run Script for Tower of Temptation Discord Bot
"""

import os
import sys
import time
import logging
import subprocess
import signal

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('run.log')
    ]
)
logger = logging.getLogger("run")

# Discord bot process
bot_process = None

def print_banner():
    """Print a banner at startup"""
    print("=" * 60)
    print("  TOWER OF TEMPTATION DISCORD BOT")
    print("  Starting bot via run.py - Replit workflow runner")
    print("  " + time.strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 60)

def start_bot():
    """Start the Discord bot process"""
    global bot_process
    
    try:
        # Start the bot using app_enhanced.py
        cmd = ["python", "app_enhanced.py"]
        
        # Run the process
        logger.info(f"Starting bot process with command: {' '.join(cmd)}")
        bot_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            preexec_fn=os.setsid
        )
        
        # Log output from the process
        if bot_process and bot_process.stdout:
            for line in bot_process.stdout:
                print(line, end='')
                sys.stdout.flush()
        else:
            logger.warning("Bot process stdout not available for logging")
        
        # If we get here, the process has terminated
        exit_code = bot_process.wait()
        logger.error(f"Bot process terminated with exit code: {exit_code}")
        
    except Exception as e:
        logger.error(f"Failed to start bot process: {e}")
        sys.exit(1)

def cleanup(signum, frame):
    """Clean up resources when the script is terminated"""
    global bot_process
    
    logger.info("Cleaning up resources...")
    
    if bot_process:
        try:
            # Terminate the bot process and all its children
            logger.info("Terminating bot process...")
            os.killpg(os.getpgid(bot_process.pid), signal.SIGTERM)
            bot_process.wait(timeout=5)
            logger.info("Bot process terminated")
        except Exception as e:
            logger.error(f"Failed to terminate bot process: {e}")
    
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, cleanup)
signal.signal(signal.SIGTERM, cleanup)

# Main entry point
if __name__ == "__main__":
    print_banner()
    start_bot()