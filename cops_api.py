import aiohttp
import asyncio
import re
from typing import Dict, Any, Optional, List

def format_player_ign(raw_name: str, tag: Optional[str] = None) -> str:
    """
    Prevents double clan tags (e.g., '[URGH] [URGH] MiesterZ' -> '[URGH] MiesterZ').
    """
    if not raw_name:
        return "Unknown"
    
    clean_name = raw_name.strip()
    
    # Remove any existing bracketed tag if it matches tag or pattern
    if tag:
        tag_pattern = f"[{tag}]"
        while clean_name.startswith(tag_pattern):
            clean_name = clean_name[len(tag_pattern):].strip()
            
    # Strip any leading bracketed tag if tag wasn't explicitly provided but name has it
    match = re.match(r'^\[([^\]]+)\]\s*(.+)$', clean_name)
    if match:
        extracted_tag = match.group(1)
        extracted_name = match.group(2).strip()
        # If tag wasn't passed, use extracted tag
        if not tag:
            tag = extracted_tag
        clean_name = extracted_name

    if tag:
        return f"[{tag}] {clean_name}"
    return clean_name


class CriticalOpsAPI:
    """
    Critical Ops Game API Client with multi-rank support, live marketplace integration,
    and profile tracking.
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
        # Strip brackets if user passed [TAG] IGN
        ign_clean = ign.strip()
        if ign_clean.startswith("[") and "]" in ign_clean:
            ign_clean = ign_clean.split("]", 1)[1].strip()

        session = await self.get_session()
        try:
            async with session.get(f"{self.base_url}/player/{ign_clean}", timeout=aiohttp.ClientTimeout(total=8)) as resp:
                if resp.status != 200:
                    return None
                raw     = await resp.json()
                summary = raw.get("summary", {})
                if not summary:
                    return None

                user_id   = summary.get("userId", "")
                raw_name  = summary.get("name", ign_clean)
                level     = summary.get("level", 0)
                mmr       = summary.get("mmr", 0)
                banned    = summary.get("banned", False)

                rank_info = summary.get("rank", {})
                rank_name = rank_info.get("name", "Unranked") if isinstance(rank_info, dict) else "Unranked"

                highest   = summary.get("highestRank", {})
                peak_rank = highest.get("name", rank_name) if isinstance(highest, dict) else rank_name

                lb_pos    = summary.get("leaderboardPosition")

                clan_info = summary.get("clan", {}) or {}
                clan_tag  = clan_info.get("tag", "") if isinstance(clan_info, dict) else ""

                formatted_ign = format_player_ign(raw_name, clan_tag)

                # Career & Season K/D Tracking
                career = summary.get("career", {}).get("ranked", {})
                career_kills  = career.get("k", 0)
                career_deaths = career.get("d", 0)

                seasons = summary.get("seasons", [])
                latest_season = seasons[-1].get("ranked", {}) if seasons else {}
                season_kills  = latest_season.get("k", career_kills)
                season_deaths = latest_season.get("d", career_deaths)

                kd = round(career_kills / max(1, career_deaths), 2)

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
                creation_year     = max(2017, 2026 - (17 - earliest))
                account_age_years = 2026 - creation_year

                return {
                    "ign":               formatted_ign,
                    "ign_raw":           raw_name,
                    "id":                f"COP-{user_id}",
                    "level":             level,
                    "account_age_str":   f"{account_age_years} years ({creation_year})",
                    "rating":            mmr,
                    "peak_rating":       peak_rating,
                    "lowest_rating":     lowest_rating,
                    "rank":              rank_name,
                    "rank_position":     lb_pos,
                    "kills":             career_kills,
                    "deaths":            career_deaths,
                    "season_kills":      season_kills,
                    "season_deaths":     season_deaths,
                    "kd_ratio":          kd,
                    "clan_tag":          clan_tag,
                    "banned":            banned,
                }
        except Exception as e:
            print(f"[COPS API ERROR] /player/{ign_clean} failed: {e}")
            return None

    # ==================== LEADERBOARD (ELITE & SPEC OPS) ====================

    async def get_elite_leaderboard(self) -> List[Dict[str, Any]]:
        """
        Fetch leaderboard with clean IGN formatting (no double clan tags).
        Includes Spec Ops and Elite Ops players.
        """
        session = await self.get_session()
        players = []
        try:
            async with session.get(f"{self.base_url}/leaderboard/elite?limit=100", timeout=aiohttp.ClientTimeout(total=8)) as resp:
                if resp.status != 200:
                    return []
                data    = await resp.json()
                entries = data.get("entries", [])
                for item in entries:
                    raw_name = item.get("name", "")
                    rating   = item.get("rating", 0)
                    rank_pos = item.get("rank")
                    tag      = item.get("tag", "")
                    
                    if raw_name and rating:
                        formatted_ign = format_player_ign(raw_name, tag)
                        players.append({
                            "ign":           formatted_ign,
                            "ign_raw":       raw_name,
                            "tag":           tag or "",
                            "rank":          "Elite Ops" if rating >= 2000 else "Spec Ops",
                            "rank_position": rank_pos,
                            "rating":        rating,
                        })
        except Exception as e:
            print(f"[COPS API ERROR] /leaderboard/elite failed: {e}")
        return players

    # ==================== LIVE MARKETPLACE FEED ====================

    async def get_marketplace_feed(self) -> List[Dict[str, Any]]:
        """
        Fetch live marketplace activity (Buy requests and Sell requests).
        """
        session = await self.get_session()
        try:
            async with session.get(f"{self.base_url}/feed", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("events", [])
        except Exception:
            pass
        return []


cops_api_client = CriticalOpsAPI()
