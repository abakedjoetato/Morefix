# How to Run Tower of Temptation Discord Bot

This document provides instructions for running the Tower of Temptation Discord Bot on Replit.

## Prerequisites

Before running the bot, make sure you have the following:

1. A Discord bot token (stored in the DISCORD_TOKEN environment variable)
2. A MongoDB connection string (stored in the MONGODB_URI environment variable)

## Running the Bot

There are multiple ways to run the bot:

### Method 1: Using start.sh

Run the following command:

```bash
./start.sh
```

This will start the Discord bot using the enhanced app entry point.

### Method 2: Using app_enhanced.py directly

Run the following command:

```bash
python app_enhanced.py
```

This will start the Discord bot with improved error handling.

### Method 3: Using run.py

Run the following command:

```bash
python run.py
```

This provides an additional wrapper with monitoring capabilities.

## Monitoring

The bot logs information to:

- `app.log` - Main application log
- `bot.log` - Bot-specific logging
- `run.log` - Runner process logging

## Troubleshooting

If the bot fails to start:

1. Check the log files for specific errors
2. Verify that DISCORD_TOKEN and MONGODB_URI are correctly set
3. Make sure all dependencies are installed

## Compatibility

The bot is compatible with py-cord 2.6.1. The compatibility patches in `utils/discord_patches.py` ensure that cogs using discord.py style imports will work with py-cord.