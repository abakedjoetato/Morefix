#!/bin/bash

# Discord Bot Launcher Script
# 
# This script launches the Tower of Temptation Discord bot with proper
# environment setup and error handling.

# Log file
LOG_FILE="bot.log"

# Clear log file
: > $LOG_FILE

# Function to log messages
log() {
  local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
  echo "[$timestamp] $1" | tee -a $LOG_FILE
}

# Check for MongoDB URI
if [ -z "$MONGODB_URI" ]; then
  log "ERROR: MONGODB_URI environment variable is not set."
  log "Please set the MONGODB_URI environment variable."
  exit 1
fi

# Check for Discord token
if [ -z "$DISCORD_TOKEN" ]; then
  log "ERROR: DISCORD_TOKEN environment variable is not set."
  log "Please set the DISCORD_TOKEN environment variable."
  exit 1
fi

# Install dependencies if not already installed
if [ ! -f ".env_setup_complete" ]; then
  log "Installing dependencies..."
  python -m pip install -r requirements_clean.txt
  
  if [ $? -eq 0 ]; then
    log "Dependencies installed successfully."
    touch .env_setup_complete
  else
    log "ERROR: Failed to install dependencies."
    exit 1
  fi
fi

# Run the bot
log "Starting Discord bot..."
python run_discord_bot.py

# Check exit code
if [ $? -ne 0 ]; then
  log "ERROR: Bot exited with an error."
  exit 1
fi

log "Bot shutdown successfully."
exit 0