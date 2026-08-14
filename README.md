# 🎮 Critical Ops Discord Bot

A Discord Bot built in Python (`discord.py` v2) for Critical Ops players. Featuring `/search` profiles, `/snipe` player tracking, and automatic **Spec Ops+ Leaderboard Tracking** in channel ID `1537846978300354822`.

---

## ✨ Features

### 1. `/search ign`
Displays a clean, dark-mode **Blue Embed** with detailed player statistics:
- **In-Game Name (IGN)** & **User ID**
- **Rank & Rating** (Spec Ops, Elite Ops, Master, etc.)
- **Kills / Deaths & K/D Ratio**
- **Peak Rating & Lowest Rating** (This ranked season)
- **Account Creation Year & Account Age**
- **Account Level**
- **Footer**: `made by powm`

### 2. `/snipe ign`
Allows you to target and monitor any player's online and match status:
- Sends real-time DM/channel ping when target enters a ranked match:  
  `@user Player x is currenly in ranked score (x/y)`
- Sends alert when match finishes:  
  `@user Player x has ended the ranked game score (x/y)`
- **Footer**: `made by pown`

### 3. Automated Spec Ops+ Leaderboard Tracker
- Automatically broadcasts live updates in **Green Embeds** to target channel ID `1537846978300354822`.
- Tracks all Spec Ops and Elite Ops players.
- Formats:
  - **Elite Ops**: `Player: #15 → #13, 1990 → 1996 (+6) (x-x)`
  - **Spec Ops**: `Player: 1812 → 1820 (+8) (x-x)`
  - **Promotions**: Appends `(new)` when a player advances from Master to Spec Ops.

---

## 🚀 How to Setup & Run

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Bot Token & Settings
Create a `.env` file in the project folder (or edit `config.py`):
```env
DISCORD_TOKEN=your_actual_discord_bot_token
LEADERBOARD_CHANNEL_ID=1537846978300354822
```

### 3. Start the Bot
```bash
python bot.py
```

---

## 🛠️ Requirements & Discord Developer Portal Setup
1. Go to [Discord Developer Portal](https://discord.com/developers/applications).
2. Create an App & Bot.
3. Enable **Message Content Intent** under Bot settings.
4. Invite the bot to your server with `applications.commands` and `bot` permissions.

---
*Created with ❤️ for powm / pown*
