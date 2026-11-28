import { el, esc, getLang, setLang, loadGraph, loadJson, avatar, seasonLabel, dailySeed, rng } from "./common.js";
import { initLayout } from "./layout.js";
import { getDaily, recordDaily, resultCard, wireResultCard } from "./daily.js";
import { quizPool, quizOptions, matchFeed, quizPoints } from "./matches.js";

// The match is told as a live text commentary: the clock runs, each event is
// typed out as it happens, and the player picks the match from four options
// whenever they think they know it. Earlier answers score more.

const REASONS = {
  tr: { foul: "faul", argument: "itiraz", time: "zaman geçirme", handball: "elle oynama", simulation: "simülasyon",
    violent: "sert hareket", persistent: "sürekli faul", lastman: "son adam faulü", offball: "topsuz alanda faul", dangerous: "tehlikeli oyun" },
  en: { foul: "foul", argument: "dissent", time: "time wasting", handball: "handball", simulation: "simulation",
    violent: "violent conduct", persistent: "persistent fouling", lastman: "last-man foul", offball: "off-the-ball foul", dangerous: "dangerous play" },
};

const TEXT = {
  tr: {
    daily: "Günün maçı", free: "Serbest", lang: "EN",
    ask: "Bu hangi maç?",
    home: "ev sahibi", away: "deplasman",
    live: "Canlı", ht: "Devre arası", ft: "Maç sonu",
    pause: "Duraklat", resume: "Devam et", fast: "Hızlandır", slow: "Normal hız",
    points: (n) => `Puan: ${n}`,
    rule: "Erken bilene çok puan: 30. ve 60. dakikada ve maç bitince 1 puan düşer. Her yanlış şık da 1 puan götürür.",
    won: (n) => `Doğru! ${n} puan aldın.`,
    lost: "Bilemedin. Doğru cevap:",
    again: "Yeni maç",
    line: {
      kickoff: () => "Hakem başlama düdüğünü çaldı.",
      half: (s) => `İlk yarı sona erdi. Skor ${s[0]}-${s[1]}.`,
      extra: (s) => `Normal süre ${s[0]}-${s[1]} bitti, uzatmalara gidiliyor.`,
      full: (s) => `Maç sona erdi! Skor ${s[0]}-${s[1]}.`,
      pens: (p) => `Penaltı atışları ${p[0]}-${p[1]} bitti.`,
      goal: (x) => `GOL! ${x.who} (${x.side}) skoru ${x.score[0]}-${x.score[1]} yaptı.${x.other ? ` Asist: ${x.other}.` : ""}`,
      pen: (x) => `GOL! ${x.who} (${x.side}) penaltıyı gole çevirdi. Skor ${x.score[0]}-${x.score[1]}.`,
      og: (x) => `${x.who} topu kendi ağlarına gönderdi! Skor ${x.score[0]}-${x.score[1]}.`,
      misspen: (x) => `${x.who} (${x.side}) penaltıdan yararlanamadı.`,
      yellow: (x) => `${x.who} (${x.side}) sarı kart gördü${x.reason ? `: ${x.reason}` : ""}.`,
      red: (x) => `${x.who} (${x.side}) ${x.second ? "ikinci sarıdan" : "doğrudan"} kırmızı kart gördü${x.reason ? `: ${x.reason}` : ""}!`,
      sub: (x) => `Oyuncu değişikliği (${x.side}): ${x.other || "?"} girdi, ${x.who} çıktı.`,
      "var-nogoal": (x) => `VAR incelemesi sonrası gol iptal edildi${x.who ? `: ${x.who} (${x.side})` : ""}.`,
      "var-goal": (x) => `VAR golü onayladı${x.who ? `: ${x.who} (${x.side})` : ""}.`,
      "var-pen": () => "VAR incelemesi sonrası penaltı noktası gösterildi.",
      "var-nopen": () => "VAR incelemesi sonrası penaltı kararı kaldırıldı.",
      "var-red": (x) => `VAR incelemesi: ${x.who || "oyuncu"} (${x.side}) için kart kırmızıya çevrildi.`,
      "var-nored": (x) => `VAR kırmızı kartı geri aldı${x.who ? `: ${x.who} (${x.side})` : ""}.`,
      stats: (st) => `İstatistikler: ${statParts(st, ["topla oynama", "şut", "isabetli şut", "korner"])}.`,
      info: (m) => `Maç bilgisi: ${[m.round, formatDate(m.date), m.venue].filter(Boolean).join(", ")}.`,
      coaches: (c) => `Teknik direktörler: ${c[0] || "?"} (ev sahibi), ${c[1] || "?"} (deplasman).`,
    },
  },
  en: {
    daily: "Daily match", free: "Free play", lang: "TR",
    ask: "Which match is this?",
    home: "home", away: "away",
    live: "Live", ht: "Half-time", ft: "Full-time",
    pause: "Pause", resume: "Resume", fast: "Speed up", slow: "Normal speed",
    points: (n) => `Points: ${n}`,
    rule: "Answer early for more points: you lose 1 at the 30th and 60th minute and at full-time, and 1 for every wrong pick.",
    won: (n) => `Correct! You scored ${n}.`,
    lost: "Not this time. The answer:",
    again: "New match",
    line: {
      kickoff: () => "The referee blows the whistle and we're under way.",
      half: (s) => `Half-time. It's ${s[0]}-${s[1]}.`,
      extra: (s) => `${s[0]}-${s[1]} after 90 minutes, so we go to extra time.`,
      full: (s) => `Full-time! It finishes ${s[0]}-${s[1]}.`,
      pens: (p) => `The penalty shootout ends ${p[0]}-${p[1]}.`,
      goal: (x) => `GOAL! ${x.who} (${x.side}) makes it ${x.score[0]}-${x.score[1]}.${x.other ? ` Assist: ${x.other}.` : ""}`,
      pen: (x) => `GOAL! ${x.who} (${x.side}) scores from the spot. ${x.score[0]}-${x.score[1]}.`,
      og: (x) => `Own goal by ${x.who}! ${x.score[0]}-${x.score[1]}.`,
      misspen: (x) => `${x.who} (${x.side}) misses a penalty.`,
      yellow: (x) => `${x.who} (${x.side}) is booked${x.reason ? ` for ${x.reason}` : ""}.`,
      red: (x) => `${x.who} (${x.side}) is sent off${x.second ? " for a second yellow" : ""}${x.reason ? ` (${x.reason})` : ""}!`,
      sub: (x) => `Substitution (${x.side}): ${x.other || "?"} on, ${x.who} off.`,
      "var-nogoal": (x) => `VAR rules out the goal${x.who ? ` by ${x.who} (${x.side})` : ""}.`,
      "var-goal": (x) => `VAR confirms the goal${x.who ? ` by ${x.who} (${x.side})` : ""}.`,
      "var-pen": () => "After a VAR review, the referee points to the spot.",
      "var-nopen": () => "After a VAR review, the penalty is overturned.",
      "var-red": (x) => `After a VAR review, ${x.who || "a player"} (${x.side}) is shown a red card instead.`,
      "var-nored": (x) => `VAR overturns the red card${x.who ? ` for ${x.who} (${x.side})` : ""}.`,
      stats: (st) => `Stats: ${statParts(st, ["possession", "shots", "on target", "corners"])}.`,
      info: (m) => `Match details: ${[m.round, formatDate(m.date), m.venue].filter(Boolean).join(", ")}.`,
      coaches: (c) => `Managers: ${c[0] || "?"} (home), ${c[1] || "?"} (away).`,
    },
  },
};

function statParts(st, names) {
  return names.map((name, i) => {
    const [a, b] = [st[0][i], st[1][i]];
    if (a == null || b == null) return null;
    return i === 0 ? `${name} %${a}-%${b}` : `${name} ${a}-${b}`;
  }).filter(Boolean).join(", ");
}
const formatDate = (iso) => iso.split("-").reverse().join(".");

// Pace of the commentary, in milliseconds.
const PACE = {
  normal: { minute: 45, char: 22, pause: 1100 },
  fast: { minute: 12, char: 6, pause: 350 },
};
const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;

const state = {
  lang: getLang(), mode: "daily", match: null, options: [], feed: [],
  shown: 0,       // feed items fully on screen
  typing: -1,     // index of the item being typed, or -1
  clock: 0, score: [0, 0], finished: false,
  wrong: new Set(), done: false, won: false, paused: false, fast: false,
};
let graph, pool, run = 0;
const T = () => TEXT[state.lang];
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const teamName = (id) => esc(graph.data.teams[id].name);
const personName = (x) => (typeof x === "number" ? graph.data.players[x]?.name : x) || "";

function lineText(item) {
  const t = T();
  const line = t.line[item.kind];
  if (["kickoff", "half", "extra", "full"].includes(item.kind)) return line(item.score);
  if (item.kind === "pens") return line(item.pens);
  if (item.kind === "stats") return line(item.stats);
  if (item.kind === "info") return line(state.match);
  if (item.kind === "coaches") return line(state.match.coaches);
  return line({
    who: personName(item.who), other: personName(item.other),
    side: item.side ? t.away : t.home, score: item.score, second: item.second,
    reason: item.note ? REASONS[state.lang][item.note] : "",
  });
}

const lineHtml = (item, i, text) =>
  `<li class="ev k-${item.kind}${item.second ? " k-red2" : ""}" data-i="${i}"><span class="min">${item.label}</span><span class="txt">${esc(text)}</span></li>`;

const status = () => {
  const t = T();
  if (state.finished || state.done) return t.ft;
  const last = state.feed[state.shown - 1];
  return last?.kind === "half" && state.clock <= 45 ? t.ht : t.live;
};
const points = () => quizPoints(state.clock, state.finished, state.wrong.size);

function renderBoard() {
  const t = T();
  el("clock").textContent = state.finished || state.done ? "" : `${state.clock}'`;
  el("state").textContent = status();
  el("score").textContent = `${state.score[0]} - ${state.score[1]}`;
  el("points").textContent = t.points(points());
}

function render() {
  const t = T();
  el("mode-daily").textContent = t.daily;
  el("mode-free").textContent = t.free;
  el("mode-daily").disabled = state.mode === "daily";
  el("mode-free").disabled = state.mode === "free";
  el("about").textContent = t.rule;
  if (state.mode === "daily" && state.already) {
    el("app").innerHTML = resultCard("quiz", state.lang, { already: true });
    el("app").removeAttribute("aria-busy");
    return wireResultCard(el("app"), "quiz", state.lang);
  }

  const m = state.match;
  const upto = state.done ? state.feed.length : state.shown + (state.typing >= 0 ? 1 : 0);
  let html = `<div class="board">
      <p class="comp">${esc(graph.data.leagues[m.comp])} ${seasonLabel(m.season)}</p>
      <div class="scoreline"><span>${t.home}</span><b id="score"></b><span>${t.away}</span></div>
      <p class="clockline"><span id="state" class="live"></span> <b id="clock"></b> <span id="points" class="pts"></span></p>
    </div>
    <ol class="feed" id="feed" aria-live="polite">${state.feed.slice(0, upto).map((item, i) => lineHtml(item, i, lineText(item))).join("")}</ol>`;
  if (!state.done) {
    html += `<p class="feed-controls"><button id="pause">${state.paused ? t.resume : t.pause}</button> <button id="speed">${state.fast ? t.slow : t.fast}</button></p>`;
  }
  html += `<p><b>${t.ask}</b></p><div class="options">${state.options.map((o) => {
    const cls = state.wrong.has(o.id) ? "wrong" : state.done && o === m ? "right" : "";
    const off = state.done || state.wrong.has(o.id) ? " disabled" : "";
    return `<button class="${cls}" data-pick="${o.id}"${off}>${avatar(graph.data, "teams", o.teams[0])} ${teamName(o.teams[0])} – ${teamName(o.teams[1])} ${avatar(graph.data, "teams", o.teams[1])}</button>`;
  }).join("")}</div>`;
  if (state.done && state.won) html += `<p class="won">${t.won(points())}</p>`;
  else if (state.done) html += `<p>${t.lost} <b>${teamName(m.teams[0])} ${m.goals[0]}–${m.goals[1]} ${teamName(m.teams[1])}</b></p>`;
  if (state.done && state.mode === "free") html += `<p><button id="again">${t.again}</button></p>`;
  const finishedDaily = state.done && state.mode === "daily";
  if (finishedDaily) {
    recordDaily("quiz", { won: state.won, points: state.won ? points() : 0, wrong: state.wrong.size });
    layout.refresh();
    html += resultCard("quiz", state.lang);
  }
  el("app").innerHTML = html;
  el("app").removeAttribute("aria-busy");
  if (finishedDaily) wireResultCard(el("app"), "quiz", state.lang);
  renderBoard();
  scrollFeed();
}

function scrollFeed() {
  const feed = el("feed");
  if (feed) feed.scrollTop = feed.scrollHeight;
}

async function waitWhilePaused(id) {
  while (state.paused && id === run) await sleep(120);
}

// Runs the commentary until the feed ends, the player answers, or a new match starts.
async function stream(id) {
  const live = () => id === run && !state.done;
  while (live() && state.shown < state.feed.length) {
    const item = state.feed[state.shown];
    const pace = state.fast ? PACE.fast : PACE.normal;
    // run the clock up to this event
    while (live() && state.clock < item.minute) {
      await waitWhilePaused(id);
      state.clock = reducedMotion ? item.minute : state.clock + 1;
      renderBoard();
      if (!reducedMotion) await sleep(state.fast ? PACE.fast.minute : PACE.normal.minute);
    }
    if (!live()) return;
    // type the line out
    state.typing = state.shown;
    const i = state.shown;
    el("feed").insertAdjacentHTML("beforeend", lineHtml(item, i, ""));
    const text = lineText(item);
    for (let k = 1; k <= text.length && live() && !reducedMotion; k++) {
      await waitWhilePaused(id);
      const node = document.querySelector(`#feed li[data-i="${i}"] .txt`);
      if (!node) break;
      node.textContent = lineText(item).slice(0, k);
      scrollFeed();
      await sleep(state.fast ? PACE.fast.char : PACE.normal.char);
    }
    if (!live()) return;
    const node = document.querySelector(`#feed li[data-i="${i}"] .txt`);
    if (node) node.textContent = lineText(item);
    state.typing = -1;
    state.shown++;
    state.score = item.score;
    if (item.kind === "full") state.finished = true;
    renderBoard();
    scrollFeed();
    await sleep(pace.pause);
    await waitWhilePaused(id);
  }
}

function finish(won) {
  Object.assign(state, { done: true, won, typing: -1, shown: state.feed.length, score: [...state.match.goals] });
  render();
}

function newPuzzle() {
  const random = rng(state.mode === "daily" ? dailySeed("quiz") : Math.random());
  state.match = pool[Math.floor(random() * pool.length)];
  state.options = quizOptions(pool, state.match, random);
  state.feed = matchFeed(state.match);
  Object.assign(state, { shown: 0, typing: -1, clock: 0, score: [0, 0], finished: false, wrong: new Set(), done: false, won: false, paused: false });
  state.already = state.mode === "daily" && !!getDaily("quiz");
  run++; // stops any commentary still running from the previous match
  render();
  if (!state.already) stream(run);
}

el("app").addEventListener("click", (e) => {
  const b = e.target.closest("button");
  if (!b) return;
  if (b.dataset.pick) {
    const id = Number(b.dataset.pick);
    if (id === state.match.id) return finish(true);
    state.wrong.add(id);
    if (state.wrong.size === 3 || points() === 0) return finish(false);
    b.disabled = true;
    b.classList.add("wrong");
    renderBoard();
  } else if (b.id === "pause") {
    state.paused = !state.paused;
    b.textContent = state.paused ? T().resume : T().pause;
  } else if (b.id === "speed") {
    state.fast = !state.fast;
    b.textContent = state.fast ? T().slow : T().fast;
  } else if (b.id === "again") newPuzzle();
  else if (b.id === "go-free") { state.mode = "free"; newPuzzle(); }
});
el("mode-daily").onclick = () => { state.mode = "daily"; newPuzzle(); };
el("mode-free").onclick = () => { state.mode = "free"; newPuzzle(); };
// the line being typed is redrawn and keeps typing in the new language
const layout = initLayout((lang) => { state.lang = lang; if (state.match) render(); });

graph = await loadGraph();
pool = quizPool((await loadJson("matches")).matches);
newPuzzle();
