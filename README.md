# Clubhopper

A football games site in the spirit of [Starlinked](https://github.com/sevvaaal/starlinked): hop from club to club through shared players.

Planned games:

- **Chain:** link a start and a target through club squads, where each club node is a club in one season (e.g. "Barcelona 2010/11"), the way Starlinked links movies through their cast.
- **Complete the lineup:** fill in the missing players of a famous match's starting XI.
- **Match quiz:** questions drawn from real match events (who was sent off, who scored the winner...).
- **Career path:** guess the player from the clubs they played for, in order.

Scope for now: the big five leagues (Premier League, La Liga, Serie A, Bundesliga, Ligue 1), no national teams. Seasons open one by one as their data is collected; the rest show as "coming soon".

## Data pipeline

Data is collected ahead of time into our own files instead of calling APIs while people play, so free API limits never slow the games down.

```bash
cd pipeline
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp ../.env.example ../.env   # then put your API-Football key in .env
python check_api_football.py # which seasons the free plan can read, and today's quota
python check_wikidata.py     # how complete Wikidata's club histories are
```
