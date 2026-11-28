import { buildGraph, teamSeasons, squad, makePuzzle, rng, pathLength } from "./chain.js";
import { puzzleDate } from "./common.js";
import { initLayout } from "./layout.js";
import { getDaily, recordDaily, resultCard, wireResultCard } from "./daily.js";

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
    about: "Bir oyuncu, ligde ya da Avrupa kupalarında en az 1 dakika oynadığı takım-sezona sayılır.",
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
    about: "A player counts for a team-season if they played at least 1 minute for that club in the league or a European cup.",
  },
};

// chain: [player, teamSeason, player, ...]; team: the team-season picked
// from the current player, whose squad is being shown.
const savedLang = (() => { try { return localStorage.getItem("lang"); } catch { return null; } })();
// chain.html?mode=free opens free play (the menu links there).
const startMode = new URLSearchParams(location.search).get("mode") === "free" ? "free" : "daily";
const state = { lang: savedLang || "tr", mode: startMode, puzzle: null, chain: [], team: null, gaveUp: false };
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
const here = () => state.chain[state.chain.length - 1];

function newPuzzle() {
  const seed = state.mode === "daily" ? puzzleDate() : Math.random();
  state.already = state.mode === "daily" && !!getDaily("chain");
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
  el("about").textContent = T.about;
  if (state.mode === "daily" && state.already) {
    el("app").innerHTML = resultCard("chain", state.lang, { already: true });
    el("app").removeAttribute("aria-busy");
    return wireResultCard(el("app"), "chain", state.lang);
  }

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
  const finishedDaily = done && state.mode === "daily";
  if (finishedDaily) {
    recordDaily("chain", { won, links: pathLength(state.chain), best });
    layout.refresh();
    html += resultCard("chain", state.lang);
  }

  el("app").innerHTML = html;
  el("app").removeAttribute("aria-busy");
  if (finishedDaily) wireResultCard(el("app"), "chain", state.lang);
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
  else if (b.id === "go-free") return setMode("free");
  else if (b.dataset.share !== undefined) return;
  render();
});
// Switching mode also updates the address, so the menu marks the right item.
function setMode(mode) {
  state.mode = mode;
  history.replaceState(null, "", mode === "free" ? "?mode=free" : location.pathname);
  layout.refresh();
  newPuzzle();
}
// Daily and free play are picked from the menu (chain.html, chain.html?mode=free).
const layout = initLayout((lang) => { state.lang = lang; if (state.puzzle) render(); });

graph = buildGraph(await (await fetch("data/game.json")).json());
newPuzzle();
