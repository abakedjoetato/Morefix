"""
Enhanced entry point for Replit to start the Discord bot

This version includes additional compatibility fixes and error handling
for issues with py-cord 2.6.1 and different library versions.
"""

import os
import sys
import subprocess
import time
import signal
import logging
import traceback

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log')
    ]
)
logger = logging.getLogger("app_enhanced")

# Discord bot process
bot_process = None

def start_discord_bot():
    """
    Start the Discord bot in a subprocess with improved error handling
    """
    global bot_process
    
    try:
        logger.info("Starting Discord bot with enhanced compatibility...")
        
        # Set environment variables for compatibility
        env = os.environ.copy()
        
        # Run the bot using our main.py directly
        cmd = ["python", "main.py"]
        
        logger.info(f"Running command: {' '.join(cmd)}")
        bot_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            env=env,
            preexec_fn=os.setsid
        )
        
        # Create a thread to continuously read and log output
        import threading
        
        def log_output():
            """Function to continuously read and log output from the bot process"""
            startup_lines = 0
            max_startup_lines = 20
            try:
                logger.info("Bot starting - showing output...")
                # Check if stdout is valid
                if bot_process and bot_process.stdout:
                    for line in iter(bot_process.stdout.readline, ''):
                        sys.stdout.write(line)
                        sys.stdout.flush()
                        startup_lines += 1
                        if startup_lines == max_startup_lines:
                            logger.info("Bot startup proceeding - further logs will be in bot.log")
                else:
                    logger.warning("Bot process stdout not available for logging")
            except Exception as e:
                logger.error(f"Error reading bot output: {e}")
                
        # Start the output logging thread
        output_thread = threading.Thread(target=log_output, daemon=True)
        output_thread.start()
        
        # Log a message indicating the bot is running
        logger.info("Bot startup initiated - check bot.log for details")
        
        # Don't wait for process to complete - we want it to keep running
        logger.info("Discord bot process is now running in the background")
        logger.info("Monitor the bot.log file for ongoing logs")
            
    except Exception as e:
        logger.error(f"Failed to start Discord bot process: {e}")
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
    # Print banner
    print("=" * 60)
    print("  TOWER OF TEMPTATION DISCORD BOT (Enhanced Entry Point)")
    print("  Starting Discord bot with py-cord 2.6.1 compatibility fixes")
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