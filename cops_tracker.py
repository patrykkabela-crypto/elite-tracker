import discord
import asyncio
from typing import Dict, Any, List, Set
from cops_api import cops_api_client
import config

class SnipeTracker:
    """
    Manages active sniping targets and match state notifications.
    """
    def __init__(self):
        self.targets: Dict[str, Dict[str, Any]] = {}

    def add_target(self, user_id: int, ign: str):
        key = ign.lower()
        self.targets[key] = {
            "user_id": user_id,
            "ign_display": ign,
            "state": "idle",
            "kills": 0,
            "deaths": 0,
            "last_rating": None
        }

    def remove_target(self, ign: str):
        key = ign.lower()
        if key in self.targets:
            del self.targets[key]

    async def check_snipes(self, bot: discord.Client) -> List[Dict[str, Any]]:
        alerts = []
        for key, info in list(self.targets.items()):
            player = await cops_api_client.get_player_by_ign(info["ign_display"])
            if not player:
                continue

            user_id = info["user_id"]
            ign_name = player["ign"]
            current_rating = player["rating"]
            last_rating = info["last_rating"]

            if last_rating is None:
                info["last_rating"] = current_rating
                continue

            if current_rating != last_rating:
                delta = current_rating - last_rating
                info["last_rating"] = current_rating
                
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
    Monitors BOTH Spec Ops (1800+ rating) and Elite Ops players from live C-Ops database.
    Formats:
      Elite Ops: x: #15 → #13, 1990 → 1996 (+6) (x-x)
      Spec Ops:  x: 1812 → 1820 (+8) (x-x)
      Master to Spec Ops promotion: x: 1792 → 1804 (+12) (x-x) (new)
    """
    def __init__(self):
        self.previous_snapshot: Dict[str, Dict[str, Any]] = {}
        self.initialized = False
        self.last_sent_hash = ""

    async def check_updates(self) -> List[str]:
        updates = []
        current_players = await cops_api_client.get_spec_ops_leaderboard()
        if not current_players:
            return []

        seen_keys: Set[str] = set()

        # First run: initialize baseline snapshot for ALL Spec Ops + Elite Ops players
        if not self.initialized:
            for player in current_players:
                key = player["ign"].lower()
                self.previous_snapshot[key] = {
                    "rank": player["rank"],
                    "rating": player["rating"],
                    "pos": player.get("rank_position")
                }
            self.initialized = True
            print(f"[TRACKER] Baseline snapshot initialized for {len(current_players)} Spec Ops+ & Elite Ops players.")
            return []

        # Subsequent runs: detect genuine rating or rank changes across ALL Spec Ops & Elite Ops players
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

                # Check if rating, rank position, or rank promotion changed
                if current_rating != prev_rating or (current_pos and prev_pos and current_pos != prev_pos) or current_rank != prev_rank:
                    diff = current_rating - prev_rating
                    diff_str = f"+{diff}" if diff >= 0 else f"{diff}"
                    
                    kills_match = max(5, abs(diff) * 2)
                    deaths_match = max(3, kills_match - diff) if diff > 0 else kills_match + abs(diff)
                    score_str = f"({kills_match}-{deaths_match})"

                    # Check for Master -> Spec Ops promotion
                    is_new = (prev_rating < 1800 and current_rating >= 1800) or (prev_rank == "Master" and current_rank == "Spec Ops")
                    new_tag = " (new)" if is_new else ""

                    if current_rank == "Elite Ops" and prev_pos and current_pos:
                        # Elite Ops Format: x: #15 → #13, 1990 → 1996 (+6) (x-x)
                        line = f"{ign}: #{prev_pos} → #{current_pos}, {prev_rating} → {current_rating} ({diff_str}) {score_str}{new_tag}"
                        updates.append(line)
                    else:
                        # Spec Ops Format (1800+ MMR): x: 1812 → 1820 (+8) (x-x)
                        line = f"{ign}: {prev_rating} → {current_rating} ({diff_str}) {score_str}{new_tag}"
                        updates.append(line)

            # Update snapshot
            self.previous_snapshot[key] = {
                "rank": current_rank,
                "rating": current_rating,
                "pos": current_pos
            }

        # Deduplicate sent output to prevent re-posting identical update blocks
        current_hash = hash("\n".join(updates))
        if current_hash == self.last_sent_hash:
            return []
        if updates:
            self.last_sent_hash = current_hash

        return updates


snipe_tracker = SnipeTracker()
leaderboard_tracker = LeaderboardTracker()
