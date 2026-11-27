"""Collect raw football data from API-Football into data/raw/.

Every API response is saved under data/raw/ and never requested again, so the
script picks up where it stopped. It stops on its own before the daily quota
runs out. The plan (free or Pro) is read from the account's /status, or set
with --plan.

Phases, newest season first:

1. Squads: each competition-season's teams, fixture list and players (with
   nationality, age, photo and that season's appearances). Enough for the
   chain and career-path games.
2. Transfers: one request per club, used by build.py to drop players the API
   wrongly lists at clubs they only joined later.
3. Matches: each match's details (lineups with benches, goals, cards,
   substitutions).

Free plan (100 requests a day, 10 a minute): seasons 2022/23-2024/25 only,
players fetched per team and capped at 3 pages (60 players), one request per
match. Run it once a day.

Pro plan (7500 a day): every season the API covers up to 2025/26, players
fetched league-wide with no page cap, match details 20 per request.

    python collect.py                  # spend today's quota
    python collect.py --dry-run        # only show what's left to fetch
    python collect.py --only serie-a   # one competition (repeatable)
    python collect.py --seasons 2023   # some seasons only (repeatable)
    python collect.py --rate 100       # requests a minute (Pro)
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

# API-Football league ids and the first season the API covers. Order =
# collection priority within a season.
COMPETITIONS = {
    "super-lig": (203, 2011),
    "premier-league": (39, 2010),
    "la-liga": (140, 2010),
    "serie-a": (135, 2010),
    "bundesliga": (78, 2010),
    "ligue-1": (61, 2010),
    "champions-league": (2, 2011),
    "europa-league": (3, 2014),
}
LEAGUES = {slug: league_id for slug, (league_id, _) in COMPETITIONS.items()}
FREE_COMPETITIONS = ["super-lig", "premier-league", "la-liga", "serie-a", "bundesliga", "ligue-1"]
FREE_SEASONS = [2024, 2023, 2022]  # start year: 2024 = 2024/25
LAST_SEASON = 2025  # 2026/27 is still being played; left out for now

FREE = {"reserve": 5, "per_minute": 10, "max_page": 3, "batch": 1}
PRO = {"reserve": 50, "per_minute": 100, "max_page": None, "batch": 20}
FINISHED = ("FT", "AET", "PEN")

load_dotenv(ROOT / ".env")
KEY = os.environ.get("API_FOOTBALL_KEY", "")


class QuotaReached(Exception):
    pass


class Api:
    def __init__(self, dry_run: bool, plan: str | None, per_minute: int | None):
        self.dry_run = dry_run
        self.client = httpx.Client(base_url=BASE_URL, headers={"x-apisports-key": KEY}, timeout=60)
        self.last_request = 0.0
        self.used = 0
        self.settings = dict(FREE)  # until /status says which plan this is
        status = self.call("/status")["response"]  # /status is free
        account_plan = status["subscription"]["plan"]
        self.pro = (plan or ("free" if account_plan.lower() == "free" else "pro")) == "pro"
        self.settings = dict(PRO if self.pro else FREE)
        if per_minute:
            self.settings["per_minute"] = per_minute
        requests = status["requests"]
        self.left = requests["limit_day"] - requests["current"] - self.settings["reserve"]
        print(f"Plan: {account_plan} (collecting as {'Pro' if self.pro else 'free'}), "
              f"ends {status['subscription'].get('end', '?')[:16]}")
        print(f"Quota today: {requests['current']} used of {requests['limit_day']}, "
              f"{max(self.left, 0)} available to spend, {self.settings['per_minute']} a minute\n")

    def call(self, path: str, **params) -> dict:
        """One HTTP request, retried through dropped connections and rate limits."""
        for attempt in range(8):
            wait = self.last_request + 60 / self.settings["per_minute"] - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            self.last_request = time.monotonic()
            try:
                response = self.client.get(path, params=params)
                if response.status_code in (429, 500, 502, 503, 504):
                    raise httpx.TransportError(f"HTTP {response.status_code}")
                data = response.json()
            except (httpx.TransportError, ValueError) as e:
                pause = min(15 * 2**attempt, 300)
                print(f"  network problem ({e}); retrying in {pause}s")
                time.sleep(pause)
                continue
            errors = data.get("errors")
            if errors and "ratelimit" in json.dumps(errors).lower().replace(" ", ""):
                print("  per-minute limit hit; waiting a minute")
                time.sleep(61)
                continue
            return data
        raise RuntimeError(f"{path} {params}: gave up after repeated network errors")

    def get(self, path: str, **params) -> dict:
        if self.dry_run or self.used >= self.left:
            raise QuotaReached
        data = self.call(path, **params)
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
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False))
    tmp.replace(path)  # never leave a half-written file behind


def load(path: Path) -> dict:
    return json.loads(path.read_text())


def season_label(slug: str, season: int) -> str:
    return f"{slug} {season}/{(season + 1) % 100:02d}"


def build_queue(pro: bool, only: list[str], seasons: list[int]) -> list[tuple[str, int, int]]:
    slugs = list(COMPETITIONS) if pro else FREE_COMPETITIONS
    if only:
        slugs = [s for s in slugs if s in only]
    years = range(LAST_SEASON, 2009, -1) if pro else FREE_SEASONS
    queue = [
        (slug, COMPETITIONS[slug][0], year)
        for year in years
        for slug in slugs
        if year >= COMPETITIONS[slug][1] and (not seasons or year in seasons)
    ]
    return queue


def collect_basics(api: Api, folder: Path, league_id: int, season: int) -> None:
    teams_file = folder / "teams.json"
    if not teams_file.exists():
        save(teams_file, api.get("/teams", league=league_id, season=season))
    fixtures_file = folder / "fixtures.json"
    if not fixtures_file.exists():
        save(fixtures_file, api.get("/fixtures", league=league_id, season=season))


def collect_squads_free(api: Api, slug: str, league_id: int, season: int) -> None:
    """Free plan: each team's players, up to 3 pages of 20."""
    folder = RAW / slug / str(season)
    if (folder / "SQUADS_COMPLETE").exists():
        return
    collect_basics(api, folder, league_id, season)
    max_page = api.settings["max_page"]
    capped = []
    for team_id in sorted(t["team"]["id"] for t in load(folder / "teams.json")["response"]):
        first = folder / "team-players" / f"{team_id}-page-1.json"
        if not first.exists():
            save(first, api.get("/players", team=team_id, season=season, page=1))
        total = load(first)["paging"]["total"]
        if total > max_page:
            capped.append(team_id)
        for page in range(2, min(total, max_page) + 1):
            page_file = folder / "team-players" / f"{team_id}-page-{page}.json"
            if not page_file.exists():
                save(page_file, api.get("/players", team=team_id, season=season, page=page))
    note = f" ({len(capped)} teams had more than {max_page} pages)" if capped else ""
    print(f"  {season_label(slug, season)}: squads complete{note}")
    (folder / "SQUADS_COMPLETE").write_text("")


def collect_squads_pro(api: Api, slug: str, league_id: int, season: int) -> None:
    """Pro: every player of the competition-season, league-wide, all pages."""
    folder = RAW / slug / str(season)
    if (folder / "PLAYERS_COMPLETE").exists():
        return
    collect_basics(api, folder, league_id, season)
    page, total = 1, 1
    while page <= total:
        page_file = folder / "players" / f"page-{page}.json"
        if not page_file.exists():
            save(page_file, api.get("/players", league=league_id, season=season, page=page))
        total = load(page_file)["paging"]["total"]
        page += 1
    print(f"  {season_label(slug, season)}: all {total} player pages complete")
    (folder / "PLAYERS_COMPLETE").write_text("")


def collect_transfers(api: Api, queue: list[tuple[str, int, int]]) -> None:
    """Transfers of every club we have a squad for, one request per club.

    The API copies some players' stats to clubs they only joined later;
    build.py uses these dates to drop those.
    """
    team_ids: dict[int, None] = {}
    for slug, _, season in queue:
        teams_file = RAW / slug / str(season) / "teams.json"
        if teams_file.exists():
            team_ids.update(dict.fromkeys(t["team"]["id"] for t in load(teams_file)["response"]))
    for team_id in team_ids:
        out = RAW / "transfers" / f"team-{team_id}.json"
        if not out.exists():
            save(out, api.get("/transfers", team=team_id))


def ranked_fixture_ids(fixtures: list[dict]) -> list[int]:
    """Finished matches, most interesting first: matches between teams near the
    top of the final table come first. The table is worked out from the
    results, so it costs no extra request."""
    points: dict[int, int] = {}
    for match in fixtures:
        home, away = match["teams"]["home"], match["teams"]["away"]
        for side in (home, away):
            points.setdefault(side["id"], 0)
        if match["fixture"]["status"]["short"] not in FINISHED:
            continue
        if home["winner"]:
            points[home["id"]] += 3
        elif away["winner"]:
            points[away["id"]] += 3
        else:
            points[home["id"]] += 1
            points[away["id"]] += 1
    position = {team: rank for rank, team in enumerate(sorted(points, key=points.get, reverse=True), start=1)}
    finished = [m for m in fixtures if m["fixture"]["status"]["short"] in FINISHED]
    finished.sort(
        key=lambda m: (
            position[m["teams"]["home"]["id"]] + position[m["teams"]["away"]["id"]],
            m["fixture"]["id"],
        )
    )
    return [m["fixture"]["id"] for m in finished]


def collect_matches(api: Api, slug: str, season: int) -> None:
    """Match details (lineups, events), saved one file per match. Pro fetches
    20 matches a request; the free plan one."""
    folder = RAW / slug / str(season)
    if (folder / "MATCHES_COMPLETE").exists() or not (folder / "fixtures.json").exists():
        return
    fixture_ids = ranked_fixture_ids(load(folder / "fixtures.json")["response"])
    missing = [f for f in fixture_ids if not (folder / "matches" / f"{f}.json").exists()]
    batch = api.settings["batch"]
    for i in range(0, len(missing), batch):
        ids = missing[i : i + batch]
        if batch == 1:
            data = api.get("/fixtures", id=ids[0])
        else:
            data = api.get("/fixtures", ids="-".join(map(str, ids)))
        for match in data["response"]:
            save(folder / "matches" / f"{match['fixture']['id']}.json", {"response": [match]})
    still = [f for f in fixture_ids if not (folder / "matches" / f"{f}.json").exists()]
    if still:
        print(f"  {season_label(slug, season)}: the API returned nothing for {len(still)} matches: {still[:10]}")
    print(f"  {season_label(slug, season)}: match details complete ({len(fixture_ids) - len(still)} matches)")
    (folder / "MATCHES_COMPLETE").write_text("")


def report(queue: list[tuple[str, int, int]], pro: bool) -> None:
    print("\nProgress:")
    by_slug: dict[str, list[int]] = {}
    for slug, _, season in queue:
        by_slug.setdefault(slug, []).append(season)
    marker = "PLAYERS_COMPLETE" if pro else "SQUADS_COMPLETE"
    for slug, seasons in by_slug.items():
        squads = matches = total = 0
        for season in seasons:
            folder = RAW / slug / str(season)
            squads += (folder / marker).exists()
            if (folder / "matches").exists():
                matches += len(list((folder / "matches").glob("*.json")))
            if (folder / "fixtures.json").exists():
                total += sum(m["fixture"]["status"]["short"] in FINISHED for m in load(folder / "fixtures.json")["response"])
        print(f"  {slug:17} squads {squads}/{len(seasons)} seasons   matches {matches}/{total or '?'}")
    clubs = len(list((RAW / "transfers").glob("team-*.json")))
    print(f"  transfers: {clubs} clubs")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="don't fetch, just report progress")
    parser.add_argument("--plan", choices=["free", "pro"], help="override the plan read from /status")
    parser.add_argument("--rate", type=int, help="requests a minute")
    parser.add_argument("--only", action="append", default=[], choices=list(COMPETITIONS), help="competition(s) to collect")
    parser.add_argument("--seasons", action="append", type=int, default=[], help="season start year(s) to collect")
    parser.add_argument("--squads-only", action="store_true", help="skip match details")
    args = parser.parse_args()
    if not KEY or KEY == "your_api_football_key_here":
        sys.exit("Put your API-Football key in ../.env first (API_FOOTBALL_KEY=...).")

    api = Api(args.dry_run, args.plan, args.rate)
    queue = build_queue(api.pro, args.only, args.seasons)
    started = time.monotonic()
    try:
        # Phase 1: squads for every competition-season (enough for the chain game).
        for slug, league_id, season in queue:
            if api.pro:
                collect_squads_pro(api, slug, league_id, season)
            else:
                collect_squads_free(api, slug, league_id, season)
        # Phase 2: transfers of every club seen, to fix wrong squad entries.
        collect_transfers(api, queue)
        # Phase 3: match details.
        if not args.squads_only:
            for slug, _, season in queue:
                collect_matches(api, slug, season)
        print("\nEverything in the queue is collected.")
    except QuotaReached:
        print("\nStopped: today's quota is spent (or --dry-run). Run again tomorrow to continue.")
    finally:
        minutes = (time.monotonic() - started) / 60
        print(f"Requests used this run: {api.used} in {minutes:.0f} min")
        report(queue, api.pro)


if __name__ == "__main__":
    main()
