"""Match data for the Complete the lineup and Match quiz games.

Reads the raw match details in data/raw/ (no API requests) and writes
site/data/matches.json:

    matches    notable matches: big league games between top clubs, the
               Champions League from the round of 16, the Europa League from
               the quarter-finals, and every European game of a Turkish club
               from the group stage on. Each has both starting XIs, every
               event (goals, cards, substitutions, VAR, missed penalties)
               and a few team stats.
    positions  each player's most common lineup position (G, D, M, F), used as
               a hint in the Career path game.

Run build.py first; only players and teams in game.json are kept.

    python build_matches.py
"""

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from build import COMPETITIONS, FINISHED, RAW, load

ROOT = Path(__file__).resolve().parent.parent
GAME = ROOT / "site" / "data" / "game.json"
OUT = ROOT / "site" / "data" / "matches.json"

LEAGUES = [s for s in COMPETITIONS if s not in ("champions-league", "europa-league")]
BIG_PER_LEAGUE = 6  # clubs per league whose meetings count as big games
CL_ROUNDS = ("Round of 16", "Quarter-finals", "Semi-finals", "Final")
EL_ROUNDS = ("Quarter-finals", "Semi-finals", "Final")
QUALIFYING = re.compile(r"Qualifying|Preliminary|Play-offs", re.I)


def big_clubs(game: dict) -> dict[str, set[int]]:
    """Per league, the clubs with the most European seasons (CL counts double)."""
    home: dict[int, Counter] = defaultdict(Counter)
    europe: Counter = Counter()
    for node in game["nodes"]:
        for comp in node["comps"]:
            if comp in LEAGUES:
                home[node["team"]][comp] += 1
        europe[node["team"]] += 2 * ("champions-league" in node["comps"]) + ("europa-league" in node["comps"])
    by_league: dict[str, list[int]] = defaultdict(list)
    for team, leagues in home.items():
        by_league[leagues.most_common(1)[0][0]].append(team)
    return {lg: set(sorted(teams, key=lambda t: -europe[t])[:BIG_PER_LEAGUE]) for lg, teams in by_league.items()}


def notable(slug: str, fixture: dict, big: dict, turkish: set[int]) -> bool:
    rnd = fixture["league"]["round"]
    home, away = fixture["teams"]["home"]["id"], fixture["teams"]["away"]["id"]
    if slug in LEAGUES:
        return home in big[slug] and away in big[slug]
    if QUALIFYING.search(rnd):
        return False
    if home in turkish or away in turkish:
        return True
    rounds = CL_ROUNDS if slug == "champions-league" else EL_ROUNDS
    return rnd in rounds


def lineup(side: dict, players: dict) -> list | None:
    """[[player id, shirt number, position, grid], ...] for the starting XI."""
    xi = side.get("startXI") or []
    if len(xi) != 11:
        return None
    out = []
    for slot in xi:
        p = slot["player"]
        if str(p["id"]) not in players:
            return None
        out.append([p["id"], p.get("number"), p.get("pos"), p.get("grid")])
    return out


# (type, detail) -> our kind. Penalty shootout kicks are left out; the score has the shootout result.
EVENT_KINDS = {
    ("Goal", "Normal Goal"): "goal",
    ("Goal", "Penalty"): "pen",
    ("Goal", "Own Goal"): "og",
    ("Goal", "Missed Penalty"): "misspen",
    ("Card", "Yellow Card"): "yellow",
    ("Card", "Red Card"): "red",
    # A second yellow comes as a plain "Red Card"; the site spots it from the earlier yellow.
    ("subst", None): "sub",
    ("Var", "Goal cancelled"): "var-nogoal",
    ("Var", "Goal confirmed"): "var-goal",
    ("Var", "Penalty confirmed"): "var-pen",
    ("Var", "Penalty awarded"): "var-pen",
    ("Var", "Penalty cancelled"): "var-nopen",
    ("Var", "Card upgrade"): "var-red",
    ("Var", "Red card cancelled"): "var-nored",
}
# Card comments from the API -> short keys the site translates.
CARD_REASONS = {
    "Foul": "foul", "Argument": "argument", "Time wasting": "time", "Handball": "handball",
    "Simulation": "simulation", "Violent conduct": "violent", "Persistent fouling": "persistent",
    "Professional foul last man": "lastman", "Off the ball foul": "offball",
    "Professional handball": "handball", "Dangerous play": "dangerous",
}


def person(ref: dict, players: dict):
    """A player as their id when the game knows them, else their name (or None)."""
    pid = ref.get("id")
    if pid is not None and str(pid) in players:
        return pid
    return ref.get("name")


def events(match: dict, home: int, players: dict) -> list:
    """Everything that happened, in order:
    [minute, extra, side (0 home, 1 away), player, kind, other player, note].

    player/other are ids or names (see person). other is the assist for goals and the
    player coming on for a substitution (player is the one going off). For own goals the
    side is the team the goal counts for, as the API gives it. note is a card reason.
    """
    out = []
    for e in match.get("events") or []:
        if e.get("comments") == "Penalty Shootout":
            continue
        detail = None if e["type"] == "subst" else e["detail"]
        kind = EVENT_KINDS.get((e["type"], detail))
        if not kind or e["time"]["elapsed"] is None:
            continue
        side = 0 if e["team"]["id"] == home else 1
        other = person(e.get("assist") or {}, players) if kind in ("goal", "sub") else None
        note = CARD_REASONS.get(e.get("comments")) if e["type"] == "Card" else None
        out.append([e["time"]["elapsed"], e["time"]["extra"], side, person(e["player"] or {}, players), kind, other, note])
    return out


def stats(match: dict, home: int) -> list | None:
    """Per side [possession %, shots, shots on target, corners], or None when missing."""
    by_team = {s["team"]["id"]: {x["type"]: x["value"] for x in s["statistics"]} for s in match.get("statistics") or []}
    if len(by_team) != 2 or home not in by_team:
        return None
    away = next(t for t in by_team if t != home)

    def row(st: dict):
        poss = st.get("Ball Possession")
        poss = int(str(poss).rstrip("%")) if poss else None
        return [poss, st.get("Total Shots"), st.get("Shots on Goal"), st.get("Corner Kicks")]

    rows = [row(by_team[home]), row(by_team[away])]
    return rows if any(v is not None for r in rows for v in r) else None


def main() -> None:
    game = load(GAME)
    players, teams = game["players"], game["teams"]
    big = big_clubs(game)
    turkish = {t for t in big.get("super-lig", set())} | {
        n["team"] for n in game["nodes"] if "super-lig" in n["comps"]}

    positions: dict[int, Counter] = defaultdict(Counter)
    matches = []
    for slug in COMPETITIONS:
        for folder in sorted((RAW / slug).glob("[0-9]*")):
            if not (folder / "fixtures.json").exists():
                continue
            season = int(folder.name)
            for fx in load(folder / "fixtures.json")["response"]:
                if fx["fixture"]["status"]["short"] not in FINISHED:
                    continue
                path = folder / "matches" / f"{fx['fixture']['id']}.json"
                if not path.exists():
                    continue
                match = load(path)["response"][0]
                for side in match.get("lineups") or []:
                    for slot in side.get("startXI") or []:
                        if slot["player"].get("pos"):
                            positions[slot["player"]["id"]][slot["player"]["pos"]] += 1
                if not notable(slug, fx, big, turkish):
                    continue
                sides = match.get("lineups") or []
                home_id = fx["teams"]["home"]["id"]
                if len(sides) != 2 or sides[0]["team"]["id"] != home_id:
                    sides = sorted(sides, key=lambda s: s["team"]["id"] != home_id)
                xis = [lineup(s, players) for s in sides] if len(sides) == 2 else [None]
                if None in xis or any(str(fx["teams"][k]["id"]) not in teams for k in ("home", "away")):
                    continue
                score = match["score"]
                matches.append({
                    "id": fx["fixture"]["id"],
                    "comp": slug,
                    "season": season,
                    "round": fx["league"]["round"],
                    "date": fx["fixture"]["date"][:10],
                    "venue": (fx["fixture"].get("venue") or {}).get("name"),
                    "teams": [fx["teams"]["home"]["id"], fx["teams"]["away"]["id"]],
                    "goals": [fx["goals"]["home"], fx["goals"]["away"]],
                    "pens": [score["penalty"]["home"], score["penalty"]["away"]] if score["penalty"]["home"] is not None else None,
                    "formations": [s.get("formation") for s in sides],
                    "coaches": [(s.get("coach") or {}).get("name") for s in sides],
                    "xi": xis,
                    "events": events(match, home_id, players),
                    "stats": stats(match, home_id),
                })
    pos = {pid: c.most_common(1)[0][0] for pid, c in positions.items() if str(pid) in players}
    OUT.write_text(json.dumps({"matches": matches, "positions": pos}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    by_comp = Counter(m["comp"] for m in matches)
    print(f"{len(matches)} notable matches, positions for {len(pos)} players, "
          f"{OUT.stat().st_size // 1024} KB -> {OUT.relative_to(ROOT)}")
    print(", ".join(f"{k} {v}" for k, v in by_comp.items()))
    for lg, clubs in big.items():
        print(f"  big in {lg}: {', '.join(teams[str(t)]['name'] for t in clubs if str(t) in teams)}")


if __name__ == "__main__":
    main()
