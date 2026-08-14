import discord
from discord import app_commands
from discord.ext import commands, tasks
import asyncio
import config
from cops_api import cops_api_client
from cops_tracker import snipe_tracker, leaderboard_tracker


# ==================== PAGINATION VIEW ====================

class LeaderboardPaginationView(discord.ui.View):
    def __init__(self, players: list, per_page: int = 10):
        super().__init__(timeout=600)
        self.players = players
        self.per_page = per_page
        self.current_page = 1
        self.total_pages = max(1, (len(self.players) + self.per_page - 1) // self.per_page)
        self._update_buttons()

    def _update_buttons(self):
        self.first_button.disabled = (self.current_page <= 1)
        self.prev_button.disabled  = (self.current_page <= 1)
        self.next_button.disabled  = (self.current_page >= self.total_pages)
        self.last_button.disabled  = (self.current_page >= self.total_pages)

    def get_page_embed(self) -> discord.Embed:
        start = (self.current_page - 1) * self.per_page
        page  = self.players[start:start + self.per_page]

        lines = []
        for p in page:
            pos     = p.get("rank_position")
            pos_str = f"#{pos}" if pos else "#?"
            rating  = p.get("rating", 0)
            rank    = p.get("rank", "Unknown")
            ign     = p.get("ign", "?")
            lines.append(f"**{pos_str}** {p['ign']} — **{p['rating']:,}** Rating")

        embed = discord.Embed(
            title="CRITICAL OPS LEADERBOARD",
            description="\n".join(lines) if lines else "No players found.",
            color=discord.Color.gold()
        )
        embed.set_footer(
            text=f"Page {self.current_page}/{self.total_pages} — {len(self.players)} Elite Ops players • made by pown"
        )
        return embed

    @discord.ui.button(label="⏮ First",    style=discord.ButtonStyle.secondary, custom_id="lb_first")
    async def first_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = 1
        self._update_buttons()
        await interaction.response.edit_message(embed=self.get_page_embed(), view=self)

    @discord.ui.button(label="◀ Previous", style=discord.ButtonStyle.primary,   custom_id="lb_prev")
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 1:
            self.current_page -= 1
        self._update_buttons()
        await interaction.response.edit_message(embed=self.get_page_embed(), view=self)

    @discord.ui.button(label="Next ▶",    style=discord.ButtonStyle.primary,   custom_id="lb_next")
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page < self.total_pages:
            self.current_page += 1
        self._update_buttons()
        await interaction.response.edit_message(embed=self.get_page_embed(), view=self)

    @discord.ui.button(label="Last ⏭",   style=discord.ButtonStyle.secondary, custom_id="lb_last")
    async def last_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = self.total_pages
        self._update_buttons()
        await interaction.response.edit_message(embed=self.get_page_embed(), view=self)


# ==================== BOT ====================

class CriticalOpsBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # Register commands globally (takes ~1h to propagate)
        await self.tree.sync()
        print(f"[BOT] Global slash command sync complete.")

    async def on_ready(self):
        print(f"==========================================")
        print(f"[BOT LOGGED IN] {self.user.name} ({self.user.id})")
        print(f"[TARGET CHANNEL] {config.LEADERBOARD_CHANNEL_ID}")
        print(f"==========================================")

        await self.change_presence(
            activity=discord.Game(name="Critical Ops | /search /snipe /unsnipe /leaderboard")
        )

        # Instantly sync to the guild where the leaderboard channel lives
        try:
            channel = self.get_channel(config.LEADERBOARD_CHANNEL_ID)
            if channel and hasattr(channel, "guild"):
                guild = channel.guild
                self.tree.copy_global_to(guild=guild)
                synced = await self.tree.sync(guild=guild)
                print(f"[BOT] Instant guild sync to '{guild.name}': {len(synced)} commands.")
        except Exception as e:
            print(f"[BOT WARNING] Guild sync failed: {e}")

        # Send startup notification
        try:
            channel = self.get_channel(config.LEADERBOARD_CHANNEL_ID)
            if channel:
                embed = discord.Embed(
                    title="SPEC OPS+ LEADERBOARD TRACKER ONLINE",
                    description=(
                        "Bot has connected to Critical Ops live database.\n"
                        "Actively monitoring Spec Ops+ & Elite Ops player rank changes every 15 seconds..."
                    ),
                    color=discord.Color.blue()
                )
                embed.set_footer(text="made by pown • Auto Leaderboard Tracking")
                await channel.send(embed=embed)
        except Exception as e:
            print(f"[ON_READY WARNING] Startup message failed: {e}")

        # Start the background tracking loop
        if not background_tracking_loop.is_running():
            background_tracking_loop.start()
            print(f"[BOT] Background tracking loop started (interval: {config.SNIPE_CHECK_INTERVAL}s)")


bot = CriticalOpsBot()


# ==================== SLASH COMMANDS ====================

@bot.tree.command(name="search", description="Search a Critical Ops player profile")
@app_commands.describe(ign="Player In-Game Name (IGN)")
async def cmd_search(interaction: discord.Interaction, ign: str):
    await interaction.response.defer()
    player = await cops_api_client.get_player_by_ign(ign)
    if not player:
        await interaction.followup.send(f"Player **{ign}** not found in Critical Ops database.", ephemeral=True)
        return

    embed = discord.Embed(
        title=f"Critical Ops Player Profile: {player['ign']}",
        color=discord.Color.blue()
    )
    embed.add_field(name="IGN",              value=f"`{player['ign']}`",                              inline=True)
    embed.add_field(name="Account ID",       value=f"`{player['id']}`",                              inline=True)
    embed.add_field(name="Rank & Rating",    value=f"**{player['rank']}** ({player['rating']:,} Rating)", inline=True)
    embed.add_field(name="Kills / Deaths",   value=f"{player['kills']:,} / {player['deaths']:,} (K/D: **{player['kd_ratio']}**)", inline=False)
    embed.add_field(name="Peak / Lowest",    value=f"Peak: **{player['peak_rating']:,}** | Lowest: **{player['lowest_rating']:,}**", inline=False)
    embed.add_field(name="Account Age",      value=player['account_age_str'],                        inline=True)
    embed.add_field(name="Level",            value=f"Level **{player['level']}**",                   inline=True)
    embed.set_footer(text="made by powm")
    await interaction.followup.send(embed=embed)


@bot.tree.command(name="snipe", description="Snipe and track a player's ranked match status")
@app_commands.describe(ign="Player IGN to snipe")
async def cmd_snipe(interaction: discord.Interaction, ign: str):
    await interaction.response.defer()
    user_id = interaction.user.id

    player = await cops_api_client.get_player_by_ign(ign)
    if player:
        display_name = player["ign"]
        rank_str     = player.get("rank", "Unknown")
        rating_str   = f"{player.get('rating', 0):,}"
        clan_tag     = player.get("clan_tag", "")
        profile_line = f"**{rank_str}** — {rating_str} MMR"
        if clan_tag:
            profile_line += f" | Clan: **[{clan_tag}]**"
    else:
        display_name = ign
        profile_line = "Player not found in database — will still track MMR changes."


    added = snipe_tracker.add_target(user_id, display_name)
    if not added:
        await interaction.followup.send(
            f"Player **{display_name}** is already being sniped by you!",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title="Player Snipe Activated",
        description=(
            f"Now actively sniping **{display_name}**\n"
            f"{profile_line}\n\n"
            f"You will receive automated alerts when their MMR changes (ranked game finished).\n"
            f"*Note: C-Ops API does not expose real-time online/in-game status.*"
        ),
        color=discord.Color.dark_purple()
    )
    embed.set_footer(text="made by pown")
    await interaction.followup.send(embed=embed)



@bot.tree.command(name="unsnipe", description="Stop sniping a player")
@app_commands.describe(ign="Player IGN to stop sniping")
async def cmd_unsnipe(interaction: discord.Interaction, ign: str):
    await interaction.response.defer()
    user_id = interaction.user.id

    player = await cops_api_client.get_player_by_ign(ign)
    display_name = player["ign"] if player else ign

    removed = snipe_tracker.remove_target(user_id, display_name)
    if not removed:
        await interaction.followup.send(
            f"You are not currently sniping player **{display_name}**.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title="Player Snipe Deactivated",
        description=f"Stopped sniping **{display_name}**.",
        color=discord.Color.dark_red()
    )
    embed.set_footer(text="made by pown")
    await interaction.followup.send(embed=embed)


@bot.tree.command(name="leaderboard", description="Show Critical Ops Elite Ops Leaderboard (real MMR) with page buttons")
async def cmd_leaderboard(interaction: discord.Interaction):
    await interaction.response.defer()

    players = await cops_api_client.get_elite_leaderboard()
    if not players:
        await interaction.followup.send(
            "Could not retrieve Critical Ops Elite Ops Leaderboard. API may be down.",
            ephemeral=True
        )
        return

    view  = LeaderboardPaginationView(players=players, per_page=10)
    embed = view.get_page_embed()
    await interaction.followup.send(embed=embed, view=view)


# ==================== BACKGROUND TRACKING LOOP ====================

@tasks.loop(seconds=15)
async def background_tracking_loop():
    try:
        # ---- Snipe Alerts ----
        snipe_alerts = await snipe_tracker.check_snipes(bot)
        for alert in snipe_alerts:
            user = bot.get_user(alert["user_id"])
            if user:
                try:
                    await user.send(alert["message"])
                except Exception as e:
                    print(f"[SNIPE DM ERROR] Could not DM user {alert['user_id']}: {e}")

        # ---- Leaderboard Updates ----
        leaderboard_updates = await leaderboard_tracker.check_updates()
        if leaderboard_updates:
            target_channel = bot.get_channel(config.LEADERBOARD_CHANNEL_ID)
            if target_channel:
                embed = discord.Embed(
                    title="SPEC OPS+ LEADERBOARD TRACKER",
                    description="\n".join(leaderboard_updates),
                    color=discord.Color.green()
                )
                embed.set_footer(text="made by pown • Auto Leaderboard Tracking")
                await target_channel.send(embed=embed)
                print(f"[TRACKER] Posted {len(leaderboard_updates)} update(s) to channel.")
            else:
                print(f"[TRACKER WARNING] Channel {config.LEADERBOARD_CHANNEL_ID} not found!")

    except Exception as e:
        print(f"[BACKGROUND LOOP ERROR] {e}")


@background_tracking_loop.before_loop
async def before_tracking_loop():
    await bot.wait_until_ready()


if __name__ == "__main__":
    token = config.DISCORD_TOKEN
    if not token:
        print("[ERROR] DISCORD_TOKEN is not set!")
        exit(1)
    bot.run(token)
