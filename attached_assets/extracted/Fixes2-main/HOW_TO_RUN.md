# How to Run the Tower of Temptation Discord Bot

## Quick Start
Press the "Run" button at the top of the Replit interface. This will:
1. Start the Discord bot through app.py
2. Handle all dependencies automatically
3. Connect to Discord with your configured bot token

## Monitoring
- The bot will log basic startup information to the console
- Detailed logs are written to `bot.log`
- The bot will indicate if it's running properly or if there are issues

## Manual Start Options
You can also start the bot manually using any of these methods:

1. Using the run_discord_bot.sh script:
   ```bash
   bash run_discord_bot.sh
   ```

2. Using Python directly:
   ```bash
   python app.py
   ```

## Troubleshooting
- Check `bot.log` for detailed error messages
- Ensure both DISCORD_TOKEN and MONGODB_URI environment variables are set
- If the bot crashes, it will automatically restart