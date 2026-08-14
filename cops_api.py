import aiohttp
import asyncio
from typing import Dict, Any, Optional, List

class CriticalOpsAPI:
    """
    Real-Time Critical Ops Game API Client.
    Fetches official player profiles, stats, and live Spec Ops+ / Elite Ops leaderboards
    directly from Critical Ops database proxy endpoints.
    """
    def __init__(self):
        self.base_url = "https://cops.melodia.cloud/api"
        self.session: Optional[aiohttp.ClientSession] = None

    async def get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json"
            }
            self.session = aiohttp.ClientSession(headers=headers)
        return self.session

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()

    async def get_player_by_ign(self, ign: str) -> Optional[Dict[str, Any]]:
        ign_clean = ign.strip()
        session = await self.get_session()
        
        try:
            async with session.get(f"{self.base_url}/player/{ign_clean}") as resp:
                if resp.status == 200:
                    raw = await resp.json()
                    summary = raw.get("summary", {})
                    if not summary:
                        return None
                    
                    user_id = summary.get("userId", f"COP-{abs(hash(ign_clean)) % 8999999 + 1000000}")
                    name = summary.get("name", ign_clean)
                    level = summary.get("level", 0)
                    mmr = summary.get("mmr", 0)
                    
                    rank_info = summary.get("rank", {})
                    rank_name = rank_info.get("name", "Unranked") if isinstance(rank_info, dict) else "Unranked"
                    
                    highest_rank_info = summary.get("highestRank", {})
                    peak_rank_name = highest_rank_info.get("name", rank_name) if isinstance(highest_rank_info, dict) else rank_name
                    
                    leaderboard_pos = summary.get("leaderboardPosition")
                    
                    career = summary.get("career", {}).get("ranked", {})
                    kills = career.get("k", 0)
                    deaths = career.get("d", 0)
                    kd_ratio = career.get("kd", round(kills / max(1, deaths), 2))
                    
                    seasons = summary.get("seasons", [])
                    mmr_history = [mmr]
                    for s in seasons:
                        r = s.get("ranked", {})
                        if r.get("games", 0) > 0 and "mmr" in r:
                            mmr_history.append(r["mmr"])
                    
                    peak_rating = max(mmr_history)
                    lowest_rating = min(mmr_history)
                    
                    earliest_season = min([s.get("season", 0) for s in seasons if s.get("ranked", {}).get("games", 0) > 0], default=17)
                    creation_year = max(2017, 2026 - (17 - earliest_season))
                    account_age_years = 2026 - creation_year

                    return {
                        "ign": name,
                        "id": f"COP-{user_id}",
                        "level": level,
                        "account_creation_year": creation_year,
                        "account_age_str": f"{account_age_years} years ({creation_year})",
                        "rating": mmr,
                        "peak_rating": peak_rating,
                        "lowest_rating": lowest_rating,
                        "rank": rank_name,
                        "rank_position": leaderboard_pos,
                        "kills": kills,
                        "deaths": deaths,
                        "kd_ratio": kd_ratio,
                        "raw": summary
                    }
                elif resp.status == 404:
                    return None
        except Exception as e:
            print(f"[COPS API ERROR] Query for {ign_clean} failed: {e}")
            return None

        return None

    async def get_spec_ops_leaderboard(self) -> List[Dict[str, Any]]:
        """
        Fetch full live Spec Ops & Elite Ops players down to 1800+ rating from Critical Ops database.
        Combines Elite Ops and Ranked leaderboards.
        """
        session = await self.get_session()
        leaderboard_players = []
        seen_names = set()
        
        # 1. Fetch Elite Ops Top Leaderboard
        try:
            async with session.get(f"{self.base_url}/leaderboard/elite") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    entries = data.get("entries", [])
                    for item in entries:
                        name = item.get("name")
                        if name and name.lower() not in seen_names:
                            seen_names.add(name.lower())
                            leaderboard_players.append({
                                "ign": name,
                                "rank": "Elite Ops",
                                "rank_position": item.get("rank"),
                                "rating": item.get("rating", 2000),
                                "movement": item.get("movement", 0)
                            })
        except Exception as e:
            print(f"[COPS API ERROR] Elite leaderboard query failed: {e}")

        # 2. Fetch Extended Spec Ops Leaderboard (Up to 1000 players down to 1800 MMR)
        try:
            async with session.get(f"{self.base_url}/leaderboard/ranked") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    entries = data.get("entries", [])
                    for idx, item in enumerate(entries, start=len(leaderboard_players) + 1):
                        name = item.get("name")
                        if name and name.lower() not in seen_names:
                            seen_names.add(name.lower())
                            rating = item.get("rating", 1800 + max(0, 200 - idx))
                            if rating >= 1800:
                                leaderboard_players.append({
                                    "ign": name,
                                    "rank": "Spec Ops" if rating < 2000 else "Elite Ops",
                                    "rank_position": idx,
                                    "rating": rating,
                                    "movement": 0
                                })
        except Exception as e:
            print(f"[COPS API ERROR] Extended ranked leaderboard query failed: {e}")

        return leaderboard_players

cops_api_client = CriticalOpsAPI()
