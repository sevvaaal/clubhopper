import { el, esc, getLang, setLang, loadGraph, loadJson, avatar, flag, initials, dottedInitials, seasonLabel, dailySeed, rng, playerIndex, playerSearch } from "./common.js";
import { career, careerPool, pickPlayer, MAX_GUESSES, HINTS } from "./career.js";

const POS = {
  tr: { G: "Kaleci", D: "Defans", M: "Orta saha", F: "Forvet" },
  en: { G: "Goalkeeper", D: "Defender", M: "Midfielder", F: "Forward" },
};
const TEXT = {
  tr: {
    daily: "Günün kariyeri", free: "Serbest", lang: "EN",
    intro: "Bu kariyer kimin? Kulüpleri ve sezonları en eskiden yeniye.",
    note: "Yalnızca kapsadığımız ligler ve Avrupa kupaları görünür (2010'dan beri). Aradaki boşluk başka bir ligde oynadığı anlamına gelebilir.",
    gap: "… başka bir lig",
    apps: (n) => `${n} maç`,
    search: "Oyuncu adı yaz…",
    left: (n) => `${n} tahmin hakkın kaldı.`,
    wrongs: "Yanlış tahminler:",
    hint: { position: "Mevki", nat: "Uyruk", born: "Doğum yılı", initials: "Baş harfler", photo: "Fotoğraf" },
    won: (n) => `Tebrikler! ${n}. tahminde bildin.`,
    lost: "Bu sefer olmadı. Cevap:",
    giveUp: "Pes et", again: "Yeni oyuncu",
  },
  en: {
    daily: "Daily career", free: "Free play", lang: "TR",
    intro: "Whose career is this? Clubs and seasons, oldest first.",
    note: "Only the leagues and European cups we cover are shown (since 2010). A gap may mean they played in another league.",
    gap: "… another league",
    apps: (n) => `${n} apps`,
    search: "Type a player's name…",
    left: (n) => `${n} guesses left.`,
    wrongs: "Wrong guesses:",
    hint: { position: "Position", nat: "Nationality", born: "Born", initials: "Initials", photo: "Photo" },
    won: (n) => `Well done! You got it on guess ${n}.`,
    lost: "Not this time. The answer:",
    giveUp: "Give up", again: "New player",
  },
};

const state = { lang: getLang(), mode: "daily", answer: null, guesses: [], done: false };
let graph, index, pool, positions;
const T = () => TEXT[state.lang];

function newPuzzle() {
  const random = rng(state.mode === "daily" ? dailySeed("career") : Math.random());
  state.answer = pickPlayer(pool, random);
  state.guesses = [];
  state.done = false;
  render();
}

function hintValue(kind) {
  const p = graph.data.players[state.answer];
  if (kind === "position") return POS[state.lang][positions[state.answer]] || "?";
  if (kind === "nat") return p.nat?.trim() ? flag(p.nat, { withName: true }) : "?";
  if (kind === "born") return p.born?.slice(0, 4) || "?";
  if (kind === "initials") return dottedInitials(p.name);
  return avatar(graph.data, "players", state.answer);
}

function careerHtml() {
  const spells = career(graph, state.answer);
  let html = `<ol class="career">`;
  spells.forEach((s, i) => {
    if (i && s.from - spells[i - 1].to > 1) html += `<li class="gap">${T().gap}</li>`;
    const team = graph.data.teams[s.team];
    const years = s.from === s.to ? seasonLabel(s.from) : `${seasonLabel(s.from)}–${seasonLabel(s.to).slice(-2)}`;
    html += `<li><span class="years">${years}</span>${avatar(graph.data, "teams", s.team)} ${esc(team.name)} <small>${T().apps(s.apps)}</small></li>`;
  });
  return html + `</ol>`;
}

function render() {
  const t = T();
  el("mode-daily").textContent = t.daily;
  el("mode-free").textContent = t.free;
  el("mode-daily").disabled = state.mode === "daily";
  el("mode-free").disabled = state.mode === "free";
  el("lang").textContent = t.lang;
  el("about").textContent = t.note;
  el("about-link").textContent = state.lang === "tr" ? "Hakkında" : "About";
  document.documentElement.lang = state.lang;

  const won = state.guesses.includes(state.answer);
  const wrong = state.guesses.filter((g) => g !== state.answer);
  const shown = state.done ? HINTS.length : Math.min(wrong.length, HINTS.length);

  let html = `<p>${t.intro}</p>${careerHtml()}`;
  if (shown) {
    html += `<ul class="hints">${HINTS.slice(0, shown).map((h) => `<li>${t.hint[h]}: <b>${hintValue(h)}</b></li>`).join("")}</ul>`;
  }
  if (wrong.length) {
    html += `<p class="guesses">${t.wrongs} ${wrong.map((g) => esc(graph.data.players[g].name)).join(", ")}</p>`;
  }
  const who = `${avatar(graph.data, "players", state.answer)} <b>${esc(graph.data.players[state.answer].name)}</b>`;
  if (won) html += `<p class="won">${t.won(state.guesses.length)}</p><p>${who}</p>`;
  else if (state.done) html += `<p>${t.lost} ${who}</p>`;
  else html += `<div id="search"></div><p><small>${t.left(MAX_GUESSES - state.guesses.length)}</small> <button id="give-up">${t.giveUp}</button></p>`;
  if (state.done && state.mode === "free") html += `<p><button id="again">${t.again}</button></p>`;
  el("app").innerHTML = html;
  el("app").removeAttribute("aria-busy");

  if (!state.done) playerSearch(el("search"), graph, index, guess, t.search);
}

function guess(pid) {
  if (state.guesses.includes(pid)) return;
  state.guesses.push(pid);
  if (pid === state.answer || state.guesses.length >= MAX_GUESSES) state.done = true;
  render();
}

el("app").addEventListener("click", (e) => {
  const b = e.target.closest("button");
  if (b?.id === "give-up") { state.done = true; render(); }
  else if (b?.id === "again") newPuzzle();
});
el("mode-daily").onclick = () => { state.mode = "daily"; newPuzzle(); };
el("mode-free").onclick = () => { state.mode = "free"; newPuzzle(); };
el("lang").onclick = () => { state.lang = state.lang === "tr" ? "en" : "tr"; setLang(state.lang); render(); };

graph = await loadGraph();
positions = (await loadJson("matches")).positions;
index = playerIndex(graph);
pool = careerPool(graph);
newPuzzle();
