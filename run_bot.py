"""
Simple script to run the Discord bot with development mode enabled
"""
import os
import sys
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Enable development mode
os.environ["DISCORD_DEV_MODE"] = "true"

# Import the start_bot function from main module
from main import start_bot

if __name__ == "__main__":
    print("Starting Discord bot in development mode...")
    print("This will initialize the bot without connecting to Discord API")
    asyncio.run(start_bot())
    print("Bot setup complete. Run 'python main.py' for production mode.")