import discord
from discord import app_commands
from discord.ext import commands, tasks
import asyncio
import os
import config
from cops_api import cops_api_client
from cops_tracker import snipe_tracker, leaderboard_tracker

class CriticalOpsBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print("[BOT] Slash commands synchronized successfully.")
        
        if not background_tracking_loop.is_running():
            background_tracking_loop.start(self)

bot = CriticalOpsBot()

@bot.event
async def on_ready():
    print(f"==========================================")
    print(f"[BOT LOGGED IN] {bot.user.name} ({bot.user.id})")
    print(f"[TARGET CHANNEL ID] {config.LEADERBOARD_CHANNEL_ID}")
    print(f"==========================================")
    await bot.change_presence(activity=discord.Game(name="Critical Ops | /search /snipe /leaderboard"))
    
    # Send online status message to channel 1537846978300354822 so user knows tracker is active
    try:
        channel = bot.get_channel(config.LEADERBOARD_CHANNEL_ID)
        if channel:
            embed = discord.Embed(
                title="SPEC OPS+ LEADERBOARD TRACKER ONLINE",
                description="Bot has connected to Critical Ops live database. Actively monitoring Spec Ops+ & Elite Ops player rank changes...",
                color=discord.Color.blue()
            )
            embed.set_footer(text="made by pown • Auto Leaderboard Tracking")
            await channel.send(embed=embed)
    except Exception as e:
        print(f"[ON_READY WARNING] Could not send startup message: {e}")

# ==================== SLASH COMMANDS ====================

@bot.tree.command(name="search", description="Search real Critical Ops player profile stats")
@app_commands.describe(ign="In-Game Name (IGN) to search")
async def search(interaction: discord.Interaction, ign: str):
    """
    /search ign
    Clean Blue Embed with profile stats, K/D, ratings, level, account age.
    Footer: made by powm
    """
    await interaction.response.defer()
    
    player = await cops_api_client.get_player_by_ign(ign)
    if not player:
        await interaction.followup.send(f"Player **{ign}** was not found in Critical Ops database.", ephemeral=True)
        return

    embed = discord.Embed(
        title=f"Critical Ops Player Profile: {player['ign']}",
        color=discord.Color.blue()
    )
    
    embed.add_field(name="IGN", value=f"`{player['ign']}`", inline=True)
    embed.add_field(name="Account ID", value=f"`{player['id']}`", inline=True)
    embed.add_field(name="Rank & Rating", value=f"**{player['rank']}** ({player['rating']:,} Rating)", inline=True)
    
    embed.add_field(name="Kills / Deaths", value=f"{player['kills']:,} / {player['deaths']:,} (K/D: **{player['kd_ratio']}**)", inline=False)
    embed.add_field(name="Peak / Lowest Rating", value=f"Peak: **{player['peak_rating']:,}** | Lowest: **{player['lowest_rating']:,}**", inline=False)
    embed.add_field(name="Account Age", value=f"{player['account_age_str']}", inline=True)
    embed.add_field(name="Level", value=f"Level **{player['level']}**", inline=True)
    
    embed.set_footer(text="made by powm")
    
    await interaction.followup.send(embed=embed)


@bot.tree.command(name="snipe", description="Snipe and track a player's active ranked match status")
@app_commands.describe(ign="In-Game Name (IGN) to snipe")
async def snipe(interaction: discord.Interaction, ign: str):
    """
    /snipe ign
    Tracks player and notifies when they are in game ranked with score (x/y).
    Footer signature: made by pown
    """
    user_id = interaction.user.id
    
    player = await cops_api_client.get_player_by_ign(ign)
    display_name = player["ign"] if player else ign

    snipe_tracker.add_target(user_id, display_name)

    embed = discord.Embed(
        title="Player Snipe Activated",
        description=f"Now actively sniping **{display_name}**!\nYou will receive automated alerts when they enter or finish a ranked game.",
        color=discord.Color.dark_purple()
    )
    embed.set_footer(text="made by pown")
    
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="leaderboard", description="Show official Critical Ops Leaderboard (Elite 1 down to Spec Ops 1800+)")
@app_commands.describe(page="Page number (1-3)")
async def leaderboard(interaction: discord.Interaction, page: int = 1):
    """
    /leaderboard
    Displays live real-time Leaderboard of top Elite Ops & Spec Ops players.
    Footer: made by pown
    """
    await interaction.response.defer()
    
    page = max(1, page)
    leaderboard_players = await cops_api_client.get_spec_ops_leaderboard()
    
    if not leaderboard_players:
        await interaction.followup.send("Could not retrieve Critical Ops Leaderboard at this time.", ephemeral=True)
        return

    per_page = 10
    total_pages = (len(leaderboard_players) + per_page - 1) // per_page
    page = min(page, max(1, total_pages))
    
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    page_entries = leaderboard_players[start_idx:end_idx]

    description_lines = []
    for p in page_entries:
        pos = p.get("rank_position")
        pos_str = f"#{pos}" if pos else "#"
        description_lines.append(f"**{pos_str}** {p['ign']} — **{p['rank']}** ({p['rating']:,} Rating)")

    embed = discord.Embed(
        title="CRITICAL OPS LEADERBOARD",
        description="\n".join(description_lines),
        color=discord.Color.gold()
    )
    embed.set_footer(text=f"Page {page}/{total_pages} • made by pown")
    
    await interaction.followup.send(embed=embed)

# ==================== BACKGROUND TRACKING ====================

@tasks.loop(seconds=config.SNIPE_CHECK_INTERVAL)
async def background_tracking_loop(bot_instance: commands.Bot):
    try:
        # 1. Process Snipe Alerts
        snipe_alerts = await snipe_tracker.check_snipes(bot_instance)
        for alert in snipe_alerts:
            user = bot_instance.get_user(alert["user_id"])
            if user:
                try:
                    await user.send(alert["message"])
                except Exception:
                    pass

        # 2. Process Spec Ops+ Leaderboard Updates
        leaderboard_updates = await leaderboard_tracker.check_updates()
        if leaderboard_updates:
            target_channel = bot_instance.get_channel(config.LEADERBOARD_CHANNEL_ID)
            if target_channel:
                description_text = "\n".join(leaderboard_updates)
                
                embed = discord.Embed(
                    title="SPEC OPS+ LEADERBOARD TRACKER",
                    description=description_text,
                    color=discord.Color.green()
                )
                embed.set_footer(text="made by pown • Auto Leaderboard Tracking")
                
                await target_channel.send(embed=embed)

    except Exception as e:
        print(f"[BACKGROUND LOOP ERROR] {e}")

@background_tracking_loop.before_loop
async def before_tracking_loop():
    await bot.wait_until_ready()

if __name__ == "__main__":
    token = config.DISCORD_TOKEN
    bot.run(token)
