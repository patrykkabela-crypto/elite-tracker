import os
import json
import sqlite3
from typing import Dict, Any, List, Tuple, Optional

BACKUP_FILE = "snipe_backup.json"

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
        print("[DB] Connected to Railway PostgreSQL Database.")
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
    Fail-Safe Multi-Storage Database Manager with live message editing support.
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
                            games_played INT DEFAULT 0,
                            last_rating INT DEFAULT NULL,
                            last_position INT DEFAULT NULL,
                            mid_match BOOLEAN DEFAULT FALSE,
                            match_start_kills INT DEFAULT 0,
                            match_start_deaths INT DEFAULT 0,
                            live_message_id BIGINT DEFAULT NULL,
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
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS hacker_list (
                            id SERIAL PRIMARY KEY,
                            ign VARCHAR(100) UNIQUE NOT NULL,
                            reported_by BIGINT NOT NULL,
                            reporter_name VARCHAR(100),
                            status VARCHAR(50) DEFAULT 'Under Investigation',
                            reason VARCHAR(255) DEFAULT 'Hackusated during Snipe',
                            is_banned BOOLEAN DEFAULT FALSE,
                            hackusations INT DEFAULT 1,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        );
                    """)
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS marketplace_subscriptions (
                            id SERIAL PRIMARY KEY,
                            user_id BIGINT NOT NULL,
                            category VARCHAR(50) NOT NULL,
                            gun_name VARCHAR(50) NOT NULL,
                            skin_name VARCHAR(100) NOT NULL,
                            track_type VARCHAR(20) DEFAULT 'both',
                            max_price INT DEFAULT 0,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
                            games_played INTEGER DEFAULT 0,
                            last_rating INTEGER DEFAULT NULL,
                            last_position INTEGER DEFAULT NULL,
                            mid_match INTEGER DEFAULT 0,
                            match_start_kills INTEGER DEFAULT 0,
                            match_start_deaths INTEGER DEFAULT 0,
                            live_message_id INTEGER DEFAULT NULL,
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
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS hacker_list (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            ign TEXT UNIQUE NOT NULL,
                            reported_by INTEGER NOT NULL,
                            reporter_name TEXT,
                            status TEXT DEFAULT 'Under Investigation',
                            reason TEXT DEFAULT 'Hackusated during Snipe',
                            is_banned INTEGER DEFAULT 0,
                            hackusations INTEGER DEFAULT 1,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        );
                    """)
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS marketplace_subscriptions (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            user_id INTEGER NOT NULL,
                            category TEXT NOT NULL,
                            gun_name TEXT NOT NULL,
                            skin_name TEXT NOT NULL,
                            track_type TEXT DEFAULT 'both',
                            max_price INTEGER DEFAULT 0,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        );
                    """)
                
                columns_to_add = [
                    ("games_played", "INTEGER DEFAULT 0" if not self.use_pg else "INT DEFAULT 0"),
                    ("last_position", "INTEGER DEFAULT NULL" if not self.use_pg else "INT DEFAULT NULL"),
                    ("mid_match", "INTEGER DEFAULT 0" if not self.use_pg else "BOOLEAN DEFAULT FALSE"),
                    ("match_start_kills", "INTEGER DEFAULT 0" if not self.use_pg else "INT DEFAULT 0"),
                    ("match_start_deaths", "INTEGER DEFAULT 0" if not self.use_pg else "INT DEFAULT 0"),
                    ("live_message_id", "INTEGER DEFAULT NULL" if not self.use_pg else "BIGINT DEFAULT NULL")
                ]

                for col_name, col_def in columns_to_add:
                    try:
                        cursor.execute(f"ALTER TABLE snipe_targets ADD COLUMN {col_name} {col_def}")
                    except Exception:
                        pass

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
        
        backup_data = self._load_json_backup()
        already_exists = key_str in backup_data

        backup_data[key_str] = {
            "user_id": user_id,
            "ign_display": ign_display,
            "ign_lowercase": ign_lower,
            "state": "idle",
            "kills": 0,
            "deaths": 0,
            "games_played": 0,
            "last_rating": None,
            "last_position": None,
            "mid_match": False,
            "match_start_kills": 0,
            "match_start_deaths": 0,
            "live_message_id": None
        }
        self._save_json_backup(backup_data)

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
        
        backup_data = self._load_json_backup()
        removed_json = key_str in backup_data
        if removed_json:
            del backup_data[key_str]
            self._save_json_backup(backup_data)

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

    def update_snipe_state(self, user_id: int, ign_display: str, state: str, last_rating: int, kills: int = 0, deaths: int = 0, games_played: int = 0, last_position: Optional[int] = None, mid_match: bool = False, match_start_kills: int = 0, match_start_deaths: int = 0, live_message_id: Optional[int] = None):
        ign_lower = ign_display.lower()
        key_str = f"{user_id}:{ign_lower}"
        
        backup_data = self._load_json_backup()
        if key_str in backup_data:
            backup_data[key_str]["state"] = state
            backup_data[key_str]["last_rating"] = last_rating
            backup_data[key_str]["kills"] = kills
            backup_data[key_str]["deaths"] = deaths
            backup_data[key_str]["games_played"] = games_played
            backup_data[key_str]["last_position"] = last_position
            backup_data[key_str]["mid_match"] = mid_match
            backup_data[key_str]["match_start_kills"] = match_start_kills
            backup_data[key_str]["match_start_deaths"] = match_start_deaths
            backup_data[key_str]["live_message_id"] = live_message_id
            self._save_json_backup(backup_data)

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                ph = "%s" if self.use_pg else "?"
                m_val = 1 if mid_match else 0
                cursor.execute(f"""
                    UPDATE snipe_targets
                    SET state = {ph}, last_rating = {ph}, kills = {ph}, deaths = {ph}, games_played = {ph}, last_position = {ph}, mid_match = {ph}, match_start_kills = {ph}, match_start_deaths = {ph}, live_message_id = {ph}
                    WHERE user_id = {ph} AND ign_lowercase = {ph}
                """, (state, last_rating, kills, deaths, games_played, last_position, m_val if not self.use_pg else mid_match, match_start_kills, match_start_deaths, live_message_id, user_id, ign_lower))
                conn.commit()
        except Exception as e:
            print(f"[DB ERROR] update_snipe_state failed: {e}")

    def update_live_message_id(self, user_id: int, ign_display: str, live_message_id: Optional[int]):
        ign_lower = ign_display.lower()
        key_str = f"{user_id}:{ign_lower}"
        backup_data = self._load_json_backup()
        if key_str in backup_data:
            backup_data[key_str]["live_message_id"] = live_message_id
            self._save_json_backup(backup_data)

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                ph = "%s" if self.use_pg else "?"
                cursor.execute(f"UPDATE snipe_targets SET live_message_id = {ph} WHERE user_id = {ph} AND ign_lowercase = {ph}", (live_message_id, user_id, ign_lower))
                conn.commit()
        except Exception as e:
            print(f"[DB ERROR] update_live_message_id failed: {e}")

    def get_all_snipe_targets(self) -> Dict[Tuple[int, str], Dict[str, Any]]:
        targets = {}
        backup_data = self._load_json_backup()
        for key_str, item in backup_data.items():
            u_id = int(item["user_id"])
            ign_low = item["ign_lowercase"]
            targets[(u_id, ign_low)] = {
                "user_id": u_id,
                "ign_display": item["ign_display"],
                "state": item.get("state", "idle"),
                "kills": item.get("kills", 0),
                "deaths": item.get("deaths", 0),
                "games_played": item.get("games_played", 0),
                "last_rating": item.get("last_rating"),
                "last_position": item.get("last_position"),
                "mid_match": bool(item.get("mid_match", False)),
                "match_start_kills": item.get("match_start_kills", 0),
                "match_start_deaths": item.get("match_start_deaths", 0),
                "live_message_id": item.get("live_message_id")
            }

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT user_id, ign_lowercase, ign_display, state, kills, deaths, games_played, last_rating, last_position, mid_match, match_start_kills, match_start_deaths, live_message_id FROM snipe_targets")
                for row in cursor.fetchall():
                    u_id = int(row["user_id"])
                    ign_low = row["ign_lowercase"]
                    targets[(u_id, ign_low)] = {
                        "user_id": u_id,
                        "ign_display": row["ign_display"],
                        "state": row["state"],
                        "kills": row["kills"] or 0,
                        "deaths": row["deaths"] or 0,
                        "games_played": row.get("games_played", 0) or 0,
                        "last_rating": row["last_rating"],
                        "last_position": row.get("last_position"),
                        "mid_match": bool(row.get("mid_match", False)),
                        "match_start_kills": row.get("match_start_kills", 0) or 0,
                        "match_start_deaths": row.get("match_start_deaths", 0) or 0,
                        "live_message_id": row.get("live_message_id")
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

    # ==================== HACKER LIST (HACKUSATE) ====================

    def hackusate_player(self, ign: str, reported_by: int, reporter_name: str, is_banned: bool = False) -> int:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                ph = "%s" if self.use_pg else "?"
                cursor.execute(f"SELECT id, hackusations FROM hacker_list WHERE LOWER(ign) = LOWER({ph})", (ign,))
                existing = cursor.fetchone()
                if existing:
                    count = existing["hackusations"] + 1
                    b_val = 1 if is_banned else 0
                    if self.use_pg:
                        cursor.execute("""
                            UPDATE hacker_list
                            SET hackusations = %s, is_banned = %s, status = CASE WHEN %s THEN 'Banned' ELSE status END
                            WHERE id = %s
                        """, (count, is_banned, is_banned, existing["id"]))
                    else:
                        cursor.execute("""
                            UPDATE hacker_list
                            SET hackusations = ?, is_banned = ?, status = CASE WHEN ? THEN 'Banned' ELSE status END
                            WHERE id = ?
                        """, (count, b_val, b_val, existing["id"]))
                    conn.commit()
                    return count
                else:
                    b_val = 1 if is_banned else 0
                    status = 'Banned' if is_banned else 'Under Investigation'
                    if self.use_pg:
                        cursor.execute("""
                            INSERT INTO hacker_list (ign, reported_by, reporter_name, status, is_banned, hackusations)
                            VALUES (%s, %s, %s, %s, %s, 1)
                        """, (ign, reported_by, reporter_name, status, is_banned))
                    else:
                        cursor.execute("""
                            INSERT INTO hacker_list (ign, reported_by, reporter_name, status, is_banned, hackusations)
                            VALUES (?, ?, ?, ?, ?, 1)
                        """, (ign, reported_by, reporter_name, status, b_val))
                    conn.commit()
                    return 1
        except Exception as e:
            print(f"[DB ERROR] hackusate_player failed: {e}")
            return 1

    def get_hacker_list(self) -> List[Dict[str, Any]]:
        entries = []
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT ign, reporter_name, status, is_banned, hackusations, created_at FROM hacker_list ORDER BY hackusations DESC, created_at DESC")
                for row in cursor.fetchall():
                    entries.append({
                        "ign": row["ign"],
                        "reporter": row["reporter_name"],
                        "status": row["status"],
                        "is_banned": bool(row["is_banned"]),
                        "hackusations": row["hackusations"],
                        "created_at": str(row["created_at"])
                    })
        except Exception as e:
            print(f"[DB ERROR] get_hacker_list failed: {e}")
        return entries

    # ==================== MARKETPLACE SUBSCRIPTIONS ====================

    def add_marketplace_subscription(self, user_id: int, category: str, gun_name: str, skin_name: str, track_type: str = "both") -> bool:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                if self.use_pg:
                    cursor.execute("""
                        INSERT INTO marketplace_subscriptions (user_id, category, gun_name, skin_name, track_type)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (user_id, category, gun_name, skin_name, track_type))
                else:
                    cursor.execute("""
                        INSERT INTO marketplace_subscriptions (user_id, category, gun_name, skin_name, track_type)
                        VALUES (?, ?, ?, ?, ?)
                    """, (user_id, category, gun_name, skin_name, track_type))
                conn.commit()
                return True
        except Exception as e:
            print(f"[DB ERROR] add_marketplace_subscription failed: {e}")
            return False

    def get_user_marketplace_subscriptions(self, user_id: int) -> List[Dict[str, Any]]:
        subs = []
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                ph = "%s" if self.use_pg else "?"
                cursor.execute(f"SELECT category, gun_name, skin_name, track_type FROM marketplace_subscriptions WHERE user_id = {ph}", (user_id,))
                for row in cursor.fetchall():
                    subs.append({
                        "category": row["category"],
                        "gun_name": row["gun_name"],
                        "skin_name": row["skin_name"],
                        "track_type": row["track_type"]
                    })
        except Exception as e:
            print(f"[DB ERROR] get_user_marketplace_subscriptions failed: {e}")
        return subs


db = DatabaseManager()
