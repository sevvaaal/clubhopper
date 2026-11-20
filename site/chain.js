// Chain game logic, independent of the page so it can be tested with node.
//
// Players are the stops of the chain; two players are linked by every
// team-season they both played for. A move is: from the current player, pick
// one of their team-seasons, then pick a teammate from that squad.
// A path looks like [player, teamSeason, player, teamSeason, ..., player].

export function buildGraph(data) {
  const nodes = new Map(); // team-season id -> node
  const playerNodes = new Map(); // player id -> [team-season id]
  const minutes = new Map(); // player id -> league minutes over all seasons
  for (const n of data.nodes) {
    nodes.set(n.id, n);
    for (const [id, , mins] of n.players) {
      if (!playerNodes.has(id)) playerNodes.set(id, []);
      playerNodes.get(id).push(n.id);
      minutes.set(id, (minutes.get(id) || 0) + mins);
    }
  }
  // Newest season first in every player's list.
  for (const list of playerNodes.values()) list.sort((a, b) => nodes.get(b).season - nodes.get(a).season);
  return { data, nodes, playerNodes, minutes };
}

// The team-seasons a player can be followed through.
export const teamSeasons = (graph, playerId) => graph.playerNodes.get(playerId) || [];

// The squad of a team-season, most minutes first, without `except`.
export function squad(graph, nodeId, except) {
  return graph.nodes.get(nodeId).players.map(([id]) => id).filter((id) => id !== except);
}

// Shortest path between two players, or null.
export function shortestPath(graph, a, b) {
  if (a === b) return [a];
  const prev = new Map([[a, null]]);
  let frontier = [a];
  while (frontier.length) {
    const next = [];
    for (const pid of frontier) {
      for (const nodeId of teamSeasons(graph, pid)) {
        for (const [to] of graph.nodes.get(nodeId).players) {
          if (prev.has(to)) continue;
          prev.set(to, [pid, nodeId]);
          if (to === b) return unwind(prev, b);
          next.push(to);
        }
      }
    }
    frontier = next;
  }
  return null;
}

function unwind(prev, b) {
  const path = [b];
  let cur = b;
  while (prev.get(cur)) {
    const [from, nodeId] = prev.get(cur);
    path.unshift(from, nodeId);
    cur = from;
  }
  return path;
}

// Links in a path ("Icardi → Galatasaray 23/24 → Muslera" is 1).
export const pathLength = (path) => (path.length - 1) / 2;

// Deterministic PRNG so the daily puzzle is the same for everyone.
export function rng(seed) {
  let h = 2166136261;
  for (const c of String(seed)) h = Math.imul(h ^ c.charCodeAt(0), 16777619);
  return () => {
    h = Math.imul(h ^ (h >>> 15), 2246822507);
    h = Math.imul(h ^ (h >>> 13), 3266489909);
    h ^= h >>> 16;
    return (h >>> 0) / 4294967296;
  };
}

// Start and target are drawn from the most-played players, so both are names
// people know. Returns { start, target, solution } with at least minLinks
// links, or the longest pair found.
export function makePuzzle(graph, random, { minLinks = 3, pool = 250 } = {}) {
  const known = [...graph.minutes.entries()]
    .sort((x, y) => y[1] - x[1] || x[0] - y[0])
    .slice(0, pool)
    .map(([id]) => id);
  let best = null;
  for (let tries = 0; tries < 400; tries++) {
    const a = known[Math.floor(random() * known.length)];
    const b = known[Math.floor(random() * known.length)];
    if (a === b) continue;
    const solution = shortestPath(graph, a, b);
    if (!solution) continue;
    const candidate = { start: a, target: b, solution };
    if (pathLength(solution) >= minLinks) return candidate;
    if (!best || pathLength(solution) > pathLength(best.solution)) best = candidate;
  }
  return best;
}
