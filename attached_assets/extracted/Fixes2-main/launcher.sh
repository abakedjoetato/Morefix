#!/usr/bin/env bash
# Launcher script for Tower of Temptation Discord Bot
# This script is executed by app.py to start the bot in Replit

# Exit on error
set -e

echo "Tower of Temptation Discord Bot Launcher"
echo "========================================"
echo "Starting bot at $(date)"

# Make sure the script is executable
chmod +x run.py

# Start the bot
echo "Executing main bot script..."
python3 run.py

# If we get here, the bot has exited
echo "Bot process has terminated at $(date)"