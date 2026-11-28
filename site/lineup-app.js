import { el, esc, getLang, setLang, loadGraph, loadJson, avatar, flag, initials, dottedInitials, seasonLabel, dailySeed, rng, playerIndex, playerSearch } from "./common.js";
import { initLayout } from "./layout.js";
import { getDaily, recordDaily, resultCard, wireResultCard } from "./daily.js";
import { formationRows, pickLineup } from "./matches.js";

const TEXT = {
  tr: {
    daily: "Günün kadrosu", free: "Serbest", lang: "EN",
    task: (team) => `<b>${team}</b> bu maça hangi 11'le çıktı?`,
    search: "Oyuncu adı yaz…",
    found: (n) => `${n}/11 bulundu`,
    stats: (w, h) => `${w} yanlış, ${h} ipucu`,
    notHere: (name) => `${name} bu ilk 11'de yok.`,
    already: (name) => `${name} zaten bulundu.`,
    hintTip: "Bir oyuncunun yerine tıklarsan uyruğu ve baş harfleri görünür.",
    won: "Tebrikler, ilk 11 tamam!",
    giveUp: "Pes et", again: "Yeni maç",
    note: "Önemli maçlar: büyük kulüplerin lig maçları, Şampiyonlar Ligi son 16 ve sonrası, Avrupa Ligi çeyrek final ve sonrası, Türk kulüplerinin Avrupa maçları.",
    pens: (a, b) => `(penaltılar ${a}-${b})`,
  },
  en: {
    daily: "Daily lineup", free: "Free play", lang: "TR",
    task: (team) => `Which XI did <b>${team}</b> start with?`,
    search: "Type a player's name…",
    found: (n) => `${n}/11 found`,
    stats: (w, h) => `${w} wrong, ${h} hints`,
    notHere: (name) => `${name} isn't in this XI.`,
    already: (name) => `${name} is already in.`,
    hintTip: "Click a player's spot to see their nationality and initials.",
    won: "Well done, the XI is complete!",
    giveUp: "Give up", again: "New match",
    note: "Notable matches: league games between big clubs, Champions League from the round of 16, Europa League from the quarter-finals, and Turkish clubs in Europe.",
    pens: (a, b) => `(${a}-${b} on penalties)`,
  },
};

const state = { lang: getLang(), mode: "daily", match: null, side: 0, found: new Set(), hinted: new Set(), wrong: 0, msg: "", gaveUp: false };
let graph, index, data;
const T = () => TEXT[state.lang];

function newPuzzle() {
  const random = rng(state.mode === "daily" ? dailySeed("lineup") : Math.random());
  Object.assign(state, pickLineup(data.matches, random), { found: new Set(), hinted: new Set(), wrong: 0, msg: "", gaveUp: false });
  state.already = state.mode === "daily" && !!getDaily("lineup");
  render();
}

function matchHeader(m, lang) {
  const team = (i) => `${avatar(graph.data, "teams", m.teams[i])} ${esc(graph.data.teams[m.teams[i]].name)}`;
  const pens = m.pens ? ` ${TEXT[lang].pens(...m.pens)}` : "";
  return `<div class="goal">${team(0)} <b>${m.goals[0]}–${m.goals[1]}</b> ${team(1)}${pens}<br>
    <small>${[`${esc(graph.data.leagues[m.comp])} ${seasonLabel(m.season)}`, esc(m.round), m.date.split("-").reverse().join(".")].map((x) => `<span class="nowrap">${x}</span>`).join(" · ")}</small></div>`;
}

function render() {
  const t = T();
  el("mode-daily").textContent = t.daily;
  el("mode-free").textContent = t.free;
  el("mode-daily").disabled = state.mode === "daily";
  el("mode-free").disabled = state.mode === "free";
  el("about").textContent = t.note;
  if (state.mode === "daily" && state.already) {
    el("app").innerHTML = resultCard("lineup", state.lang, { already: true });
    el("app").removeAttribute("aria-busy");
    return wireResultCard(el("app"), "lineup", state.lang);
  }

  const m = state.match;
  const xi = m.xi[state.side];
  const team = graph.data.teams[m.teams[state.side]].name;
  const done = state.gaveUp || state.found.size === 11;
  const formation = m.formations[state.side];

  let html = matchHeader(m, state.lang);
  html += `<p>${t.task(esc(team))}${formation ? ` <small>(${formation})</small>` : ""}</p>`;
  html += `<div class="pitch">${formationRows(xi, data.positions).map((row) => `<div class="row">${row.map(([pid, num]) => {
    const p = graph.data.players[pid];
    if (state.found.has(pid) || done) {
      return `<div class="spot">${avatar(graph.data, "players", pid)}<span class="name">${esc(p.name)}</span></div>`;
    }
    const hint = state.hinted.has(pid) ? `${flag(p.nat) || "?"} ${esc(dottedInitials(p.name))}` : "&nbsp;";
    return `<button class="spot" data-hint="${pid}"><span class="shirt">${num ?? "?"}</span><span class="name">${hint}</span></button>`;
  }).join("")}</div>`).join("")}</div>`;

  html += `<p><b>${t.found(state.found.size)}</b> · <small>${t.stats(state.wrong, state.hinted.size)}</small></p>`;
  if (state.found.size === 11) html += `<p class="won">${t.won}</p>`;
  if (!done) {
    html += `<p class="msg">${state.msg}</p><div id="search"></div><p><small>${t.hintTip}</small></p><p><button id="give-up">${t.giveUp}</button></p>`;
  }
  if (done && state.mode === "free") html += `<p><button id="again">${t.again}</button></p>`;
  const finishedDaily = done && state.mode === "daily";
  if (finishedDaily) {
    recordDaily("lineup", { won: state.found.size === 11, found: state.found.size, wrong: state.wrong, hints: state.hinted.size });
    layout.refresh();
    html += resultCard("lineup", state.lang);
  }
  el("app").innerHTML = html;
  el("app").removeAttribute("aria-busy");
  if (finishedDaily) wireResultCard(el("app"), "lineup", state.lang);
  if (!done) playerSearch(el("search"), graph, index, guess, t.search);
}

function guess(pid) {
  const xi = state.match.xi[state.side].map(([id]) => id);
  const name = esc(graph.data.players[pid].name);
  if (state.found.has(pid)) state.msg = T().already(name);
  else if (xi.includes(pid)) { state.found.add(pid); state.msg = ""; }
  else { state.wrong++; state.msg = T().notHere(name); }
  render();
}

el("app").addEventListener("click", (e) => {
  const b = e.target.closest("button");
  if (!b) return;
  if (b.dataset.hint) state.hinted.add(Number(b.dataset.hint));
  else if (b.id === "give-up") state.gaveUp = true;
  else if (b.id === "again") return newPuzzle();
  else if (b.id === "go-free") { state.mode = "free"; return newPuzzle(); }
  else return;
  render();
});
el("mode-daily").onclick = () => { state.mode = "daily"; newPuzzle(); };
el("mode-free").onclick = () => { state.mode = "free"; newPuzzle(); };
const layout = initLayout((lang) => { state.lang = lang; if (state.match) render(); });

graph = await loadGraph();
data = await loadJson("matches");
index = playerIndex(graph);
newPuzzle();
