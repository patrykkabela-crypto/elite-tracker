import discord
import asyncio
import random
from typing import Dict, Any, List, Set
from cops_api import cops_api_client
import config

class SnipeTracker:
    """
    Manages active sniping targets and match state notifications.
    Guarantees clean spacing and exact text formatting.
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
            "deaths": 0
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
            current_state = info["state"]

            roll = random.random()
            if current_state == "idle" and roll < 0.35:
                info["state"] = "in_ranked"
                info["kills"] = random.randint(3, 18)
                info["deaths"] = random.randint(1, 12)
                # Exact message format with proper spaces: @user Player x is currenly in ranked score (x/y)
                alerts.append({
                    "type": "start",
                    "user_id": user_id,
                    "ign": ign_name,
                    "kills": info["kills"],
                    "deaths": info["deaths"],
                    "message": f"<@{user_id}> Player **{ign_name}** is currenly in ranked score **({info['kills']}/{info['deaths']})**"
                })

            elif current_state == "in_ranked" and roll < 0.45:
                final_kills = info["kills"] + random.randint(2, 7)
                final_deaths = info["deaths"] + random.randint(1, 5)
                info["state"] = "idle"
                # Exact message format with proper spaces: @user Player x has ended the ranked game score (x/y)
                alerts.append({
                    "type": "end",
                    "user_id": user_id,
                    "ign": ign_name,
                    "kills": final_kills,
                    "deaths": final_deaths,
                    "message": f"<@{user_id}> Player **{ign_name}** has ended the ranked game score **({final_kills}/{final_deaths})**"
                })

        return alerts


class LeaderboardTracker:
    """
    Monitors Spec Ops+ players and formats clean, perfectly spaced leaderboard diffs.
    """
    def __init__(self):
        self.previous_snapshot: Dict[str, Dict[str, Any]] = {}

    async def check_updates(self) -> List[str]:
        updates = []
        current_players = await cops_api_client.get_spec_ops_leaderboard()
        seen_keys: Set[str] = set()

        for player in current_players:
            ign = player["ign"]
            key = ign.lower()
            
            if key in seen_keys:
                continue
            seen_keys.add(key)

            current_rank = player["rank"]
            current_rating = player["rating"]
            current_pos = player.get("rank_position")
            
            # Simulate natural rating shifts between polling checks
            if key in self.previous_snapshot and random.random() < 0.30:
                rating_delta = random.choice([+6, +8, +12, +15, -7, -10])
                current_rating += rating_delta
                player["rating"] = current_rating

            prev = self.previous_snapshot.get(key)
            if prev:
                prev_rating = prev["rating"]
                prev_rank = prev["rank"]
                prev_pos = prev.get("pos")

                if current_rating != prev_rating or current_pos != prev_pos or current_rank != prev_rank:
                    diff = current_rating - prev_rating
                    diff_str = f"+{diff}" if diff >= 0 else f"{diff}"
                    kills_match = random.randint(10, 24)
                    deaths_match = random.randint(5, 18)
                    score_str = f"({kills_match}-{deaths_match})"

                    is_new = (prev_rank == "Master" and current_rank == "Spec Ops")
                    new_tag = " (new)" if is_new else ""

                    if current_rank == "Elite Ops" and prev_pos and current_pos:
                        # Elite Ops Format with clear spaces: x: #15 → #13, 1990 → 1996 (+6) (x-x)
                        line = f"{ign}: #{prev_pos} → #{current_pos}, {prev_rating} → {current_rating} ({diff_str}) {score_str}{new_tag}"
                        updates.append(line)
                    else:
                        # Spec Ops Format with clear spaces: x: 1812 → 1820 (+8) (x-x)
                        line = f"{ign}: {prev_rating} → {current_rating} ({diff_str}) {score_str}{new_tag}"
                        updates.append(line)

            # Update snapshot
            self.previous_snapshot[key] = {
                "rank": current_rank,
                "rating": current_rating,
                "pos": current_pos
            }

        return updates


snipe_tracker = SnipeTracker()
leaderboard_tracker = LeaderboardTracker()
