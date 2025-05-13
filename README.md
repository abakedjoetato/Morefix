# Tower of Temptation Discord Bot

A Discord bot for the Tower of Temptation game, built with Python, Pycord, and MongoDB for data persistence.

## Important: Running Without Web Server

This bot runs directly without using any web server components (no Flask, no gunicorn). It uses a custom launcher system with process management and heartbeat mechanisms to keep the bot running.

## Setup Instructions

### Prerequisites

- Python 3.11+
- A Discord bot token
- MongoDB database (optional for testing with mock data)

### Environment Variables

Copy the `.env.example` file to a new file named `.env` and fill in your values:

```
# Discord Bot Configuration
DISCORD_TOKEN=your_discord_token_here
COMMAND_PREFIX=!

# MongoDB Configuration
MONGODB_URI=mongodb://username:password@host:port/database
DB_NAME=discordbot

# Logging Level: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL=INFO
```

### Running the Bot

There are several ways to run the bot:

#### Method 1: Directly with Python
```bash
python start_bot.py
```

#### Method 2: Using the Launcher Script
```bash
./launcher.sh
```

#### Method 3: Using the Keep Alive Script (Recommended for Replit)
```bash
python keep_alive.py
```

## Bot Features

- PvP statistics tracking
- Player rivalries
- Guild settings management
- Premium features
- Economy system
- Factions
- More features coming soon!

## Testing with Mock Data

If you don't have a MongoDB database, the bot includes a robust mocking system. Just leave the `MONGODB_URI` variable empty or use a placeholder value, and the bot will use mock data for testing.

## Discord Bot Token

You'll need to create a Discord bot and get a token. Instructions:

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" and give it a name
3. Go to the "Bot" tab and click "Add Bot"
4. Under the "TOKEN" section, click "Copy" to get your token
5. Add this token to your `.env` file

## Troubleshooting

- If you see "DISCORD_TOKEN not set" warnings, make sure you've properly set up your environment variables
- The bot logs extensive information to help with debugging
- Check the `bot.log` file for detailed logs

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.