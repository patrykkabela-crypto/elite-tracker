import os
from dotenv import load_dotenv

# Load environment variables from .env file if available
load_dotenv()

# Discord Bot Token & Application ID
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
DISCORD_APP_ID = os.getenv("DISCORD_APP_ID", "1537842692761985184")

# Target channel for automatic Spec Ops+ leaderboard tracking
LEADERBOARD_CHANNEL_ID = int(os.getenv("LEADERBOARD_CHANNEL_ID", "1537846978300354822"))

# Polling intervals in seconds
SNIPE_CHECK_INTERVAL = int(os.getenv("SNIPE_CHECK_INTERVAL", "15"))  # Check sniped players every 15 sec
LEADERBOARD_CHECK_INTERVAL = int(os.getenv("LEADERBOARD_CHECK_INTERVAL", "30"))  # Check leaderboard every 30 sec

# C-Ops API Endpoint (Optional custom proxy/endpoint configuration)
COPS_API_BASE_URL = os.getenv("COPS_API_BASE_URL", "https://api.criticalopsgame.com/v1")
COPS_API_KEY = os.getenv("COPS_API_KEY", "")
