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
    for s in seasons:
        partial = "" if s["teams"] == s["of"] else f"  PARTIAL: {s['teams']} of {s['of']} teams"
        capped = f"  (squads cut at 3 pages: {', '.join(s['capped'])})" if s["capped"] else ""
        print(f"  {s['league']} {s['season']}: {s['teams']} teams{partial}{capped}")


if __name__ == "__main__":
    main()
