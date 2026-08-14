import sqlite3
import os
from typing import Dict, Any, List, Tuple

class DatabaseManager:
    """
    SQLite Database Manager for persistent snipe targets and tracker snapshots
    so data survives bot restarts and redeployments on Railway.
    """
    def __init__(self, db_path: str = "bot_data.db"):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Snipe Targets Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS snipe_targets (
                    user_id INTEGER NOT NULL,
                    ign_lowercase TEXT NOT NULL,
                    ign_display TEXT NOT NULL,
                    state TEXT DEFAULT 'idle',
                    kills INTEGER DEFAULT 0,
                    deaths INTEGER DEFAULT 0,
                    last_rating INTEGER DEFAULT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, ign_lowercase)
                );
            """)
            # Leaderboard Snapshot Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS leaderboard_snapshot (
                    ign_lowercase TEXT PRIMARY KEY,
                    ign_display TEXT NOT NULL,
                    rank_name TEXT NOT NULL,
                    rating INTEGER NOT NULL,
                    rank_position INTEGER DEFAULT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.commit()

    # ==================== SNIPE TARGETS ====================

    def add_snipe_target(self, user_id: int, ign_display: str) -> bool:
        ign_lower = ign_display.lower()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO snipe_targets (user_id, ign_lowercase, ign_display)
                    VALUES (?, ?, ?)
                """, (user_id, ign_lower, ign_display))
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False  # Already exists

    def remove_snipe_target(self, user_id: int, ign_display: str) -> bool:
        ign_lower = ign_display.lower()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM snipe_targets
                WHERE user_id = ? AND ign_lowercase = ?
            """, (user_id, ign_lower))
            conn.commit()
            return cursor.rowcount > 0

    def update_snipe_state(self, user_id: int, ign_display: str, state: str, last_rating: int):
        ign_lower = ign_display.lower()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE snipe_targets
                SET state = ?, last_rating = ?
                WHERE user_id = ? AND ign_lowercase = ?
            """, (state, last_rating, user_id, ign_lower))
            conn.commit()

    def get_all_snipe_targets(self) -> Dict[Tuple[int, str], Dict[str, Any]]:
        targets = {}
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT user_id, ign_lowercase, ign_display, state, kills, deaths, last_rating FROM snipe_targets")
            for row in cursor.fetchall():
                key = (row["user_id"], row["ign_lowercase"])
                targets[key] = {
                    "user_id": row["user_id"],
                    "ign_display": row["ign_display"],
                    "state": row["state"],
                    "kills": row["kills"],
                    "deaths": row["deaths"],
                    "last_rating": row["last_rating"]
                }
        return targets

    # ==================== LEADERBOARD SNAPSHOT ====================

    def save_leaderboard_snapshot(self, players: List[Dict[str, Any]]):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            for p in players:
                key = p["ign"].lower()
                cursor.execute("""
                    INSERT OR REPLACE INTO leaderboard_snapshot (ign_lowercase, ign_display, rank_name, rating, rank_position, updated_at)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (key, p["ign"], p["rank"], p["rating"], p.get("rank_position")))
            conn.commit()

    def get_leaderboard_snapshot(self) -> Dict[str, Dict[str, Any]]:
        snapshot = {}
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT ign_lowercase, rank_name, rating, rank_position FROM leaderboard_snapshot")
            for row in cursor.fetchall():
                snapshot[row["ign_lowercase"]] = {
                    "rank": row["rank_name"],
                    "rating": row["rating"],
                    "pos": row["rank_position"]
                }
        return snapshot

db = DatabaseManager()
