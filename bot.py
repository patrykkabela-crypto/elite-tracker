import discord
from discord import app_commands
from discord.ext import commands, tasks
import asyncio
import config
from cops_api import cops_api_client
from cops_tracker import snipe_tracker, leaderboard_tracker
from database import db

# ==================== CRITICAL OPS GENUINE SKIN CATALOG DATA ====================

SKIN_CATALOG = {
    "Knives": {
        "Remix": ["Hyperion", "Glitch", "Cyberpunk", "Solar", "Neon", "Thermal"],
        "Kukri": ["Golden Feather", "Dragonfly", "Crimson", "Obsidian", "Damascus"],
        "Karambit": ["Fade", "Doppler", "Glitch", "Crimson", "Golden Age", "Thermal"],
        "Balisong": ["Spectrum", "Neon", "Hyperion", "Overdrive", "Void", "Chroma"],
        "Tac-Knife": ["Tactical", "Urban", "Scorched", "Safari", "Midnight", "Rust"],
        "Pipe Wrench": ["Heavy Metal", "Rust", "Gold", "Chrome", "Steel"]
    },
    "Gloves": {
        "Specialist": ["Emerald", "Crimson", "Snow", "Gold Touch", "Stealth"],
        "Operative": ["Blackout", "Venom", "Cobalt", "Inferno", "Viper"],
        "Tactician": ["Desert Storm", "Digital", "Ghost", "Apex", "Overdrive"]
    },
    "Pistols": {
        "P250": ["Cyber", "Supernova", "Pulse", "Sandstorm", "Neon"],
        "GSR 1911": ["Chrome", "Royal", "Dragon", "Golden Age", "Vintage"],
        "MR96": ["Python", "Wild West", "Black Gold", "Magnum Force", "Redline"],
        "Deagle": ["Golden Dragon", "Blaze", "Code Red", "Mecha", "Royal"],
        "Dual MTX": ["Double Trouble", "Cyber", "Inferno", "Pulse"]
    },
    "SMGs": {
        "MP5": ["Sub Zero", "Neon Rider", "Chrono", "Acid", "Velocity"],
        "MP7": ["Armor Core", "Impulse", "Special Ops", "Velocity", "Tsunami"],
        "P90": ["Grim", "Cold War", "Death Adder", "Vortex", "Hyperion"],
        "Vector": ["Speed Demon", "Cyberpunk", "Electric", "Phantom", "Overdrive"]
    },
    "Rifles": {
        "AK-47": ["Dragon", "Valkyrie", "Crimson", "Circuit", "Tiger", "Glitch", "Neon Wave"],
        "M4": ["Cyberpunk", "Vampire", "Valkyrie", "Golden Age", "Spectre", "Frostbite"],
        "HK417": ["Sniper Core", "Spectre", "Overwatch", "Titan", "Shadow"],
        "SA58": ["Warfare", "Commando", "Ironclad", "Tactical", "Apex"],
        "AR-15": ["Tactical", "Stealth", "Phantom", "Viper", "Midnight"],
        "SG 551": ["Pulse", "Cyber", "Vortex", "Hyperion", "Overdrive"]
    },
    "Shotguns": {
        "FP6": ["Bulldozer", "Carnage", "Heavy Hitter", "Inferno", "Thunder"],
        "Super 90": ["Enforcer", "Riot", "Vulkan", "Overkill", "Titanium"]
    },
    "Snipers": {
        "TRG-22": ["Dragon", "Hyperion", "Gungnir", "Frostbite", "Vectra"],
        "M14": ["Marksman", "Hunter", "Stalker", "Ghost", "Precision"],
        "URAT": ["Reaper", "Void", "Oblivion", "Eclipse", "Supernova"]
    }
}

AI_VALUATIONS = {
    "Dragon": "AI Valuation: RARE C-OPS SKIN (HIGH DEMAND - WORTH TO BUY)",
    "Valkyrie": "AI Valuation: TOP TIER C-OPS SKIN (GREAT VALUE - WORTH TO BUY)",
    "Fade": "AI Valuation: HIGH VALUE KNIFE SKIN (BEST OFFER CANDIDATE)",
    "Hyperion": "AI Valuation: LEGENDARY C-OPS MARKET ITEM (HIGH LIQUIDITY)",
    "Golden Age": "AI Valuation: EXCLUSIVE EVENT ITEM (HIGH PROFIT POTENTIAL)"
}

def get_ai_recommendation(skin_name: str) -> str:
    for key, val in AI_VALUATIONS.items():
        if key.lower() in skin_name.lower():
            return val
    return "AI Valuation: RECOMMENDED C-OPS MARKETPLACE SKIN (Fair Credit Price)"

# ==================== HACKUSATE BUTTON VIEW ====================

class HackusateView(discord.ui.View):
    def __init__(self, target_ign: str, user_id: int, user_name: str):
        super().__init__(timeout=800)
        self.target_ign = target_ign
        self.user_id = user_id
        self.user_name = user_name

    @discord.ui.button(label="Hackusate Player", style=discord.ButtonStyle.danger, custom_id="hackusate_btn")
    async def hackusate_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        count = db.hackusate_player(
            ign=self.target_ign,
            reported_by=self.user_id,
            reporter_name=self.user_name
        )
        
        embed = discord.Embed(
            title="Hackusation Registered",
            description=(
                f"Player **{self.target_ign}** has been added to the **Hacker Watchlist** (`/hackerlist`)\n"
                f"Total Hackusations: **{count}**\n\n"
                f"Reported by: <@{self.user_id}>\n"
                f"Status: `Under Investigation`"
            ),
            color=discord.Color.red()
        )
        embed.set_footer(text="made by pown • C-Ops Anti-Cheat Watch")
        button.disabled = True
        await interaction.response.edit_message(view=self)
        await interaction.followup.send(embed=embed, ephemeral=False)

# ==================== MARKETPLACE SELECT SKIN VIEWS ====================

class CustomSkinModal(discord.ui.Modal, title="Custom Critical Ops Skin Input"):
    skin_name_input = discord.ui.TextInput(
        label="Exact C-Ops Skin Name",
        placeholder="Type any Tier 1-7 skin name (e.g., Valkyrie, Glitch, Dragon...)",
        required=True,
        max_length=50
    )

    def __init__(self, category: str, gun_name: str):
        super().__init__()
        self.category = category
        self.gun_name = gun_name

    async def on_submit(self, interaction: discord.Interaction):
        skin_name = self.skin_name_input.value.strip()
        ai_advice = get_ai_recommendation(skin_name)
        
        db.add_marketplace_subscription(
            user_id=interaction.user.id,
            category=self.category,
            gun_name=self.gun_name,
            skin_name=skin_name,
            track_type="both"
        )

        embed = discord.Embed(
            title=f"Marketplace Snipe Activated: {self.gun_name} | {skin_name}",
            description=(
                f"Now tracking **{self.gun_name} — {skin_name}** live on Critical Ops Marketplace\n\n"
                f"{ai_advice}\n\n"
                f"Live Notifications Enabled:\n"
                f"• Sell Requests: Player X is Selling {skin_name} for X credits best offer\n"
                f"• Buy Requests: Player X bought requested {skin_name} for X credits best offer"
            ),
            color=discord.Color.gold()
        )
        embed.set_footer(text="made by pown • Live C-Ops Marketplace AI Notifier")
        await interaction.response.send_message(embed=embed, ephemeral=True)


class SkinSelectView(discord.ui.View):
    def __init__(self, category: str, gun_name: str, options_list: list):
        super().__init__(timeout=600)
        self.category = category
        self.gun_name = gun_name
        self.add_item(SkinSelectDropdown(category, gun_name, options_list))

    @discord.ui.button(label="✍️ Type Custom Skin Name", style=discord.ButtonStyle.secondary, custom_id="custom_skin_btn")
    async def custom_skin_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(CustomSkinModal(self.category, self.gun_name))


class SkinSelectDropdown(discord.ui.Select):
    def __init__(self, category: str, gun_name: str, options_list: list):
        self.category = category
        self.gun_name = gun_name
        select_options = [
            discord.SelectOption(label=skin, description=f"{gun_name} skin for market sniping")
            for skin in options_list[:25]
        ]
        super().__init__(
            placeholder=f"Select a skin for {gun_name}...",
            min_values=1,
            max_values=1,
            options=select_options
        )

    async def callback(self, interaction: discord.Interaction):
        skin_name = self.values[0]
        ai_advice = get_ai_recommendation(skin_name)
        
        db.add_marketplace_subscription(
            user_id=interaction.user.id,
            category=self.category,
            gun_name=self.gun_name,
            skin_name=skin_name,
            track_type="both"
        )

        embed = discord.Embed(
            title=f"Marketplace Snipe Activated: {self.gun_name} | {skin_name}",
            description=(
                f"Now tracking **{self.gun_name} — {skin_name}** live on Critical Ops Marketplace\n\n"
                f"{ai_advice}\n\n"
                f"Live Notifications Enabled:\n"
                f"• Sell Requests: Player X is Selling {skin_name} for X credits best offer\n"
                f"• Buy Requests: Player X bought requested {skin_name} for X credits best offer"
            ),
            color=discord.Color.gold()
        )
        embed.set_footer(text="made by pown • Live C-Ops Marketplace AI Notifier")
        await interaction.response.send_message(embed=embed, ephemeral=True)


class GunSelectDropdown(discord.ui.Select):
    def __init__(self, category: str, guns_dict: dict):
        self.category = category
        self.guns_dict = guns_dict
        select_options = [
            discord.SelectOption(label=gun, description=f"Select {gun} models and skins")
            for gun in guns_dict.keys()
        ]
        super().__init__(
            placeholder=f"Select a {category[:-1]} model...",
            min_values=1,
            max_values=1,
            options=select_options
        )

    async def callback(self, interaction: discord.Interaction):
        gun_name = self.values[0]
        skins = self.guns_dict.get(gun_name, [])
        
        view = SkinSelectView(self.category, gun_name, skins)
        
        embed = discord.Embed(
            title=f"Select Skin for {gun_name}",
            description=(
                f"Choose which **{gun_name}** skin you want to snipe on C-Ops Marketplace,\n"
                f"or click **✍️ Type Custom Skin Name** to type any specific C-Ops Tier 1-7 skin name:"
            ),
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class CategorySelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=600)

    @discord.ui.button(label="Knives", style=discord.ButtonStyle.primary, custom_id="cat_knives")
    async def knives_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._show_guns(interaction, "Knives")

    @discord.ui.button(label="Gloves", style=discord.ButtonStyle.primary, custom_id="cat_gloves")
    async def gloves_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._show_guns(interaction, "Gloves")

    @discord.ui.button(label="Pistols", style=discord.ButtonStyle.primary, custom_id="cat_pistols")
    async def pistols_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._show_guns(interaction, "Pistols")

    @discord.ui.button(label="SMGs", style=discord.ButtonStyle.primary, custom_id="cat_smgs")
    async def smgs_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._show_guns(interaction, "SMGs")

    @discord.ui.button(label="Rifles", style=discord.ButtonStyle.success, custom_id="cat_rifles")
    async def rifles_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._show_guns(interaction, "Rifles")

    @discord.ui.button(label="Shotguns", style=discord.ButtonStyle.secondary, custom_id="cat_shotguns")
    async def shotguns_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._show_guns(interaction, "Shotguns")

    @discord.ui.button(label="Snipers", style=discord.ButtonStyle.danger, custom_id="cat_snipers")
    async def snipers_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._show_guns(interaction, "Snipers")

    async def _show_guns(self, interaction: discord.Interaction, category: str):
        guns = SKIN_CATALOG.get(category, {})
        view = discord.ui.View()
        view.add_item(GunSelectDropdown(category, guns))
        
        embed = discord.Embed(
            title=f"Marketplace Selection — {category}",
            description=f"Click the dropdown below to select the **{category}** gun model:",
            color=discord.Color.purple()
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

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
            lines.append(f"**{pos_str}** {ign} — **{rating:,}** Rating ({rank})")

        embed = discord.Embed(
            title="CRITICAL OPS LEADERBOARD",
            description="\n".join(lines) if lines else "No players found.",
            color=discord.Color.gold()
        )
        embed.set_footer(
            text=f"Page {self.current_page}/{self.total_pages} — {len(self.players)} Spec Ops+ Players • made by pown"
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

# ==================== BOT CLASS ====================

class CriticalOpsBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print(f"[BOT] Global slash command sync complete.")

    async def on_ready(self):
        print(f"==========================================")
        print(f"[BOT LOGGED IN] {self.user.name} ({self.user.id})")
        print(f"[TARGET CHANNEL] {config.LEADERBOARD_CHANNEL_ID}")
        print(f"==========================================")

        await self.change_presence(
            activity=discord.Game(name="Critical Ops | /search /snipe /marketplaceselectskin")
        )

        try:
            channel = self.get_channel(config.LEADERBOARD_CHANNEL_ID)
            if channel and hasattr(channel, "guild"):
                guild = channel.guild
                self.tree.copy_global_to(guild=guild)
                synced = await self.tree.sync(guild=guild)
                print(f"[BOT] Instant guild sync to '{guild.name}': {len(synced)} commands.")
        except Exception as e:
            print(f"[BOT WARNING] Guild sync failed: {e}")

        try:
            channel = self.get_channel(config.LEADERBOARD_CHANNEL_ID)
            if channel:
                embed = discord.Embed(
                    title="SPEC OPS+ LEADERBOARD TRACKER ONLINE",
                    description=(
                        "Bot connected to Critical Ops live API & Railway DB.\n"
                        "Actively monitoring Spec Ops+ rank changes, Live Mid-Game Scores, & Marketplace..."
                    ),
                    color=discord.Color.blue()
                )
                embed.set_footer(text="made by pown • Auto Tracker System")
                await channel.send(embed=embed)
        except Exception as e:
            print(f"[ON_READY WARNING] Startup message failed: {e}")

        if not background_tracking_loop.is_running():
            background_tracking_loop.start()
            print(f"[BOT] Background tracking loop started.")


bot = CriticalOpsBot()

# ==================== SLASH COMMANDS ====================

@bot.tree.command(name="search", description="Search a Critical Ops player profile with detailed season & creation info")
@app_commands.describe(ign="Player In-Game Name (IGN)")
async def cmd_search(interaction: discord.Interaction, ign: str):
    await interaction.response.defer()
    player = await cops_api_client.get_player_by_ign(ign)
    if not player:
        await interaction.followup.send(f"Player **{ign}** not found in Critical Ops database.", ephemeral=True)
        return

    banned_str = " | BANNED" if player.get("banned") else ""
    embed = discord.Embed(
        title=f"Critical Ops Player Profile: {player['ign']}{banned_str}",
        color=discord.Color.red() if player.get("banned") else discord.Color.blue()
    )
    embed.add_field(name="IGN",                  value=f"`{player['ign']}`",                              inline=True)
    embed.add_field(name="Account ID",           value=f"`{player['id']}`",                              inline=True)
    embed.add_field(name="Rank & Rating",        value=f"**{player['rank']}** ({player['rating']:,} MMR)", inline=True)
    
    sn = player.get('season_num', 17)
    sg = player.get('season_games', 0)
    sw = player.get('season_wins', 0)
    sl = player.get('season_losses', 0)
    swr = player.get('season_winrate', 0)
    sk = player.get('season_kills', 0)
    sd = player.get('season_deaths', 0)
    skd = player.get('season_kd', 0)

    embed.add_field(
        name=f"Season {sn} Ranked Breakdown",
        value=(
            f"Games Played: **{sg:,}** ({sw} W / {sl} L - **{swr}% Winrate**)\n"
            f"Kills / Deaths: **{sk:,}** / **{sd:,}** (K/D: **{skd}**)"
        ),
        inline=False
    )

    embed.add_field(
        name="Total Career Ranked Stats",
        value=f"Games: **{player['career_games']:,}** | Kills: **{player['career_kills']:,}** | Deaths: **{player['career_deaths']:,}** | Career K/D: **{player['kd_ratio']}**",
        inline=False
    )

    embed.add_field(name="Peak / Lowest Rating",  value=f"Peak: **{player['peak_rating']:,}** | Lowest: **{player['lowest_rating']:,}**", inline=False)
    embed.add_field(name="Account Creation & History", value=f"`{player['account_creation_detail']}`", inline=False)
    embed.add_field(name="Level",                value=f"Level **{player['level']}**",                   inline=True)
    embed.set_footer(text="made by pown • Detailed Profile Analytics")
    await interaction.followup.send(embed=embed)


@bot.tree.command(name="snipe", description="Snipe and track player with LIVE mid-game score & match notifications (DMs Only)")
@app_commands.describe(ign="Player IGN to snipe")
async def cmd_snipe(interaction: discord.Interaction, ign: str):
    await interaction.response.defer()
    user_id = interaction.user.id

    added, player = await snipe_tracker.add_target(user_id, ign)
    if not added:
        await interaction.followup.send(
            f"Player **{ign}** is already being sniped by you!",
            ephemeral=True
        )
        return

    if player:
        display_name = player["ign"]
        rank_str     = player.get("rank", "Unknown")
        rating_str   = f"{player.get('rating', 0):,}"
        lb_pos       = player.get("rank_position")
        pos_str      = f" | Rank: **#{lb_pos}**" if lb_pos else ""
        
        if player.get("banned"):
            await interaction.followup.send(
                f"Player **{display_name}** has been BANNED by Critical Ops. You don't need to snipe them!",
                ephemeral=True
            )
            return

        profile_line = (
            f"**{rank_str}** — {rating_str} MMR{pos_str}\n"
            f"Season Games: **{player['season_games']:,}** | Season K/D: **{player['season_kills']:,} / {player['season_deaths']:,}**"
        )
    else:
        display_name = ign
        profile_line = "Player added to snipe database — live tracking active."

    embed = discord.Embed(
        title="Player Snipe Activated",
        description=(
            f"Now actively sniping **{display_name}**\n"
            f"{profile_line}\n\n"
            f"Live In-Game Score Alerts Enabled:\n"
            f"• During Game: Receive live mid-match score updates.\n"
            f"• Match Completion: Instant DM summary when season games count increases (+1 Game Finished).\n\n"
            f"Notifications are sent to your DMs ONLY."
        ),
        color=discord.Color.dark_purple()
    )
    embed.set_footer(text="made by pown • Direct Message Live Snipe System")
    view = HackusateView(target_ign=display_name, user_id=user_id, user_name=interaction.user.name)
    await interaction.followup.send(embed=embed, view=view)


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


@bot.tree.command(name="marketplaceselectskin", description="Select or type skin to snipe on Critical Ops Marketplace with AI Valuation")
async def cmd_marketplaceselectskin(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Critical Ops Marketplace Skin Snipe",
        description=(
            "Select the weapon category below to pick a skin or type any specific Tier 1-7 C-Ops skin name.\n"
            "Our AI system will analyze item valuation, best offers, buy requests, and sell requests live from C-Ops Marketplace!"
        ),
        color=discord.Color.gold()
    )
    embed.set_footer(text="made by pown • Live C-Ops Marketplace AI Notifier")
    view = CategorySelectView()
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


@bot.tree.command(name="hackerlist", description="View the Critical Ops Hacker Watchlist & Banned Players")
async def cmd_hackerlist(interaction: discord.Interaction):
    await interaction.response.defer()
    entries = db.get_hacker_list()
    
    if not entries:
        await interaction.followup.send("No players currently reported in the Hacker List.", ephemeral=True)
        return

    lines = []
    for e in entries[:20]:
        banned_tag = " [BANNED]" if e["is_banned"] else ""
        lines.append(
            f"• **{e['ign']}**{banned_tag} — **{e['hackusations']}** report(s)\n"
            f"  Status: `{e['status']}` | Reported by: `{e['reporter']}`"
        )

    embed = discord.Embed(
        title="CRITICAL OPS HACKER WATCHLIST",
        description="\n".join(lines),
        color=discord.Color.dark_red()
    )
    embed.set_footer(text="made by pown • Anti-Cheat Watchlist")
    await interaction.followup.send(embed=embed)


@bot.tree.command(name="leaderboard", description="Show Critical Ops Spec Ops & Elite Ops Leaderboard")
async def cmd_leaderboard(interaction: discord.Interaction):
    await interaction.response.defer()

    players = await cops_api_client.get_elite_leaderboard()
    if not players:
        await interaction.followup.send(
            "Could not retrieve Critical Ops Leaderboard. API may be down.",
            ephemeral=True
        )
        return

    view  = LeaderboardPaginationView(players=players, per_page=10)
    embed = view.get_page_embed()
    await interaction.followup.send(embed=embed, view=view)


# ==================== BACKGROUND TRACKING LOOP ====================

@tasks.loop(seconds=10)
async def background_tracking_loop():
    try:
        channel = bot.get_channel(config.LEADERBOARD_CHANNEL_ID)

        # ---- Snipe Alerts (DMs ONLY) ----
        snipe_alerts = await snipe_tracker.check_snipes(bot)
        for alert in snipe_alerts:
            print(f"[SNIPE ALERT] [{alert['type']}] {alert['ign']} — sending DM to user {alert['user_id']}")
            try:
                user = bot.get_user(alert["user_id"]) or await bot.fetch_user(alert["user_id"])
                if user:
                    await user.send(alert["message"])
                    print(f"[SNIPE DM SUCCESS] Sent DM to {user.name}")
            except Exception as e:
                print(f"[SNIPE DM ERROR] Failed DM for user {alert['user_id']}: {e}")

        # ---- Auto Leaderboard Updates ----
        leaderboard_updates = await leaderboard_tracker.check_updates()
        if leaderboard_updates:
            if channel:
                embed = discord.Embed(
                    title="SPEC OPS+ LEADERBOARD TRACKER",
                    description="\n".join(leaderboard_updates),
                    color=discord.Color.green()
                )
                embed.set_footer(text="made by pown • Auto Leaderboard Tracking")
                await channel.send(embed=embed)
                print(f"[TRACKER] Posted {len(leaderboard_updates)} update(s) to channel.")

    except Exception as e:
        import traceback
        print(f"[BACKGROUND LOOP ERROR] {e}")
        traceback.print_exc()


@background_tracking_loop.before_loop
async def before_tracking_loop():
    await bot.wait_until_ready()


if __name__ == "__main__":
    token = config.DISCORD_TOKEN
    if not token:
        print("[ERROR] DISCORD_TOKEN is not set!")
        exit(1)
    bot.run(token)
