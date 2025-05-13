#!/bin/bash

# Script to run the Discord bot with proper environment variables

# Check for MongoDB URI
if [ -z "$MONGODB_URI" ]; then
  echo "Error: MONGODB_URI environment variable is not set."
  echo "Please set it with: export MONGODB_URI=your_mongodb_connection_string"
  exit 1
fi

# Check for Discord token
if [ -z "$DISCORD_TOKEN" ]; then
  echo "Error: DISCORD_TOKEN environment variable is not set."
  echo "Please set it with: export DISCORD_TOKEN=your_discord_bot_token"
  exit 1
fi

# Set environment variables for development
export LOG_LEVEL=DEBUG
export ENVIRONMENT=development

# Check and install dependencies if needed
if [ ! -f ".env_setup_complete" ]; then
  echo "Setting up environment..."
  
  # Install dependencies
  pip install -r requirements_clean.txt
  
  # Mark as complete
  touch .env_setup_complete
  
  echo "Environment setup completed."
fi

# Run the bot
echo "Starting Discord bot..."
python run_discord_bot.py

# or use one of these for alternative entry points if needed
# python run.py
# python main.py