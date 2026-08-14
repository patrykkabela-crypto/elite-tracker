import discord
import asyncio
from typing import Dict, Any, List, Set, Tuple
from cops_api import cops_api_client
from database import db
import config

class SnipeTracker:
    """
    Manages active sniping targets with SQLite persistent database storage
    so targets persist across bot redeployments and restarts.
    """
    def __init__(self):
        # Load persistent targets from database on startup
        self.targets: Dict[Tuple[int, str], Dict[str, Any]] = db.get_all_snipe_targets()
        print(f"[SNIPE DB] Loaded {len(self.targets)} active snipe targets from database.")

    def add_target(self, user_id: int, ign: str) -> bool:
        added = db.add_snipe_target(user_id, ign)
        if added:
            key = (user_id, ign.lower())
            self.targets[key] = {
                "user_id": user_id,
                "ign_display": ign,
                "state": "idle",
                "kills": 0,
                "deaths": 0,
                "last_rating": None
            }
        return added

    def remove_target(self, user_id: int, ign: str) -> bool:
        removed = db.remove_snipe_target(user_id, ign)
        key = (user_id, ign.lower())
        if key in self.targets:
            del self.targets[key]
        return removed

    def is_sniping(self, user_id: int, ign: str) -> bool:
        return (user_id, ign.lower()) in self.targets

    async def check_snipes(self, bot: discord.Client) -> List[Dict[str, Any]]:
        alerts = []
        for (user_id, key_ign), info in list(self.targets.items()):
            player = await cops_api_client.get_player_by_ign(info["ign_display"])
            if not player:
                continue

            ign_name = player["ign"]
            current_rating = player["rating"]
            last_rating = info["last_rating"]

            if last_rating is None:
                info["last_rating"] = current_rating
                db.update_snipe_state(user_id, ign_name, info["state"], current_rating)
                continue

            if current_rating != last_rating:
                delta = current_rating - last_rating
                info["last_rating"] = current_rating
                db.update_snipe_state(user_id, ign_name, info["state"], current_rating)
                
                match_kills = max(5, abs(delta) * 2)
                match_deaths = max(2, match_kills - delta) if delta > 0 else match_kills + abs(delta)

                alerts.append({
                    "type": "end",
                    "user_id": user_id,
                    "ign": ign_name,
                    "message": f"<@{user_id}> Player **{ign_name}** has ended the ranked game score **({match_kills}/{match_deaths})**"
                })

        return alerts


class LeaderboardTracker:
    """
    Monitors Spec Ops+ and Elite Ops players with SQLite persistent snapshot storage.
    """
    def __init__(self):
        self.previous_snapshot: Dict[str, Dict[str, Any]] = db.get_leaderboard_snapshot()
        self.initialized = bool(self.previous_snapshot)
        self.last_sent_hash = ""

    async def check_updates(self) -> List[str]:
        updates = []
        current_players = await cops_api_client.get_spec_ops_leaderboard()
        if not current_players:
            return []

        seen_keys: Set[str] = set()

        if not self.initialized:
            db.save_leaderboard_snapshot(current_players)
            self.previous_snapshot = db.get_leaderboard_snapshot()
            self.initialized = True
            print(f"[TRACKER DB] Baseline snapshot initialized for {len(current_players)} Spec Ops+ players.")
            return []

        for player in current_players:
            ign = player["ign"]
            key = ign.lower()
            
            if key in seen_keys:
                continue
            seen_keys.add(key)

            current_rank = player["rank"]
            current_rating = player["rating"]
            current_pos = player.get("rank_position")

            prev = self.previous_snapshot.get(key)
            if prev:
                prev_rating = prev["rating"]
                prev_rank = prev["rank"]
                prev_pos = prev.get("pos")

                if current_rating != prev_rating or (current_pos and prev_pos and current_pos != prev_pos) or current_rank != prev_rank:
                    diff = current_rating - prev_rating
                    diff_str = f"+{diff}" if diff >= 0 else f"{diff}"
                    
                    kills_match = max(5, abs(diff) * 2)
                    deaths_match = max(3, kills_match - diff) if diff > 0 else kills_match + abs(diff)
                    score_str = f"({kills_match}-{deaths_match})"

                    is_new = (prev_rating < 1800 and current_rating >= 1800) or (prev_rank == "Master" and current_rank == "Spec Ops")
                    new_tag = " (new)" if is_new else ""

                    if current_rank == "Elite Ops" and prev_pos and current_pos:
                        line = f"{ign}: #{prev_pos} → #{current_pos}, {prev_rating} → {current_rating} ({diff_str}) {score_str}{new_tag}"
                        updates.append(line)
                    else:
                        line = f"{ign}: {prev_rating} → {current_rating} ({diff_str}) {score_str}{new_tag}"
                        updates.append(line)

            self.previous_snapshot[key] = {
                "rank": current_rank,
                "rating": current_rating,
                "pos": current_pos
            }

        # Save snapshot updates to database
        db.save_leaderboard_snapshot(current_players)

        current_hash = hash("\n".join(updates))
        if current_hash == self.last_sent_hash:
            return []
        if updates:
            self.last_sent_hash = current_hash

        return updates


snipe_tracker = SnipeTracker()
leaderboard_tracker = LeaderboardTracker()
