"""Turn the raw API-Football responses in data/raw/ into the game data the site reads.

Makes no API requests, so it can be re-run as often as needed.

A team-season (e.g. "Galatasaray 2024/25") is a node of the chain graph. It
covers every competition we collect for that club that season: the league,
the Champions League and the Europa League. A player belongs to a
team-season if they played at least one minute for that club in any of them.
Two players are linked by every team-season they share.

Who played where comes from the best source we have for each
competition-season:

1. Match details (lineups with minutes): exact. Used when every finished
   match of that competition-season has been collected.
2. Season stats from the squad lists: the API copies some players' stats to
   clubs they only joined later, so these are checked against transfer dates
   and copies that can't be settled are left out.

    python build.py            # writes site/data/game.json

Run it again after images.py, so each team and player knows whether we have
its picture ("img"); the site shows initials for the ones we don't.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "site" / "data" / "game.json"
IMG = ROOT / "site" / "img"  # filled by images.py

# Same ids as collect.py.
COMPETITIONS = {
    "super-lig": (203, "Süper Lig"),
    "premier-league": (39, "Premier League"),
    "la-liga": (140, "La Liga"),
    "serie-a": (135, "Serie A"),
    "bundesliga": (78, "Bundesliga"),
    "ligue-1": (61, "Ligue 1"),
    "champions-league": (2, "Şampiyonlar Ligi"),
    "europa-league": (3, "Avrupa Ligi"),
}
FINISHED = ("FT", "AET", "PEN")


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def player_info(p: dict) -> dict:
    return {
        "name": p["name"],
        "first": p.get("firstname"),
        "last": p.get("lastname"),
        "nat": p.get("nationality"),
        "born": (p.get("birth") or {}).get("date"),
        "photo": p.get("photo"),
    }


# --- Transfers: fixing the squad lists' copied stats -------------------------

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


def drop_wrong_entries(members: dict, season: int, transfers: dict) -> dict[str, int]:
    """Remove players from squads they weren't part of, in one competition-season
    built from squad stats. members: (team, player) -> [apps, minutes].

    Two signs of a copy: the player only joined the club after that season, or
    the same minutes appear at two clubs. Copies the transfer dates can't settle
    are left out at every club involved rather than guessed.
    """
    counts = {"joined later": 0, "unresolved copies": 0}
    drop = set()
    groups: dict = {}
    for (team, pid), (_, minutes) in members.items():
        if joined_later(transfers.get((pid, team), []), season):
            drop.add((team, pid))
            counts["joined later"] += 1
        groups.setdefault((pid, minutes), []).append(team)

    start, end = f"{season}-07-01", f"{season + 1}-06-15"
    for (pid, _), group in groups.items():
        left = [t for t in group if (t, pid) not in drop]
        if len(left) < 2:
            continue
        # A move between two of these clubs during the season makes both real.
        confirmed = set()
        for team in left:
            for date, _, other in transfers.get((pid, team), []):
                if other in left and start <= date <= end:
                    confirmed |= {team, other}
        for team in left:
            if team not in confirmed:
                drop.add((team, pid))
                counts["unresolved copies"] += 1

    for key in drop:
        del members[key]
    return counts


# --- Reading one competition-season ------------------------------------------

def from_matches(folder: Path, players: dict) -> dict | None:
    """(team, player) -> [matches played, minutes], from match lineups.
    None unless every finished match has been collected."""
    fixtures = load(folder / "fixtures.json")["response"]
    finished = [m["fixture"]["id"] for m in fixtures if m["fixture"]["status"]["short"] in FINISHED]
    files = [folder / "matches" / f"{f}.json" for f in finished]
    if not finished or not all(f.exists() for f in files):
        return None
    members: dict = {}
    unusable = 0
    for f in files:
        played = match_minutes(load(f)["response"][0], players)
        if played is None:
            unusable += 1
            continue
        for key, minutes in played.items():
            entry = members.setdefault(key, [0, 0])
            entry[0] += 1
            entry[1] += minutes
    # A few matches without lineups are fine (e.g. Süper Lig 2022/23's games
    # awarded after the February 2023 earthquake were never played); many
    # mean the season's lineups are patchy and squad stats are the better source.
    if not members or unusable > len(files) * 0.10:
        return None
    return members


def match_minutes(match: dict, players: dict) -> dict | None:
    """(team, player) -> minutes for everyone who played in one match.

    Uses the per-player stats when the API has them (from about 2015 on).
    Older matches and many cup qualifiers only have lineups and substitution
    events; then starters and players who came on count, with minutes
    estimated from the substitution times. None if the match has neither.
    """
    if match.get("players"):
        out = {}
        for side in match["players"]:
            for row in side["players"]:
                minutes = row["statistics"][0]["games"]["minutes"] or 0
                if minutes > 0:
                    p = row["player"]
                    players.setdefault(p["id"], {"name": p["name"], "photo": p.get("photo")})
                    out[(side["team"]["id"], p["id"])] = minutes
        if out:
            return out

    lineups = match.get("lineups") or []
    if len(lineups) != 2 or not all(l.get("startXI") for l in lineups):
        return None
    out = {}
    starters = {}
    for side in lineups:
        team = side["team"]["id"]
        for slot in side["startXI"] + (side.get("substitutes") or []):
            p = slot["player"]
            if p.get("id"):
                players.setdefault(p["id"], {"name": p["name"], "photo": None})
        for slot in side["startXI"]:
            if slot["player"].get("id"):
                starters[(team, slot["player"]["id"])] = True
                out[(team, slot["player"]["id"])] = 90
    for event in match.get("events") or []:
        if event.get("type") != "subst":
            continue
        team = event["team"]["id"]
        minute = min(max(event["time"]["elapsed"] or 0, 1), 90)
        a, b = (event.get("player") or {}).get("id"), (event.get("assist") or {}).get("id")
        # The API isn't consistent about which of the two came on: the one
        # already on the pitch is the one going off.
        on_pitch = lambda pid: pid is not None and (team, pid) in out
        going_off, coming_on = (a, b) if on_pitch(a) and not on_pitch(b) else (b, a)
        if going_off is not None and (team, going_off) in out:
            out[(team, going_off)] = max(out[(team, going_off)] - (90 - minute), 1)
        if coming_on is not None:
            out[(team, coming_on)] = max(90 - minute, 1)
    return out


def from_squads(folder: Path, league_id: int, players: dict) -> tuple[dict, list[int]]:
    """(team, player) -> [appearances, minutes] from the squad lists' season
    stats (league-wide pages on Pro, per-team pages on the free plan).
    Also returns the teams whose free-plan list was cut at 3 pages."""
    members: dict = {}
    capped = []
    pages = sorted((folder / "players").glob("page-*.json"))
    team_pages: dict[int, list[Path]] = {}
    for f in sorted((folder / "team-players").glob("*-page-*.json")):
        team_pages.setdefault(int(f.stem.split("-page-")[0]), []).append(f)
    if not pages:
        for team, files in team_pages.items():
            pages += files
            if len(files) < load(files[0])["paging"]["total"]:
                capped.append(team)
    for f in pages:
        for row in load(f)["response"]:
            p = row["player"]
            for s in row["statistics"]:
                if s["league"]["id"] != league_id or not s["team"]["id"]:
                    continue
                apps = s["games"]["appearences"] or 0
                if apps < 1:
                    continue
                players[p["id"]] = player_info(p)
                entry = members.setdefault((s["team"]["id"], p["id"]), [0, 0])
                entry[0] += apps
                entry[1] += s["games"]["minutes"] or 0
    return members, capped


def main() -> None:
    transfers = load_transfers()
    teams: dict[int, dict] = {}
    players: dict[int, dict] = {}
    by_node: dict[tuple[int, int], dict] = {}  # (season, team) -> {player: [apps, minutes]}
    comps_of: dict[tuple[int, int], set] = {}
    seasons: list[dict] = []
    dropped = {"joined later": 0, "unresolved copies": 0}

    for slug, (league_id, _) in COMPETITIONS.items():
        comp_dir = RAW / slug
        if not comp_dir.is_dir():
            continue
        for folder in sorted(comp_dir.iterdir(), reverse=True):
            if not (folder / "teams.json").exists() or not (folder / "fixtures.json").exists():
                continue
            season = int(folder.name)
            listed = load(folder / "teams.json")["response"]
            for entry in listed:
                t = entry["team"]
                teams.setdefault(t["id"], {"name": t["name"], "code": t.get("code"), "logo": t["logo"]})

            squad_members, capped = from_squads(folder, league_id, players)
            members = from_matches(folder, players)
            source = "matches"
            if members is None:
                if not squad_members:
                    continue
                members, source = squad_members, "squads"
                for k, v in drop_wrong_entries(members, season, transfers).items():
                    dropped[k] += v

            for (team, pid), (apps, minutes) in members.items():
                node = by_node.setdefault((season, team), {})
                total = node.setdefault(pid, [0, 0])
                total[0] += apps
                total[1] += minutes
                comps_of.setdefault((season, team), set()).add(slug)
            seasons.append({
                "league": slug,
                "season": season,
                "teams": len({team for team, _ in members}),
                "of": len(listed),
                "source": source,
                "capped": [teams[t]["name"] for t in capped if t in teams] if source == "squads" else [],
            })

    nodes = []
    for (season, team), members in sorted(by_node.items(), key=lambda x: (-x[0][0], x[0][1])):
        nodes.append({
            "id": f"{season}-{team}",
            "team": team,
            "season": season,
            "comps": sorted(comps_of[(season, team)], key=list(COMPETITIONS).index),
            "players": sorted(([pid, a, m] for pid, (a, m) in members.items()), key=lambda x: -x[2]),
        })

    used = {m[0] for n in nodes for m in n["players"]}
    players = {pid: p for pid, p in players.items() if pid in used}
    for pid, p in players.items():
        p["img"] = (IMG / "players" / f"{pid}.webp").exists()
    team_ids = {n["team"] for n in nodes}
    teams = {tid: t for tid, t in teams.items() if tid in team_ids}
    for tid, t in teams.items():
        t["img"] = (IMG / "teams" / f"{tid}.webp").exists()

    data = {
        "leagues": {slug: name for slug, (_, name) in COMPETITIONS.items()},
        "seasons": seasons,
        "teams": teams,
        "players": players,
        "nodes": nodes,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    seen: dict[int, int] = {}
    for n in nodes:
        for m in n["players"]:
            seen[m[0]] = seen.get(m[0], 0) + 1
    links = sum(1 for c in seen.values() if c > 1)
    print(f"{len(nodes)} team-seasons, {len(players)} players ({links} in more than one), "
          f"{OUT.stat().st_size // 1024} KB -> {OUT.relative_to(ROOT)}")
    from_matches_count = sum(s["source"] == "matches" for s in seasons)
    print(f"{len(seasons)} competition-seasons: {from_matches_count} from match lineups, "
          f"{len(seasons) - from_matches_count} from squad stats")
    print(f"Wrong squad-stat entries removed: {dropped}")
    for s in seasons:
        if s["source"] == "squads":
            partial = "" if s["teams"] == s["of"] else f"  PARTIAL: {s['teams']} of {s['of']} teams"
            capped = f"  (squads cut at 3 pages: {', '.join(s['capped'])})" if s["capped"] else ""
            print(f"  {s['league']} {s['season']} from squad stats{partial}{capped}")


if __name__ == "__main__":
    main()
