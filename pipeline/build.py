"""Turn the raw API-Football responses in data/raw/ into the game data the site reads.

Makes no API requests, so it can be re-run as often as needed.

A team-season (e.g. "Galatasaray 2024/25") is a node of the chain graph. A
player belongs to a team-season only if they played at least one league match
for that team that season. Two team-seasons are linked when a player belongs
to both.

    python build.py            # writes site/data/game.json

Run it again after images.py, so each team and player knows whether we have
its picture ("img"); the site shows initials for the ones we don't.

Only the league-seasons whose squads have been collected are included. Seasons
where some teams are still missing are included with the teams we have, and
the report says which ones are partial.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "site" / "data" / "game.json"
IMG = ROOT / "site" / "img"  # filled by images.py

# Same ids as collect.py.
LEAGUES = {
    "super-lig": (203, "Süper Lig"),
    "premier-league": (39, "Premier League"),
    "la-liga": (140, "La Liga"),
    "serie-a": (135, "Serie A"),
    "bundesliga": (78, "Bundesliga"),
    "ligue-1": (61, "Ligue 1"),
}
MIN_APPEARANCES = 1


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def team_pages(folder: Path) -> dict[int, list[Path]]:
    pages: dict[int, list[Path]] = {}
    for f in sorted((folder / "team-players").glob("*-page-*.json")):
        team_id = int(f.stem.split("-page-")[0])
        pages.setdefault(team_id, []).append(f)
    return pages


def load_transfers() -> dict[tuple[int, int], list[tuple[str, str, int | None]]]:
    """(player, team) -> that player's moves at that team: (date, "in"/"out", other team)."""
    moves: dict = {}
    for f in (RAW / "transfers").glob("team-*.json"):
        team_id = int(f.stem.removeprefix("team-"))
        for row in load(f)["response"]:
            for t in row["transfers"]:
                into, out = t["teams"]["in"]["id"], t["teams"]["out"]["id"]
                if not t.get("date") or into == out or team_id not in (into, out):
                    continue
                kind, other = ("in", out) if into == team_id else ("out", into)
                moves.setdefault((row["player"]["id"], team_id), []).append((t["date"], kind, other))
    return {key: sorted(set(m), key=lambda x: x[0]) for key, m in moves.items()}


def joined_later(moves: list, season: int) -> bool:
    """The first thing we know about the player at this team is arriving after the season."""
    return bool(moves) and moves[0][1] == "in" and moves[0][0] > f"{season + 1}-06-15"


def drop_wrong_entries(nodes: list[dict]) -> dict[str, int]:
    """Remove players from squads they weren't part of.

    The API copies some players' season stats to another of their clubs. Two
    signs: the player only joined the club after that season, or the same
    minutes appear at two clubs in one league-season. Copies the transfer dates
    can't settle are hidden at every club involved rather than guessed.
    """
    transfers = load_transfers()
    counts = {"joined later": 0, "unresolved copies": 0}
    drop: set[tuple[str, int]] = set()
    groups: dict = {}
    for n in nodes:
        for pid, _, minutes in n["players"]:
            if joined_later(transfers.get((pid, n["team"]), []), n["season"]):
                drop.add((n["id"], pid))
                counts["joined later"] += 1
            groups.setdefault((pid, n["league"], n["season"], minutes), []).append(n)

    for (pid, _, season, _), group in groups.items():
        left = [n for n in group if (n["id"], pid) not in drop]
        if len(left) < 2:
            continue
        # A move between two of these clubs during the season makes both real.
        start, end = f"{season}-07-01", f"{season + 1}-06-15"
        ids = {n["team"] for n in left}
        confirmed = set()
        for n in left:
            for date, _, other in transfers.get((pid, n["team"]), []):
                if other in ids and start <= date <= end:
                    confirmed |= {n["team"], other}
        for n in left:
            if n["team"] not in confirmed:
                drop.add((n["id"], pid))
                counts["unresolved copies"] += 1

    for n in nodes:
        n["players"] = [m for m in n["players"] if (n["id"], m[0]) not in drop]
    return counts


def main() -> None:
    teams: dict[int, dict] = {}
    players: dict[int, dict] = {}
    nodes: list[dict] = []
    seasons: list[dict] = []

    for slug, (league_id, league_name) in LEAGUES.items():
        league_dir = RAW / slug
        if not league_dir.is_dir():
            continue
        for season_dir in sorted(league_dir.iterdir(), reverse=True):
            if not (season_dir / "teams.json").exists():
                continue
            season = int(season_dir.name)
            league_teams = load(season_dir / "teams.json")["response"]
            pages = team_pages(season_dir)
            built = 0
            capped = []
            for entry in league_teams:
                team = entry["team"]
                team_pages_files = pages.get(team["id"])
                if not team_pages_files:
                    continue
                teams[team["id"]] = {
                    "name": team["name"],
                    "code": team.get("code"),
                    "logo": team["logo"],
                    "img": (IMG / "teams" / f"{team['id']}.webp").exists(),
                }
                members = {}
                total_pages = 1
                for f in team_pages_files:
                    data = load(f)
                    total_pages = data["paging"]["total"]
                    for row in data["response"]:
                        p = row["player"]
                        stats = [
                            s for s in row["statistics"]
                            if s["league"]["id"] == league_id and s["team"]["id"] == team["id"]
                        ]
                        apps = sum(s["games"]["appearences"] or 0 for s in stats)
                        minutes = sum(s["games"]["minutes"] or 0 for s in stats)
                        if apps < MIN_APPEARANCES:
                            continue
                        players.setdefault(p["id"], {
                            "name": p["name"],
                            "first": p.get("firstname"),
                            "last": p.get("lastname"),
                            "nat": p.get("nationality"),
                            "born": (p.get("birth") or {}).get("date"),
                            "photo": p.get("photo"),
                            "img": (IMG / "players" / f"{p['id']}.webp").exists(),
                        })
                        members[p["id"]] = [p["id"], apps, minutes]
                if len(team_pages_files) < total_pages:
                    capped.append(team["name"])
                nodes.append({
                    "id": f"{slug}-{season}-{team['id']}",
                    "team": team["id"],
                    "league": slug,
                    "season": season,
                    "players": sorted(members.values(), key=lambda m: -m[2]),
                })
                built += 1
            if not built:
                continue
            seasons.append({
                "league": slug,
                "season": season,
                "teams": built,
                "of": len(league_teams),
                "capped": capped,
            })

    dropped = drop_wrong_entries(nodes)
    used = {m[0] for n in nodes for m in n["players"]}
    players = {pid: p for pid, p in players.items() if pid in used}

    data = {
        "leagues": {slug: name for slug, (_, name) in LEAGUES.items()},
        "seasons": seasons,
        "teams": teams,
        "players": players,
        "nodes": nodes,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    links = sum(1 for p in players if sum(1 for n in nodes for m in n["players"] if m[0] == p) > 1)
    print(f"{len(nodes)} team-seasons, {len(players)} players ({links} in more than one), "
          f"{OUT.stat().st_size // 1024} KB -> {OUT.relative_to(ROOT)}")
    have = sum((RAW / "transfers" / f"team-{t}.json").exists() for t in teams)
    print(f"Wrong entries removed: {dropped} (transfers known for {have} of {len(teams)} teams)")
    for s in seasons:
        partial = "" if s["teams"] == s["of"] else f"  PARTIAL: {s['teams']} of {s['of']} teams"
        capped = f"  (squads cut at 3 pages: {', '.join(s['capped'])})" if s["capped"] else ""
        print(f"  {s['league']} {s['season']}: {s['teams']} teams{partial}{capped}")


if __name__ == "__main__":
    main()
