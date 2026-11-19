"""Which seasons can API-Football's free plan read, and how much quota is left?

Uses about 18 of the free plan's 100 daily requests:
  /status (doesn't count towards the quota), /leagues for the Premier League,
  /teams for each season from 2010 on, and one current squad.

    python check_api_football.py
"""

import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

BASE_URL = "https://v3.football.api-sports.io"
PREMIER_LEAGUE = 39
MANCHESTER_UNITED = 33
FIRST_SEASON, LAST_SEASON = 2010, 2025

load_dotenv(Path(__file__).resolve().parent.parent / ".env")
KEY = os.environ.get("API_FOOTBALL_KEY", "")
if not KEY or KEY == "your_api_football_key_here":
    sys.exit("Put your API-Football key in ../.env first (API_FOOTBALL_KEY=...).")

client = httpx.Client(base_url=BASE_URL, headers={"x-apisports-key": KEY}, timeout=30)


def get(path: str, **params) -> dict:
    data = client.get(path, params=params).json()
    # API-Football reports problems (bad key, plan limits) in "errors" with a 200 status.
    errors = data.get("errors")
    if errors:
        data["_error"] = "; ".join(f"{k}: {v}" for k, v in errors.items()) if isinstance(errors, dict) else str(errors)
    return data


status = get("/status")
if "_error" in status:
    sys.exit(f"API-Football refused the key: {status['_error']}")
account = status["response"]
print(f"Plan: {account['subscription']['plan']}")
print(f"Requests today: {account['requests']['current']} / {account['requests']['limit_day']}\n")

league = get("/leagues", id=PREMIER_LEAGUE)
seasons = {s["year"]: s for s in league["response"][0]["seasons"]} if league.get("response") else {}
print(f"Premier League seasons API-Football knows about: {min(seasons)}-{max(seasons)}\n" if seasons else "No league info.\n")

print("Can the free plan read each season? (teams list, 1 request per season)")
readable = []
for year in range(FIRST_SEASON, LAST_SEASON + 1):
    teams = get("/teams", league=PREMIER_LEAGUE, season=year)
    coverage = seasons.get(year, {}).get("coverage", {})
    extras = ", ".join(k for k in ("lineups", "events") if coverage.get("fixtures", {}).get(f"{k}")) or "-"
    if "_error" in teams:
        print(f"  {year}/{(year + 1) % 100:02d}: no   ({teams['_error']})")
    else:
        readable.append(year)
        print(f"  {year}/{(year + 1) % 100:02d}: yes  {teams['results']} teams; match data: {extras}")

squad = get("/players/squads", team=MANCHESTER_UNITED)
print("\nCurrent squad endpoint:", "works" if "_error" not in squad else squad["_error"])

after = get("/status")["response"]["requests"]
print(f"\nSeasons the free plan can read: {readable[0]}-{readable[-1]}" if readable else "\nNo readable seasons.")
print(f"Requests used today: {after['current']} / {after['limit_day']}")
