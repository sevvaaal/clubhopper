"""Collect raw football data from API-Football, a little every day.

Two phases, over a fixed queue of league-seasons (Süper Lig first, newest
season first):

1. Squads: each league-season's teams, fixture list and every team's player
   list (with nationality, age, photo). About 40 requests per league-season,
   and enough for the chain and career-path games.
2. Matches: each match's details (lineups with benches, goals, cards,
   substitutions), one request per match because the free plan can't batch
   them. Matches between teams near the top of the table come first.

Free plan limits this works around: 100 requests a day, 10 a minute, page
parameter at most 3, no `ids` batching, seasons 2022/23-2024/25 only.

Every API response is saved under data/raw/. Anything already saved is never
requested again, so the script just picks up where it stopped: run it once a
day and the free plan's 100 requests go further each time. It stops on its
own before the daily quota runs out.

    python collect.py              # spend today's quota
    python collect.py --dry-run    # only show what's left to fetch
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
BASE_URL = "https://v3.football.api-sports.io"

# API-Football league ids. Order = collection priority.
LEAGUES = {
    "super-lig": 203,
    "premier-league": 39,
    "la-liga": 140,
    "serie-a": 135,
    "bundesliga": 78,
    "ligue-1": 61,
}
# The seasons the free plan can read (start year: 2024 = 2024/25).
SEASONS = [2024, 2023, 2022]

DAILY_RESERVE = 5  # leave a few requests for manual checks
SECONDS_BETWEEN_REQUESTS = 6.5  # free plan: 10 requests a minute
MAX_PAGE = 3  # free plan limit on the page parameter

load_dotenv(ROOT / ".env")
KEY = os.environ.get("API_FOOTBALL_KEY", "")


class QuotaReached(Exception):
    pass


class Api:
    def __init__(self, dry_run: bool):
        self.dry_run = dry_run
        self.client = httpx.Client(base_url=BASE_URL, headers={"x-apisports-key": KEY}, timeout=60)
        self.last_request = 0.0
        self.used = 0
        status = self.client.get("/status").json()["response"]["requests"]  # /status is free
        self.left = status["limit_day"] - status["current"] - DAILY_RESERVE
        print(f"Quota today: {status['current']} used of {status['limit_day']}, {max(self.left, 0)} available to spend\n")

    def get(self, path: str, **params) -> dict:
        if self.dry_run:
            raise QuotaReached
        if self.used >= self.left:
            raise QuotaReached
        wait = self.last_request + SECONDS_BETWEEN_REQUESTS - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        self.last_request = time.monotonic()
        data = self.client.get(path, params=params).json()
        self.used += 1
        errors = data.get("errors")
        if errors:
            message = json.dumps(errors)
            if "request" in message.lower() and "limit" in message.lower():
                raise QuotaReached
            raise RuntimeError(f"{path} {params}: {message}")
        return data


def save(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False))


def load(path: Path) -> dict:
    return json.loads(path.read_text())


def season_label(league: str, season: int) -> str:
    return f"{league} {season}/{(season + 1) % 100:02d}"


def collect_squads(api: Api, league: str, league_id: int, season: int) -> None:
    """Phase 1 for one league-season: teams, fixture list and each team's players."""
    folder = RAW / league / str(season)
    teams_file = folder / "teams.json"
    if not teams_file.exists():
        save(teams_file, api.get("/teams", league=league_id, season=season))

    fixtures_file = folder / "fixtures.json"
    if not fixtures_file.exists():
        save(fixtures_file, api.get("/fixtures", league=league_id, season=season))

    # Each team's players that season (with nationality, age, photo), up to 3 pages.
    capped = []
    for team_id in sorted(t["team"]["id"] for t in load(teams_file)["response"]):
        first = folder / "team-players" / f"{team_id}-page-1.json"
        if not first.exists():
            save(first, api.get("/players", team=team_id, season=season, page=1))
        total = load(first)["paging"]["total"]
        if total > MAX_PAGE:
            capped.append(team_id)
        for page in range(2, min(total, MAX_PAGE) + 1):
            page_file = folder / "team-players" / f"{team_id}-page-{page}.json"
            if not page_file.exists():
                save(page_file, api.get("/players", team=team_id, season=season, page=page))
    note = f" ({len(capped)} teams had more than {MAX_PAGE} pages; their extra players will come from lineups)" if capped else ""
    print(f"  {season_label(league, season)}: squads complete{note}")
    (folder / "SQUADS_COMPLETE").write_text("")


def ranked_fixture_ids(fixtures: list[dict]) -> list[int]:
    """Finished matches, most interesting first: matches between teams near the
    top of the final table (title races, derbies between big clubs) come first.
    The table is worked out from the results, so it costs no extra request."""
    points: dict[int, int] = {}
    for match in fixtures:
        home, away = match["teams"]["home"], match["teams"]["away"]
        for side in (home, away):
            points.setdefault(side["id"], 0)
        if match["fixture"]["status"]["short"] not in ("FT", "AET", "PEN"):
            continue
        if home["winner"]:
            points[home["id"]] += 3
        elif away["winner"]:
            points[away["id"]] += 3
        else:
            points[home["id"]] += 1
            points[away["id"]] += 1
    position = {team: rank for rank, team in enumerate(sorted(points, key=points.get, reverse=True), start=1)}
    finished = [m for m in fixtures if m["fixture"]["status"]["short"] in ("FT", "AET", "PEN")]
    finished.sort(
        key=lambda m: (
            position[m["teams"]["home"]["id"]] + position[m["teams"]["away"]["id"]],
            m["fixture"]["id"],
        )
    )
    return [m["fixture"]["id"] for m in finished]


def collect_matches(api: Api, league: str, season: int) -> None:
    """Phase 2 for one league-season: match details (lineups, events), one request
    per match, most interesting matches first."""
    folder = RAW / league / str(season)
    fixture_ids = ranked_fixture_ids(load(folder / "fixtures.json")["response"])
    for fixture_id in fixture_ids:
        match_file = folder / "matches" / f"{fixture_id}.json"
        if not match_file.exists():
            save(match_file, api.get("/fixtures", id=fixture_id))
    print(f"  {season_label(league, season)}: all {len(fixture_ids)} match details complete")
    (folder / "MATCHES_COMPLETE").write_text("")


def report(queue: list[tuple[str, int, int]]) -> None:
    print("\nProgress:")
    for league, _, season in queue:
        folder = RAW / league / str(season)
        squads = "squads ✓" if (folder / "SQUADS_COMPLETE").exists() else "squads …"
        matches_dir = folder / "matches"
        fetched = len(list(matches_dir.glob("*.json"))) if matches_dir.exists() else 0
        total = load(folder / "fixtures.json")["results"] if (folder / "fixtures.json").exists() else "?"
        print(f"  {season_label(league, season):22} {squads}   matches {fetched}/{total}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="don't fetch, just report progress")
    args = parser.parse_args()
    if not KEY or KEY == "your_api_football_key_here":
        sys.exit("Put your API-Football key in ../.env first (API_FOOTBALL_KEY=...).")

    api = Api(args.dry_run)
    queue = [(league, league_id, season) for league, league_id in LEAGUES.items() for season in SEASONS]
    try:
        # Phase 1: squads for every league-season (enough for the chain and career games).
        for league, league_id, season in queue:
            if not (RAW / league / str(season) / "SQUADS_COMPLETE").exists():
                collect_squads(api, league, league_id, season)
        # Phase 2: match details, league-season by league-season.
        for league, _, season in queue:
            if not (RAW / league / str(season) / "MATCHES_COMPLETE").exists():
                collect_matches(api, league, season)
    except QuotaReached:
        print("\nStopped: today's quota is spent (or --dry-run). Run again tomorrow to continue.")
    finally:
        print(f"Requests used this run: {api.used}")
        report(queue)


if __name__ == "__main__":
    main()
