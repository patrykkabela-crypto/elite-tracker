import os
import json
import sqlite3
from typing import Dict, Any, List, Tuple, Optional

# File path for permanent local backup file
BACKUP_FILE = "snipe_backup.json"

# Check if Railway PostgreSQL DATABASE_URL is valid
raw_db_url = os.getenv("DATABASE_URL", "").strip()

if raw_db_url and ("postgres://" in raw_db_url or "postgresql://" in raw_db_url) and not raw_db_url.startswith("${"):
    if raw_db_url.startswith("postgres://"):
        raw_db_url = raw_db_url.replace("postgres://", "postgresql://", 1)
    
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        test_conn = psycopg2.connect(raw_db_url)
        test_conn.close()
        DATABASE_URL = raw_db_url
        USE_PG = True
        print("[DB] Successfully connected to Railway PostgreSQL Database.")
    except Exception as e:
        print(f"[DB WARNING] Could not connect to PostgreSQL ({e}). Using local persistent backup.")
        DATABASE_URL = ""
        USE_PG = False
else:
    DATABASE_URL = ""
    USE_PG = False
    print("[DB] Configured for Local Persistent Database Storage.")


class DatabaseManager:
    """
    Fail-Safe Multi-Storage Database Manager:
    Uses PostgreSQL if available, local SQLite, AND a persistent JSON backup file
    so snipe targets NEVER disappear across restarts or redeployments.
    """
    def __init__(self, sqlite_path: str = "bot_data.db"):
        self.sqlite_path = sqlite_path
        self.use_pg = USE_PG
        self.pg_url = DATABASE_URL
        self._init_db()

    def _get_connection(self):
        if self.use_pg and self.pg_url:
            try:
                import psycopg2
                from psycopg2.extras import RealDictCursor
                return psycopg2.connect(self.pg_url, cursor_factory=RealDictCursor)
            except Exception as e:
                print(f"[DB ERROR] PostgreSQL connection error: {e}")
                self.use_pg = False

        conn = sqlite3.connect(self.sqlite_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                if self.use_pg:
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS snipe_targets (
                            user_id BIGINT NOT NULL,
                            ign_lowercase VARCHAR(100) NOT NULL,
                            ign_display VARCHAR(100) NOT NULL,
                            state VARCHAR(50) DEFAULT 'idle',
                            kills INT DEFAULT 0,
                            deaths INT DEFAULT 0,
                            last_rating INT DEFAULT NULL,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            PRIMARY KEY (user_id, ign_lowercase)
                        );
                    """)
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS leaderboard_snapshot (
                            ign_lowercase VARCHAR(100) PRIMARY KEY,
                            ign_display VARCHAR(100) NOT NULL,
                            rank_name VARCHAR(50) NOT NULL,
                            rating INT NOT NULL,
                            rank_position INT DEFAULT NULL,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        );
                    """)
                else:
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
        except Exception as e:
            print(f"[DB ERROR] Database initialization error: {e}")

    # ==================== JSON FILE BACKUP ====================

    def _load_json_backup(self) -> Dict[str, Dict[str, Any]]:
        if os.path.exists(BACKUP_FILE):
            try:
                with open(BACKUP_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[DB BACKUP WARNING] Failed loading JSON backup: {e}")
        return {}

    def _save_json_backup(self, data: Dict[str, Dict[str, Any]]):
        try:
            with open(BACKUP_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[DB BACKUP ERROR] Failed saving JSON backup: {e}")

    # ==================== SNIPE TARGETS ====================

    def add_snipe_target(self, user_id: int, ign_display: str) -> bool:
        ign_lower = ign_display.lower()
        key_str = f"{user_id}:{ign_lower}"
        
        # Check JSON backup first
        backup_data = self._load_json_backup()
        already_exists = key_str in backup_data

        # Update JSON backup
        backup_data[key_str] = {
            "user_id": user_id,
            "ign_display": ign_display,
            "ign_lowercase": ign_lower,
            "state": "idle",
            "last_rating": None
        }
        self._save_json_backup(backup_data)

        # Update SQL DB
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                if self.use_pg:
                    cursor.execute("""
                        INSERT INTO snipe_targets (user_id, ign_lowercase, ign_display)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (user_id, ign_lowercase) DO NOTHING
                    """, (user_id, ign_lower, ign_display))
                else:
                    try:
                        cursor.execute("""
                            INSERT INTO snipe_targets (user_id, ign_lowercase, ign_display)
                            VALUES (?, ?, ?)
                        """, (user_id, ign_lower, ign_display))
                    except sqlite3.IntegrityError:
                        pass
                conn.commit()
        except Exception as e:
            print(f"[DB ERROR] add_snipe_target SQL error: {e}")

        return not already_exists

    def remove_snipe_target(self, user_id: int, ign_display: str) -> bool:
        ign_lower = ign_display.lower()
        key_str = f"{user_id}:{ign_lower}"
        
        # Remove from JSON backup
        backup_data = self._load_json_backup()
        removed_json = key_str in backup_data
        if removed_json:
            del backup_data[key_str]
            self._save_json_backup(backup_data)

        # Remove from SQL DB
        removed_sql = False
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                ph = "%s" if self.use_pg else "?"
                cursor.execute(f"""
                    DELETE FROM snipe_targets
                    WHERE user_id = {ph} AND ign_lowercase = {ph}
                """, (user_id, ign_lower))
                conn.commit()
                removed_sql = cursor.rowcount > 0
        except Exception as e:
            print(f"[DB ERROR] remove_snipe_target SQL error: {e}")

        return removed_json or removed_sql

    def update_snipe_state(self, user_id: int, ign_display: str, state: str, last_rating: int):
        ign_lower = ign_display.lower()
        key_str = f"{user_id}:{ign_lower}"
        
        backup_data = self._load_json_backup()
        if key_str in backup_data:
            backup_data[key_str]["state"] = state
            backup_data[key_str]["last_rating"] = last_rating
            self._save_json_backup(backup_data)

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                ph = "%s" if self.use_pg else "?"
                cursor.execute(f"""
                    UPDATE snipe_targets
                    SET state = {ph}, last_rating = {ph}
                    WHERE user_id = {ph} AND ign_lowercase = {ph}
                """, (state, last_rating, user_id, ign_lower))
                conn.commit()
        except Exception as e:
            print(f"[DB ERROR] update_snipe_state failed: {e}")

    def get_all_snipe_targets(self) -> Dict[Tuple[int, str], Dict[str, Any]]:
        targets = {}
        
        # Load from JSON backup first
        backup_data = self._load_json_backup()
        for key_str, item in backup_data.items():
            u_id = int(item["user_id"])
            ign_low = item["ign_lowercase"]
            targets[(u_id, ign_low)] = {
                "user_id": u_id,
                "ign_display": item["ign_display"],
                "state": item.get("state", "idle"),
                "kills": 0,
                "deaths": 0,
                "last_rating": item.get("last_rating")
            }

        # Sync from SQL DB
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT user_id, ign_lowercase, ign_display, state, kills, deaths, last_rating FROM snipe_targets")
                for row in cursor.fetchall():
                    u_id = int(row["user_id"])
                    ign_low = row["ign_lowercase"]
                    targets[(u_id, ign_low)] = {
                        "user_id": u_id,
                        "ign_display": row["ign_display"],
                        "state": row["state"],
                        "kills": row["kills"],
                        "deaths": row["deaths"],
                        "last_rating": row["last_rating"]
                    }
        except Exception as e:
            print(f"[DB ERROR] get_all_snipe_targets failed: {e}")
            
        return targets

    # ==================== LEADERBOARD SNAPSHOT ====================

    def save_leaderboard_snapshot(self, players: List[Dict[str, Any]]):
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                for p in players:
                    key = p["ign"].lower()
                    if self.use_pg:
                        cursor.execute("""
                            INSERT INTO leaderboard_snapshot (ign_lowercase, ign_display, rank_name, rating, rank_position, updated_at)
                            VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                            ON CONFLICT (ign_lowercase) DO UPDATE SET
                                ign_display = EXCLUDED.ign_display,
                                rank_name = EXCLUDED.rank_name,
                                rating = EXCLUDED.rating,
                                rank_position = EXCLUDED.rank_position,
                                updated_at = CURRENT_TIMESTAMP
                        """, (key, p["ign"], p["rank"], p["rating"], p.get("rank_position")))
                    else:
                        cursor.execute("""
                            INSERT OR REPLACE INTO leaderboard_snapshot (ign_lowercase, ign_display, rank_name, rating, rank_position, updated_at)
                            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                        """, (key, p["ign"], p["rank"], p["rating"], p.get("rank_position")))
                conn.commit()
        except Exception as e:
            print(f"[DB ERROR] save_leaderboard_snapshot failed: {e}")

    def get_leaderboard_snapshot(self) -> Dict[str, Dict[str, Any]]:
        snapshot = {}
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT ign_lowercase, rank_name, rating, rank_position FROM leaderboard_snapshot")
                for row in cursor.fetchall():
                    snapshot[row["ign_lowercase"]] = {
                        "rank": row["rank_name"],
                        "rating": row["rating"],
                        "pos": row["rank_position"]
                    }
        except Exception as e:
            print(f"[DB ERROR] get_leaderboard_snapshot failed: {e}")
        return snapshot

db = DatabaseManager()
