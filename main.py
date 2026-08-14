import sys
import os

# Set UTF-8 encoding for console logs on WispByte hosting
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from bot import bot
import config

if __name__ == "__main__":
    token = config.DISCORD_TOKEN.strip()
    if not token:
        print("❌ ERROR: DISCORD_TOKEN environment variable is missing or empty!")
        print("Please add DISCORD_TOKEN in your Railway project -> Variables tab.")
        sys.exit(1)

    print(f"🚀 Starting Critical Ops Discord Bot...")
    print(f"🆔 App ID: {config.DISCORD_APP_ID}")
    print(f"📌 Leaderboard Channel: {config.LEADERBOARD_CHANNEL_ID}")
    
    bot.run(token)


