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
    Manages active sniping targets with multi-layer persistent storage.
    Guarantees target survival across bot redeployments and restarts.
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
        for (user_id, key_ign), info in list(self.targets.items()):
            player = await cops_api_client.get_player_by_ign(info["ign_display"])  # real MMR via /player/{ign}
            if not player:
                continue

            ign_name     = player["ign"]
            current_rating = player["rating"]
            last_rating    = info["last_rating"]

            if last_rating is None:
                db.update_snipe_state(user_id, ign_name, info["state"], current_rating)
                continue

            if current_rating != last_rating:
                delta = current_rating - last_rating
                db.update_snipe_state(user_id, ign_name, info["state"], current_rating)

                sign = "+" if delta >= 0 else ""
                alerts.append({
                    "type":    "end",
                    "user_id": user_id,
                    "ign":     ign_name,
                    "message": (
                        f"**{ign_name}** just finished a ranked game!\n"
                        f"Rating: **{last_rating:,} → {current_rating:,}** ({sign}{delta})"
                    )
                })

        return alerts


# ==================== LEADERBOARD TRACKER ====================

class LeaderboardTracker:
    """
    Monitors Spec Ops (1800+ rating) and Elite Ops players.
    - Only posts when a player's actual rating changes (= real game played).
    - Persists last-sent hash to a file to survive bot restarts/redeploys without re-sending.
    """
    HASH_FILE = "last_tracker_hash.txt"

    def __init__(self):
        self.previous_snapshot: Dict[str, Dict[str, Any]] = db.get_leaderboard_snapshot()
        self.initialized = bool(self.previous_snapshot)
        # Load the persisted hash from disk so duplicates survive restarts
        self.last_sent_hash = self._load_hash()
        # Timestamp of last post — extra guard against burst duplicates
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
        current_players = await cops_api_client.get_elite_leaderboard()  # real MMR from /leaderboard/elite
        if not current_players:
            return []

        seen_keys: Set[str] = set()

        # First run — just take a snapshot, post nothing
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
                prev_rank   = prev["rank"]
                prev_pos    = prev.get("pos")

                # ── ONLY fire when rating actually changed (real match played) ──
                if current_rating != prev_rating:
                    diff     = current_rating - prev_rating
                    diff_str = f"+{diff}" if diff >= 0 else str(diff)

                    is_new  = (prev_rating < 1800 and current_rating >= 1800) or \
                              (prev_rank == "Master" and current_rank == "Spec Ops")
                    new_tag = " (new)" if is_new else ""

                    # Elite Ops: show rank position movement too
                    if current_rank == "Elite Ops" and prev_pos and current_pos and prev_pos != current_pos:
                        line = f"{ign}: #{prev_pos} → #{current_pos}, {prev_rating} → {current_rating} ({diff_str}){new_tag}"
                    elif current_rank == "Elite Ops" and current_pos:
                        line = f"{ign}: #{current_pos}, {prev_rating} → {current_rating} ({diff_str}){new_tag}"
                    else:
                        line = f"{ign}: {prev_rating} → {current_rating} ({diff_str}){new_tag}"

                    updates.append(line)

            # Update in-memory snapshot
            self.previous_snapshot[key] = {
                "rank":  current_rank,
                "rating": current_rating,
                "pos":    current_pos
            }

        # Persist snapshot to DB
        db.save_leaderboard_snapshot(current_players)

        if not updates:
            return []

        # ── Dedup: same content as last post? Skip. ──
        content_hash = str(hash("|".join(sorted(updates))))
        if content_hash == self.last_sent_hash:
            print(f"[TRACKER] Duplicate batch detected — skipping.")
            return []

        # ── Burst guard: don't send twice within 10 seconds ──
        now = time.time()
        if now - self.last_sent_time < 10:
            print(f"[TRACKER] Burst guard triggered — too soon since last post.")
            return []

        self.last_sent_hash  = content_hash
        self.last_sent_time  = now
        self._save_hash(content_hash)    # Persist so restarts won't re-send same batch

        return updates


snipe_tracker     = SnipeTracker()
leaderboard_tracker = LeaderboardTracker()
