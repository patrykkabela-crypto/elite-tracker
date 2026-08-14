import sys
import os

# Set UTF-8 encoding for console logs on WispByte hosting
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from bot import bot
import config

if __name__ == "__main__":
    print(f"🚀 Starting Critical Ops Discord Bot on WispByte Hosting...")
    print(f"🆔 App ID: {config.DISCORD_APP_ID}")
    print(f"📌 Leaderboard Channel: {config.LEADERBOARD_CHANNEL_ID}")
    
    bot.run(config.DISCORD_TOKEN)
