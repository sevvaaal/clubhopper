import { buildGraph, teamSeasons, squad, makePuzzle, rng, pathLength } from "./chain.js";

const TEXT = {
  tr: {
    daily: "Günün zinciri", free: "Serbest", lang: "EN",
    goal: (a, b) => `<b>${a}</b> oyuncusundan <b>${b}</b> oyuncusuna ulaş.`,
    best: (n) => `En kısa zincir ${n} adım.`,
    pickTeam: (p) => `${p} ile hangi takıma gitmek istersin?`,
    pickMate: (team) => `${team} kadrosundan bir takım arkadaşı seç:`,
    back: "← Takımlara dön", undo: "Geri al", giveUp: "Pes et", again: "Yeni bulmaca",
    won: (n, best) => `Tebrikler! ${n} adımda ulaştın (en kısa: ${best}).`,
    solution: "En kısa zincir:",
    about: (seasons) => `Prototip. Veri: API-Football. Şu an açık: ${seasons}. Bir oyuncu, ligde ya da Avrupa kupalarında en az 1 dakika oynadığı takım-sezona sayılır. Kulüp logoları ve oyuncu fotoğrafları sahiplerine aittir; yalnızca tanıtım amaçlı, küçük boyutta gösterilir. Kaldırılmasını istediğiniz bir görsel olursa bize yazın.`,
  },
  en: {
    daily: "Daily chain", free: "Free play", lang: "TR",
    goal: (a, b) => `Get from <b>${a}</b> to <b>${b}</b>.`,
    best: (n) => `The shortest chain has ${n} links.`,
    pickTeam: (p) => `Which of ${p}'s teams do you want to go to?`,
    pickMate: (team) => `Pick a teammate from ${team}:`,
    back: "← Back to teams", undo: "Undo", giveUp: "Give up", again: "New puzzle",
    won: (n, best) => `Well done! You made it in ${n} links (shortest: ${best}).`,
    solution: "Shortest chain:",
    about: (seasons) => `Prototype. Data: API-Football. Open now: ${seasons}. A player counts for a team-season if they played at least 1 minute for that club in the league or a European cup. Club crests and player photos belong to their owners and are shown small, for identification only. Contact us to have any image removed.`,
  },
};

// chain: [player, teamSeason, player, ...]; team: the team-season picked
// from the current player, whose squad is being shown.
const state = { lang: "tr", mode: "daily", puzzle: null, chain: [], team: null, gaveUp: false };
let graph;

const t = () => TEXT[state.lang];
const el = (id) => document.getElementById(id);
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);

function nodeLabel(id) {
  const n = graph.nodes.get(id);
  return `${graph.data.teams[n.team].name} ${n.season}/${String(n.season + 1).slice(2)}`;
}
const playerName = (pid) => graph.data.players[pid].name;

// Our own small copies from images.py; initials when there's no picture.
function initials(name) {
  const words = name.replace(/\./g, " ").split(/\s+/).filter(Boolean);
  const pick = words.length > 1 ? [words[0], words[words.length - 1]] : words;
  return pick.map((w) => w[0]).join("").toLocaleUpperCase("tr");
}
function avatar(kind, id, name) {
  const item = kind === "players" ? graph.data.players[id] : graph.data.teams[id];
  if (item?.img) return `<img class="pic ${kind}" src="img/${kind}/${id}.webp" alt="" loading="lazy" width="32" height="32">`;
  const hue = (Number(id) * 47) % 360;
  return `<span class="pic initials ${kind}" style="--hue:${hue}" aria-hidden="true">${esc(initials(name))}</span>`;
}
const playerPic = (pid) => avatar("players", pid, playerName(pid));
const teamPic = (nodeId) => {
  const team = graph.nodes.get(nodeId).team;
  return avatar("teams", team, graph.data.teams[team].name);
};
// "Süper Lig 2022/23–2024/25, Premier League 2023/24 (partial)–2024/25", from the data.
function openSeasons() {
  const partial = state.lang === "tr" ? "eksik" : "partial";
  const byLeague = new Map();
  for (const s of graph.data.seasons) {
    if (!byLeague.has(s.league)) byLeague.set(s.league, []);
    byLeague.get(s.league).push(s);
  }
  return [...byLeague].map(([league, list]) => {
    const label = (s) => `${s.season}/${String(s.season + 1).slice(2)}${s.teams < s.of ? ` (${partial})` : ""}`;
    list.sort((a, b) => a.season - b.season);
    const range = list.length > 1 ? `${label(list[0])}–${label(list[list.length - 1])}` : label(list[0]);
    return `${graph.data.leagues[league]} ${range}`;
  }).join(", ");
}
const here = () => state.chain[state.chain.length - 1];

function newPuzzle() {
  const seed = state.mode === "daily" ? new Date().toISOString().slice(0, 10) : Math.random();
  state.puzzle = makePuzzle(graph, rng(seed));
  state.chain = [state.puzzle.start];
  state.team = null;
  state.gaveUp = false;
  render();
}

function chainHtml(path, markLast = false) {
  return `<ol class="chain">${path
    .map((x, i) => {
      if (i % 2) return `<li class="via">↳ ${teamPic(x)} ${esc(nodeLabel(x))}</li>`;
      const cls = markLast && i === path.length - 1 ? ' class="current"' : "";
      return `<li${cls}>${playerPic(x)} ${esc(playerName(x))}</li>`;
    })
    .join("")}</ol>`;
}

const buttons = (items, attr, label, pic) =>
  `<div class="choices">${items.map((x) => `<button data-${attr}="${x}">${pic(x)} ${esc(label(x))}</button>`).join("")}</div>`;

function render() {
  const T = t();
  el("mode-daily").textContent = T.daily;
  el("mode-free").textContent = T.free;
  el("mode-daily").disabled = state.mode === "daily";
  el("mode-free").disabled = state.mode === "free";
  el("lang").textContent = T.lang;
  el("about").textContent = T.about(openSeasons());
  document.documentElement.lang = state.lang;

  const { start, target, solution } = state.puzzle;
  const best = pathLength(solution);
  const won = here() === target;
  const done = won || state.gaveUp;

  const who = (pid) => `${playerPic(pid)} ${esc(playerName(pid))}`;
  let html = `<div class="goal">${T.goal(who(start), who(target))}<br><small>${T.best(best)}</small></div>`;
  html += chainHtml(state.chain, true);

  if (won) {
    html += `<p class="won">${T.won(pathLength(state.chain), best)}</p><p>${T.solution}</p>${chainHtml(solution)}`;
  } else if (state.gaveUp) {
    html += `<p>${T.solution}</p>${chainHtml(solution)}`;
  } else if (state.team) {
    html += `<p>${T.pickMate(esc(nodeLabel(state.team)))}</p>`;
    html += buttons(squad(graph, state.team, here()), "player", playerName, playerPic);
    html += `<p><button id="back">${T.back}</button></p>`;
  } else {
    html += `<p>${T.pickTeam(esc(playerName(here())))}</p>`;
    html += buttons(teamSeasons(graph, here()), "team", nodeLabel, teamPic);
  }

  html += `<p>`;
  if (!done && state.chain.length > 1) html += `<button id="undo">${T.undo}</button> `;
  if (!done) html += `<button id="give-up">${T.giveUp}</button> `;
  if (done && state.mode === "free") html += `<button id="again">${T.again}</button>`;
  html += `</p>`;

  el("app").innerHTML = html;
}

el("app").addEventListener("click", (e) => {
  const b = e.target.closest("button");
  if (!b) return;
  if (b.dataset.team) state.team = b.dataset.team;
  else if (b.dataset.player) {
    state.chain.push(state.team, Number(b.dataset.player));
    state.team = null;
  } else if (b.id === "back") state.team = null;
  else if (b.id === "undo") {
    state.chain.splice(-2);
    state.team = null;
  } else if (b.id === "give-up") state.gaveUp = true;
  else if (b.id === "again") return newPuzzle();
  render();
});
el("mode-daily").onclick = () => { state.mode = "daily"; newPuzzle(); };
el("mode-free").onclick = () => { state.mode = "free"; newPuzzle(); };
el("lang").onclick = () => { state.lang = state.lang === "tr" ? "en" : "tr"; render(); };

graph = buildGraph(await (await fetch("data/game.json")).json());
newPuzzle();
