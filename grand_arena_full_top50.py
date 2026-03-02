# grand_arena_full_top50.py
import asyncio
import csv
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
import random
import httpx

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Encoding": "gzip, deflate",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://fantasy.grandarena.gg/",
}

async def fetch_all_contests(client):
    url = "https://fantasy.grandarena.gg/api/contests"
    params = {
        "status": "OPEN,UPCOMING,STARTING_SOON,LIVE,COMPLETED",
        "limit": 100,
        "offset": 0,
        "includeUserContext": "true",
        "hidePrivate": "true"
    }
    try:
        r = await client.get(url, params=params, timeout=20)
        data = r.json()
        return data.get("contests", [])
    except:
        return []

async def fetch_leaderboard(client, contest_id):
    url = f"https://fantasy.grandarena.gg/api/contests/{contest_id}/leaderboard"
    params = {"limit": 50, "offset": 0, "includeUserPosition": "true"}
    try:
        r = await client.get(url, params=params, timeout=20)
        if r.status_code == 200:
            return r.json().get("entries", [])
    except:
        pass
    return None

def flatten_entry(entry):
    return {
        "rank": entry.get("rank"),
        "username": entry.get("username"),
        "score": entry.get("score"),
        "entryId": entry.get("entryId"),
        "cardImages": ",".join(entry.get("cardImages", []))
    }

async def main():
    async with httpx.AsyncClient(http2=True, headers=HEADERS) as client:
        # 1. 更新 contests.json
        contests = await fetch_all_contests(client)
        if contests:
            with open("contests.json", "w", encoding="utf-8") as f:
                json.dump(contests, f, ensure_ascii=False, indent=2)
            print(f"已更新 contests.json ({len(contests)} 场)")

        # 2. 检查并更新已结束的 leaderboard
        now = datetime.now(timezone.utc)
        updated = 0

        for c in contests:
            cid = c["_id"]
            end_str = c.get("endDate")
            if not end_str:
                continue
            try:
                end_dt = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
            except:
                continue

            if end_dt + timedelta(minutes=5) > now:
                continue

            json_path = DATA_DIR / f"leaderboard_{cid}.json"
            if json_path.exists():
                continue

            entries = await fetch_leaderboard(client, cid)
            if not entries:
                continue

            data = {
                "contest_id": cid,
                "contest_name": c.get("name", ""),
                "description": c.get("description", ""),
                "startDate": c.get("startDate"),
                "endDate": end_str,
                "entries_count": c.get("entries", 0),
                "prizePool": c.get("prizePool", 0),
                "fetchedAt": now.isoformat(),
                "top50": [flatten_entry(e) for e in entries[:50]]
            }

            json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
            updated += 1
            print(f"新增 {json_path.name}")

            await asyncio.sleep(random.uniform(4, 9))

        print(f"本次新增 {updated} 场 Top50 数据")

if __name__ == "__main__":
    asyncio.run(main())
