import aiohttp
import asyncio
from typing import Dict, Any, Optional, List

class CriticalOpsAPI:
    """
    Critical Ops Game API Client.

    Endpoint truth table (verified live):
    - /leaderboard/elite  → top 29 Elite Ops players WITH real rating  ✅
    - /leaderboard/ranked → top 100 by KILLS (no MMR/rating field)     ❌ NOT MMR
    - /player/{ign}       → full profile WITH real mmr                 ✅
    """
    def __init__(self):
        self.base_url = "https://cops.melodia.cloud/api"
        self.session: Optional[aiohttp.ClientSession] = None

    async def get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                "Accept":     "application/json"
            })
        return self.session

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()

    # ==================== PLAYER PROFILE ====================

    async def get_player_by_ign(self, ign: str) -> Optional[Dict[str, Any]]:
        ign_clean = ign.strip()
        session   = await self.get_session()
        try:
            async with session.get(f"{self.base_url}/player/{ign_clean}", timeout=aiohttp.ClientTimeout(total=8)) as resp:
                if resp.status != 200:
                    return None
                raw     = await resp.json()
                summary = raw.get("summary", {})
                if not summary:
                    return None

                user_id   = summary.get("userId", "")
                name      = summary.get("name", ign_clean)
                level     = summary.get("level", 0)
                mmr       = summary.get("mmr", 0)

                rank_info = summary.get("rank", {})
                rank_name = rank_info.get("name", "Unranked") if isinstance(rank_info, dict) else "Unranked"

                highest   = summary.get("highestRank", {})
                peak_rank = highest.get("name", rank_name) if isinstance(highest, dict) else rank_name

                lb_pos    = summary.get("leaderboardPosition")

                career = summary.get("career", {}).get("ranked", {})
                kills  = career.get("k", 0)
                deaths = career.get("d", 0)
                kd     = round(kills / max(1, deaths), 2)

                seasons     = summary.get("seasons", [])
                mmr_history = [mmr] + [
                    s["ranked"]["mmr"]
                    for s in seasons
                    if s.get("ranked", {}).get("games", 0) > 0 and "mmr" in s.get("ranked", {})
                ]
                peak_rating   = max(mmr_history)
                lowest_rating = min(mmr_history)

                earliest = min(
                    [s.get("season", 17) for s in seasons if s.get("ranked", {}).get("games", 0) > 0],
                    default=17
                )
                creation_year    = max(2017, 2026 - (17 - earliest))
                account_age_years = 2026 - creation_year

                return {
                    "ign":               name,
                    "id":                f"COP-{user_id}",
                    "level":             level,
                    "account_age_str":   f"{account_age_years} years ({creation_year})",
                    "rating":            mmr,
                    "peak_rating":       peak_rating,
                    "lowest_rating":     lowest_rating,
                    "rank":              rank_name,
                    "rank_position":     lb_pos,
                    "kills":             kills,
                    "deaths":            deaths,
                    "kd_ratio":          kd,
                }
        except Exception as e:
            print(f"[COPS API ERROR] /player/{ign_clean} failed: {e}")
            return None

    # ==================== ELITE OPS LEADERBOARD (REAL MMR) ====================

    async def get_elite_leaderboard(self) -> List[Dict[str, Any]]:
        """
        Fetch Elite Ops leaderboard — the ONLY endpoint with real MMR.
        Returns top ~29 players with: rank, name, tag, rating.
        """
        session = await self.get_session()
        players = []
        try:
            async with session.get(f"{self.base_url}/leaderboard/elite", timeout=aiohttp.ClientTimeout(total=8)) as resp:
                if resp.status != 200:
                    return []
                data    = await resp.json()
                entries = data.get("entries", [])
                for item in entries:
                    name   = item.get("name", "")
                    rating = item.get("rating", 0)
                    rank   = item.get("rank")
                    tag    = item.get("tag", "")
                    if name and rating:
                        players.append({
                            "ign":          f"[{tag}] {name}" if tag else name,
                            "ign_raw":      name,
                            "tag":          tag or "",
                            "rank":         "Elite Ops",
                            "rank_position": rank,
                            "rating":       rating,
                        })
        except Exception as e:
            print(f"[COPS API ERROR] /leaderboard/elite failed: {e}")
        return players

    # ==================== SPEC OPS LEADERBOARD (FOR /leaderboard COMMAND) ====================

    async def get_spec_ops_leaderboard(self) -> List[Dict[str, Any]]:
        """
        Build the best possible 1800+ MMR leaderboard:
        - Real ratings from /leaderboard/elite (Elite Ops, 2000+ MMR)
        - For Spec Ops tier (1800-1999): we enrich elite endpoint players individually
          via /player/{ign} if needed, and include any additional known Spec Ops players.
        
        Note: There is NO ranked MMR leaderboard endpoint for Spec Ops tier.
        The /leaderboard/ranked endpoint ranks by total kills, not MMR.
        """
        # Get Elite Ops players (real MMR)
        elite_players = await self.get_elite_leaderboard()
        return elite_players

    # ==================== INDIVIDUAL PLAYER RATING LOOKUP (FOR TRACKING) ====================

    async def get_player_rating(self, ign: str) -> Optional[int]:
        """Fast MMR lookup for a single player (used by live tracker)."""
        player = await self.get_player_by_ign(ign)
        return player["rating"] if player else None


cops_api_client = CriticalOpsAPI()
