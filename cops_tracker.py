import discord
import asyncio
import time
from typing import Dict, Any, List, Set, Tuple
from cops_api import cops_api_client
from database import db
import config

# ==================== SNIPE TRACKER ====================

class SnipeTracker:
    """
    Manages active sniping targets with statistics (kills, deaths, MMR, rank position).
    Detects ranked matches and banned players instantly.
    """
    def __init__(self):
        pass

    @property
    def targets(self) -> Dict[Tuple[int, str], Dict[str, Any]]:
        return db.get_all_snipe_targets()

    def add_target(self, user_id: int, ign: str) -> bool:
        return db.add_snipe_target(user_id, ign)

    def remove_target(self, user_id: int, ign: str) -> bool:
        return db.remove_snipe_target(user_id, ign)

    def is_sniping(self, user_id: int, ign: str) -> bool:
        return (user_id, ign.lower()) in self.targets

    async def check_snipes(self, bot: discord.Client) -> List[Dict[str, Any]]:
        alerts = []
        all_targets = list(self.targets.items())
        
        for (user_id, key_ign), info in all_targets:
            player = await cops_api_client.get_player_by_ign(info["ign_display"])
            if not player:
                continue

            ign_name       = player["ign"]
            current_rating = player["rating"]
            current_kills  = player.get("kills", 0)
            current_deaths = player.get("deaths", 0)
            current_pos    = player.get("rank_position")
            is_banned      = player.get("banned", False)

            # Check if player was banned!
            if is_banned:
                db.remove_snipe_target(user_id, ign_name)
                # Auto-add to hacker list as banned
                db.hackusate_player(ign_name, user_id, "System Auto-Banned Check", is_banned=True)
                alerts.append({
                    "type":    "banned",
                    "user_id": user_id,
                    "ign":     ign_name,
                    "message": (
                        f"🚫 **PLAYER BANNED ALERT**: Player **{ign_name}** has been BANNED by Critical Ops!\n"
                        f"Target has been automatically removed from your snipe list. You do not need to snipe them anymore."
                    )
                })
                continue

            last_rating   = info["last_rating"]
            last_kills    = info["kills"]
            last_deaths   = info["deaths"]
            last_pos      = info["last_position"]

            # Initialize baseline if first run
            if last_rating is None:
                db.update_snipe_state(user_id, ign_name, info["state"], current_rating, current_kills, current_deaths, current_pos)
                continue

            # Detect stat changes (Ranked Match Completed)
            rating_changed = (current_rating != last_rating)
            kills_changed  = (current_kills > last_kills)
            deaths_changed = (current_deaths > last_deaths)

            if rating_changed or kills_changed or deaths_changed:
                delta_rating = current_rating - last_rating
                delta_k      = current_kills - last_kills
                delta_d      = current_deaths - last_deaths

                db.update_snipe_state(user_id, ign_name, info["state"], current_rating, current_kills, current_deaths, current_pos)

                sign_r = "+" if delta_rating >= 0 else ""
                
                # Format: [x] user #their ranking on leaderboard -> to what now they have , (+x)
                pos_str = ""
                if last_pos and current_pos and last_pos != current_pos:
                    pos_str = f" #{last_pos} → #{current_pos}"
                elif current_pos:
                    pos_str = f" #{current_pos}"

                stat_line = f"{ign_name}{pos_str} -> **{current_rating:,}** ({sign_r}{delta_rating})"
                if delta_k > 0 or delta_d > 0:
                    stat_line += f" | Kills: **+{delta_k}**, Deaths: **+{delta_d}**"

                alerts.append({
                    "type":    "end",
                    "user_id": user_id,
                    "ign":     ign_name,
                    "message": f"🎯 **SNIPE MATCH FINISHED**\n{stat_line}"
                })

        return alerts


# ==================== LEADERBOARD TRACKER ====================

class LeaderboardTracker:
    """
    Monitors Spec Ops (1800+ rating) and Elite Ops players.
    Only fires when actual rating or rank changes.
    """
    HASH_FILE = "last_tracker_hash.txt"

    def __init__(self):
        self.previous_snapshot: Dict[str, Dict[str, Any]] = db.get_leaderboard_snapshot()
        self.initialized = bool(self.previous_snapshot)
        self.last_sent_hash = self._load_hash()
        self.last_sent_time: float = 0.0

    def _load_hash(self) -> str:
        try:
            with open(self.HASH_FILE, "r") as f:
                return f.read().strip()
        except Exception:
            return ""

    def _save_hash(self, h: str):
        try:
            with open(self.HASH_FILE, "w") as f:
                f.write(h)
        except Exception:
            pass

    async def check_updates(self) -> List[str]:
        updates: List[str] = []
        current_players = await cops_api_client.get_elite_leaderboard()
        if not current_players:
            return []

        seen_keys: Set[str] = set()

        if not self.initialized:
            db.save_leaderboard_snapshot(current_players)
            self.previous_snapshot = db.get_leaderboard_snapshot()
            self.initialized = True
            print(f"[TRACKER] Baseline snapshot initialized — {len(current_players)} Spec Ops+ players.")
            return []

        for player in current_players:
            ign  = player["ign"]
            key  = ign.lower()
            if key in seen_keys:
                continue
            seen_keys.add(key)

            current_rank   = player["rank"]
            current_rating = player["rating"]
            current_pos    = player.get("rank_position")
            prev           = self.previous_snapshot.get(key)

            if prev:
                prev_rating = prev["rating"]
                prev_pos    = prev.get("pos")

                if current_rating != prev_rating:
                    diff     = current_rating - prev_rating
                    diff_str = f"+{diff}" if diff >= 0 else str(diff)

                    pos_transition = ""
                    if prev_pos and current_pos and prev_pos != current_pos:
                        pos_transition = f"#{prev_pos} → #{current_pos}"
                    elif current_pos:
                        pos_transition = f"#{current_pos}"
                    else:
                        pos_transition = "#?"

                    # Format: [x] user #their ranking on leaderboard -> to what now they have , (+x)
                    line = f"• **{ign}** {pos_transition} -> **{current_rating:,} MMR** ({diff_str})"
                    updates.append(line)

            self.previous_snapshot[key] = {
                "rank":   current_rank,
                "rating": current_rating,
                "pos":    current_pos
            }

        db.save_leaderboard_snapshot(current_players)

        if not updates:
            return []

        content_hash = str(hash("|".join(sorted(updates))))
        if content_hash == self.last_sent_hash:
            return []

        now = time.time()
        if now - self.last_sent_time < 5:
            return []

        self.last_sent_hash  = content_hash
        self.last_sent_time  = now
        self._save_hash(content_hash)

        return updates


snipe_tracker       = SnipeTracker()
leaderboard_tracker = LeaderboardTracker()
