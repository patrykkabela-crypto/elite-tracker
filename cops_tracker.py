import discord
import asyncio
import time
from typing import Dict, Any, List, Set, Tuple, Optional
from cops_api import cops_api_client
from database import db
import config

# ==================== SNIPE TRACKER ====================

class SnipeTracker:
    """
    Manages active sniping targets with instant baseline population,
    anti-spam deduping, and clean match tracking.
    """
    def __init__(self):
        self.sent_alert_cache: Set[str] = set()

    @property
    def targets(self) -> Dict[Tuple[int, str], Dict[str, Any]]:
        return db.get_all_snipe_targets()

    async def add_target(self, user_id: int, ign: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Adds a target and immediately populates their live baseline stats.
        Returns (success, player_data).
        """
        player = await cops_api_client.get_player_by_ign(ign)
        if not player:
            added = db.add_snipe_target(user_id, ign)
            return added, None

        display_name   = player["ign"]
        current_rating = player["rating"]
        current_kills  = player.get("season_kills", player.get("career_kills", 0))
        current_deaths = player.get("season_deaths", player.get("career_deaths", 0))
        current_games  = player.get("season_games", player.get("career_games", 0))
        current_pos    = player.get("rank_position")

        added = db.add_snipe_target(user_id, display_name)
        if added:
            db.update_snipe_state(
                user_id=user_id,
                ign_display=display_name,
                state="idle",
                last_rating=current_rating,
                kills=current_kills,
                deaths=current_deaths,
                games_played=current_games,
                last_position=current_pos,
                mid_match=False,
                match_start_kills=current_kills,
                match_start_deaths=current_deaths
            )

        return added, player

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
            current_kills  = player.get("season_kills", player.get("career_kills", 0))
            current_deaths = player.get("season_deaths", player.get("career_deaths", 0))
            current_games  = player.get("season_games", player.get("career_games", 0))
            current_pos    = player.get("rank_position")
            is_banned      = player.get("banned", False)

            # Auto-Banned Check
            if is_banned:
                db.remove_snipe_target(user_id, ign_name)
                db.hackusate_player(ign_name, user_id, "System Auto-Banned Check", is_banned=True)
                alerts.append({
                    "type":    "banned",
                    "user_id": user_id,
                    "ign":     ign_name,
                    "message": (
                        f"PLAYER BANNED: Player **{ign_name}** has been BANNED by Critical Ops.\n"
                        f"Target auto-removed from your snipe list."
                    )
                })
                continue

            last_rating       = info["last_rating"]
            last_kills        = info["kills"]
            last_deaths       = info["deaths"]
            last_games        = info["games_played"]
            last_pos          = info["last_position"]
            mid_match         = info.get("mid_match", False)
            match_start_k     = info.get("match_start_kills", current_kills)
            match_start_d     = info.get("match_start_deaths", current_deaths)

            if last_rating is None or last_games == 0 or match_start_k == 0:
                db.update_snipe_state(
                    user_id=user_id,
                    ign_display=ign_name,
                    state="idle",
                    last_rating=current_rating,
                    kills=current_kills,
                    deaths=current_deaths,
                    games_played=current_games,
                    last_position=current_pos,
                    mid_match=False,
                    match_start_kills=current_kills,
                    match_start_deaths=current_deaths
                )
                continue

            game_count_increased = (current_games > last_games and last_games > 0)
            rating_changed       = (current_rating != last_rating)
            kills_increased      = (current_kills > last_kills)
            deaths_increased     = (current_deaths > last_deaths)

            # Scenario A: RANKED MATCH FINISHED
            if game_count_increased or rating_changed:
                delta_rating = current_rating - last_rating
                delta_k      = current_kills - match_start_k
                delta_d      = current_deaths - match_start_d

                if delta_k > 100 or delta_k < 0:
                    delta_k = max(0, current_kills - last_kills)
                if delta_d > 100 or delta_d < 0:
                    delta_d = max(0, current_deaths - last_deaths)

                dedup_sig = f"{user_id}:{ign_name.lower()}:{current_games}:{current_rating}:{current_kills}"
                if dedup_sig in self.sent_alert_cache:
                    continue
                self.sent_alert_cache.add(dedup_sig)
                if len(self.sent_alert_cache) > 500:
                    self.sent_alert_cache.clear()

                sign_r = "+" if delta_rating >= 0 else ""
                pos_str = ""
                if last_pos and current_pos and last_pos != current_pos:
                    pos_str = f" #{last_pos} -> #{current_pos}"
                elif current_pos:
                    pos_str = f" #{current_pos}"

                clean_msg = (
                    f"RANKED MATCH FINISHED\n"
                    f"{ign_name}{pos_str} -> {current_rating:,} MMR ({sign_r}{delta_rating})\n"
                    f"Score: +{max(0, delta_k)} Kills, +{max(0, delta_d)} Deaths | Season Games: {current_games} (+1 Game Finished)"
                )

                db.update_snipe_state(
                    user_id=user_id,
                    ign_display=ign_name,
                    state="idle",
                    last_rating=current_rating,
                    kills=current_kills,
                    deaths=current_deaths,
                    games_played=current_games,
                    last_position=current_pos,
                    mid_match=False,
                    match_start_kills=current_kills,
                    match_start_deaths=current_deaths
                )

                alerts.append({
                    "type":    "match_ended",
                    "user_id": user_id,
                    "ign":     ign_name,
                    "message": clean_msg
                })

            # Scenario B: LIVE MID-GAME UPDATE
            elif (kills_increased or deaths_increased) and not game_count_increased:
                live_k = current_kills - match_start_k
                live_d = current_deaths - match_start_d

                if live_k > 100 or live_k < 0:
                    live_k = max(0, current_kills - last_kills)
                if live_d > 100 or live_d < 0:
                    live_d = max(0, current_deaths - last_deaths)

                dedup_sig = f"mid:{user_id}:{ign_name.lower()}:{current_kills}:{current_deaths}"
                if dedup_sig in self.sent_alert_cache:
                    continue
                self.sent_alert_cache.add(dedup_sig)

                db.update_snipe_state(
                    user_id=user_id,
                    ign_display=ign_name,
                    state="in_game",
                    last_rating=last_rating,
                    kills=current_kills,
                    deaths=current_deaths,
                    games_played=last_games,
                    last_position=current_pos,
                    mid_match=True,
                    match_start_kills=match_start_k,
                    match_start_deaths=match_start_d
                )

                clean_msg = (
                    f"IN-GAME SCORE UPDATE\n"
                    f"Player {ign_name} is currently in a ranked match\n"
                    f"Live Mid-Game Score: +{max(0, live_k)} Kills, +{max(0, live_d)} Deaths"
                )

                alerts.append({
                    "type":    "live_mid_game",
                    "user_id": user_id,
                    "ign":     ign_name,
                    "message": clean_msg
                })

        return alerts


# ==================== LEADERBOARD TRACKER ====================

class LeaderboardTracker:
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
                        pos_transition = f"#{prev_pos} -> #{current_pos}"
                    elif current_pos:
                        pos_transition = f"#{current_pos}"

                    line = f"{ign}{pos_transition} -> {current_rating:,} MMR ({diff_str})"
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
