"""
Minimal entry point for Replit to start the Discord bot

This file is just a shim to satisfy Replit's expectations
while launching the actual Discord bot process without Flask.
"""

import os
import sys
import subprocess
import time
import signal
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger("app")

# Discord bot process
bot_process = None

def start_discord_bot():
    """
    Start the Discord bot in a subprocess
    """
    global bot_process
    
    try:
        logger.info("Starting Discord bot from app.py shim...")
        # Run our existing launcher script
        bot_process = subprocess.Popen(
            ["bash", "run_discord_bot.sh"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            preexec_fn=os.setsid
        )
        
        # Log first few lines of output from bot process to show startup
        startup_lines = 0
        max_startup_lines = 20
        
        logger.info("Bot starting - showing first few lines of output...")
        for line in bot_process.stdout:
            sys.stdout.write(line)
            sys.stdout.flush()
            startup_lines += 1
            if startup_lines >= max_startup_lines:
                logger.info("Bot startup complete - further logs will be in bot.log")
                break
        
        # Don't wait for process to complete - we want it to keep running
        logger.info("Discord bot process is now running in the background")
        logger.info("Monitor the bot.log file for ongoing logs")
            
    except Exception as e:
        logger.error(f"Failed to start Discord bot process: {e}")
        import traceback
        logger.error(traceback.format_exc())

def cleanup(signum, frame):
    """
    Cleanup function to terminate the bot process when this script is stopped
    """
    global bot_process
    
    if bot_process:
        logger.info("Terminating Discord bot process...")
        try:
            os.killpg(os.getpgid(bot_process.pid), signal.SIGTERM)
            bot_process.wait(timeout=5)
            logger.info("Discord bot process terminated")
        except Exception as e:
            logger.error(f"Failed to terminate Discord bot process: {e}")
    
    # Exit this process
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, cleanup)
signal.signal(signal.SIGTERM, cleanup)

# Main entry point - Just start the Discord bot
if __name__ == "__main__":
    # This is a simple message to show in Replit's console
    print("=" * 60)
    print("  TOWER OF TEMPTATION DISCORD BOT (Replit Entry Point)")
    print("  Starting Discord bot without web server components")
    print("  " + time.strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 60)
    
    # Start the Discord bot
    start_discord_bot()
    
    # Keep this process alive
    try:
        logger.info("Main process entering monitor loop")
        
        # Check if bot process is still running
        iteration = 0
        while True:
            time.sleep(10)
            
            # Print a heartbeat message every minute (6 iterations)
            iteration += 1
            if iteration % 6 == 0:
                if bot_process and bot_process.poll() is None:
                    logger.info("Heartbeat: Discord bot is still running")
                else:
                    logger.warning("Heartbeat: Discord bot process has stopped!")
                    
                    # If bot process has stopped unexpectedly, restart it
                    if bot_process and bot_process.poll() is not None:
                        logger.info("Attempting to restart Discord bot process...")
                        start_discord_bot()
    except KeyboardInterrupt:
        cleanup(None, None)