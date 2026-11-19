"""How complete are Wikidata's club histories for footballers?

For a handful of big clubs, counts the people recorded as members of the club
(property P54, "member of sports team") and how many of those spells have
start/end dates (qualifiers P580/P582). Dates matter: two players are teammates
only if their spells at a club overlap. Also counts the squad Wikidata implies
for one sample season.

Everything is one query (all clubs at once), because the public query service
rate-limits hard at busy times. No API key needed.

    python check_wikidata.py
"""

import time

import httpx

ENDPOINT = "https://query.wikidata.org/sparql"
# Wikimedia asks for a descriptive User-Agent on automated requests.
HEADERS = {"User-Agent": "ClubhopperDataCheck/0.1 (football game data check)", "Accept": "application/sparql-results+json"}

CLUBS = {
    "Q9617": "Arsenal",
    "Q18656": "Manchester United",
    "Q1130849": "Liverpool",
    "Q9616": "Chelsea",
    "Q7156": "Barcelona",
    "Q8682": "Real Madrid",
    "Q1422": "Juventus",
    "Q15789": "Bayern Munich",
    "Q483020": "Paris Saint-Germain",
    "Q48791": "Galatasaray",
    "Q44620": "Fenerbahçe",
    "Q47870": "Beşiktaş",
}
SAMPLE_SEASON = (2015, 2016)  # a season runs roughly August to May

QUERY = """
SELECT ?club (COUNT(?spell) AS ?spells) (COUNT(?start) AS ?withStart) (COUNT(?end) AS ?withEnd)
       (COUNT(DISTINCT ?seasonPlayer) AS ?seasonSquad)
WHERE {
  VALUES ?club { %(clubs)s }
  ?player p:P54 ?spell .
  ?spell ps:P54 ?club .
  OPTIONAL { ?spell pq:P580 ?start }
  OPTIONAL { ?spell pq:P582 ?end }
  # In the sample season's squad: joined by its first year, not gone before its second.
  BIND(IF(BOUND(?start) && YEAR(?start) <= %(first)d && (!BOUND(?end) || YEAR(?end) >= %(second)d),
          ?player, ?unbound) AS ?seasonPlayer)
}
GROUP BY ?club
"""


def run(query: str) -> list[dict]:
    for attempt in range(6):
        response = httpx.get(ENDPOINT, params={"query": query}, headers=HEADERS, timeout=120)
        if response.status_code == 429:
            wait = max(int(response.headers.get("Retry-After", 62)), 62)
            print(f"  rate-limited, waiting {wait}s…", flush=True)
            time.sleep(wait)
            continue
        response.raise_for_status()
        return response.json()["results"]["bindings"]
    raise RuntimeError("Wikidata kept rate-limiting; try again later.")


rows = run(
    QUERY
    % {
        "clubs": " ".join(f"wd:{qid}" for qid in CLUBS),
        "first": SAMPLE_SEASON[0],
        "second": SAMPLE_SEASON[1],
    }
)
print(f"{'Club':22} {'spells':>7} {'start date':>11} {'end date':>9}   squad {SAMPLE_SEASON[0]}/{SAMPLE_SEASON[1] % 100:02d}")
for row in sorted(rows, key=lambda r: list(CLUBS).index(r["club"]["value"].rsplit("/", 1)[-1])):
    qid = row["club"]["value"].rsplit("/", 1)[-1]
    spells = int(row["spells"]["value"]) or 1
    print(
        f"{CLUBS[qid]:22} {int(row['spells']['value']):>7} {int(row['withStart']['value']) / spells:>10.0%}"
        f" {int(row['withEnd']['value']) / spells:>9.0%}   {int(row['seasonSquad']['value']):>4} players"
    )

print("\nA real first-team squad is about 25-35 players. Much more means youth/loan spells are mixed in;")
print("much less means missing dates. Both can be fixed by cross-checking with API-Football squads.")
