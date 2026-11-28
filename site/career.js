// Career path game logic: guess the player from the clubs they played for.
// Only the competitions we cover are known, so a career can have gaps.

// [{team, from, to, apps, minutes}], oldest first. Consecutive seasons at the
// same club are one spell.
export function career(graph, pid) {
  const rows = (graph.playerNodes.get(pid) || [])
    .map((id) => {
      const n = graph.nodes.get(id);
      const [, apps, minutes] = n.players.find(([p]) => p === pid);
      return { team: n.team, season: n.season, apps, minutes };
    })
    .sort((a, b) => a.season - b.season || a.minutes - b.minutes);
  const spells = [];
  for (const r of rows) {
    const last = spells.findLast((s) => s.team === r.team);
    if (last && last === spells[spells.length - 1] && r.season - last.to <= 1) {
      last.to = r.season;
      last.apps += r.apps;
      last.minutes += r.minutes;
    } else spells.push({ team: r.team, from: r.season, to: r.season, apps: r.apps, minutes: r.minutes });
  }
  return spells;
}

// Well-known players who moved around: at least `clubs` different clubs.
export function careerPool(graph, { clubs = 3, size = 1500 } = {}) {
  const out = [];
  for (const pid of graph.playerNodes.keys()) {
    const teams = new Set(graph.playerNodes.get(pid).map((id) => graph.nodes.get(id).team));
    if (teams.size >= clubs) out.push(pid);
  }
  out.sort((a, b) => graph.minutes.get(b) - graph.minutes.get(a));
  return out.slice(0, size);
}

export const pickPlayer = (pool, random) => pool[Math.floor(random() * pool.length)];

export const MAX_GUESSES = 6;
// Revealed one by one after each wrong guess.
export const HINTS = ["position", "nat", "born", "initials", "photo"];
