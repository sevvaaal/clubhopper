// Logic for the two match games: Complete the lineup and Match quiz.
// Uses data/matches.json from pipeline/build_matches.py.

// The starting XI in rows, goalkeeper first. Uses the lineup grid ("row:col")
// when the API has it, otherwise each player's position in that match or
// their usual position.
export function formationRows(xi, positions) {
  if (xi.every(([, , , grid]) => grid)) {
    const rows = new Map();
    for (const slot of xi) {
      const [r, c] = slot[3].split(":").map(Number);
      if (!rows.has(r)) rows.set(r, []);
      rows.get(r).push([c, slot]);
    }
    return [...rows.keys()].sort((a, b) => a - b)
      .map((r) => rows.get(r).sort((a, b) => a[0] - b[0]).map(([, slot]) => slot));
  }
  // One keeper: the one marked G in this match, else the first listed (the
  // API lists the keeper first). Anyone else usually in goal goes to defence.
  const keeper = xi.find((s) => s[2] === "G") || xi[0];
  const order = { G: 1, D: 1, M: 2, F: 3 };
  const rows = [[keeper], [], [], []];
  for (const slot of xi) if (slot !== keeper) rows[order[slot[2] || positions[slot[0]] || "M"]].push(slot);
  return rows.filter((r) => r.length);
}

// A match and one of its two sides for the lineup game.
export function pickLineup(matches, random) {
  const match = matches[Math.floor(random() * matches.length)];
  return { match, side: random() < 0.5 ? 0 : 1 };
}

// Quiz: matches with enough going on for the live feed to tell a story.
export const quizPool = (matches) => matches.filter((m) => m.events.length >= 6);

// Fisher-Yates, so the daily puzzle is the same in every browser.
export function shuffle(list, random) {
  const a = [...list];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

const pairKey = (m) => [...m.teams].sort().join("-");

// The answer plus three other matches, as alike as we can: same competition
// and season, sharing a club if possible. Never the same two clubs again.
export function quizOptions(pool, answer, random) {
  const used = new Set([pairKey(answer)]);
  const shuffled = shuffle(pool, random);
  const tiers = [
    (m) => m.comp === answer.comp && m.season === answer.season && m.teams.some((t) => answer.teams.includes(t)),
    (m) => m.comp === answer.comp && m.season === answer.season,
    (m) => m.comp === answer.comp,
    () => true,
  ];
  const options = [answer];
  for (const fits of tiers) {
    for (const m of shuffled) {
      if (options.length === 4) break;
      if (!used.has(pairKey(m)) && fits(m)) {
        used.add(pairKey(m));
        options.push(m);
      }
    }
  }
  return shuffle(options, random);
}

const SCORING = new Set(["goal", "pen", "og"]);

// The quiz's live feed: the match's events in order, with the score after each,
// plus kick-off, half-time, extra time and full-time lines, and after the
// final whistle the stats, the match details and the managers.
// Each item: { kind, minute (for the clock), label ("45+2'"), score, ...event }.
export function matchFeed(m) {
  const score = [0, 0];
  const booked = new Set();
  const feed = [{ kind: "kickoff", minute: 0, label: "1'", score: [0, 0] }];
  const events = m.events
    .map((e, i) => ({ e, i }))
    .sort((a, b) => a.e[0] - b.e[0] || (a.e[1] || 0) - (b.e[1] || 0) || a.i - b.i)
    .map(({ e }) => e);
  const extraTime = events.some(([min]) => min > 90);
  let half = false, fullRegulation = false;

  for (const [min, extra, side, who, kind, other, note] of events) {
    if (!half && min > 45) {
      feed.push({ kind: "half", minute: 45, label: "45'", score: [...score] });
      half = true;
    }
    if (extraTime && !fullRegulation && min > 90) {
      feed.push({ kind: "extra", minute: 90, label: "90'", score: [...score] });
      fullRegulation = true;
    }
    if (SCORING.has(kind)) score[side]++;
    // The API sends a second yellow as a plain red card after an earlier yellow.
    const second = kind === "red" && booked.has(who);
    if (kind === "yellow") booked.add(who);
    feed.push({
      kind, side, who, other, note, second,
      minute: min, label: `${min}${extra ? `+${extra}` : ""}'`, score: [...score],
    });
  }
  if (!half) feed.push({ kind: "half", minute: 45, label: "45'", score: [...score] });
  const end = extraTime ? 120 : 90;
  feed.push({ kind: "full", minute: end, label: `${end}'`, score: [...m.goals] });
  if (m.pens) feed.push({ kind: "pens", minute: end, label: `${end}'`, score: [...m.goals], pens: m.pens });
  if (m.stats) feed.push({ kind: "stats", minute: end, label: "", score: [...m.goals], stats: m.stats });
  feed.push({ kind: "info", minute: end, label: "", score: [...m.goals] });
  if (m.coaches.some(Boolean)) feed.push({ kind: "coaches", minute: end, label: "", score: [...m.goals] });
  return feed;
}

// Answering early pays: 5 points at kick-off, one less from the 30th and the
// 60th minute and once the match is over, and one less for every wrong pick.
export function quizPoints(minute, finished, wrong) {
  return Math.max(0, 5 - (minute >= 30) - (minute >= 60) - finished - wrong);
}
