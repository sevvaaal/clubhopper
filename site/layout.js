// The header and footer every page shares, after Starlinked's layout:
// logo and name on the left, the menu on the right (folded behind ☰ on phones),
// a dot on games whose daily puzzle hasn't been played today, and a footer
// with the tagline, the Scores and About links and the data credit.
//
// Pages put <header id="topbar"></header> and <footer id="footer"></footer> in
// their markup and call initLayout(onLang); onLang runs when the language changes.

import { getLang, setLang } from "./common.js";
import { getDaily } from "./daily.js";

// The chain is the main game, like Starlinked's Daily and Play; the other three
// sit under Mini games. [href, games whose pending daily puts a dot on it, label, pages it covers]
const MINI = ["career", "lineup", "quiz"];
const NAV = [
  ["chain.html", ["chain"], { tr: "Günün zinciri", en: "Daily chain" }, ["chain.html"]],
  ["chain.html?mode=free", [], { tr: "Serbest oyna", en: "Free play" }, ["chain.html?mode=free"]],
  ["minigames.html", MINI, { tr: "Mini oyunlar", en: "Mini games" }, ["minigames.html", "career.html", "lineup.html", "quiz.html"]],
  ["scores.html", [], { tr: "Skorlar", en: "Scores" }, ["scores.html"]],
];
const TEXT = {
  tr: {
    other: "EN", otherLabel: "Switch to English", menu: "Menüyü aç", close: "Menüyü kapat", main: "Ana menü",
    pending: "Bugünün bulmacası seni bekliyor",
    tagline: "Kulüpten kulübe, oyuncudan oyuncuya futbol bulmacaları",
    links: [["./#how", "Nasıl oynanır"], ["minigames.html", "Mini oyunlar"], ["scores.html", "Skorlar"], ["about.html", "Hakkında"]],
    legal: 'Maç ve kadro verisi <a href="https://www.api-football.com" rel="noopener">API-Football</a>\'dan alınır. Kulüp logoları ve oyuncu fotoğrafları sahiplerine aittir.',
  },
  en: {
    other: "TR", otherLabel: "Türkçeye geç", menu: "Open menu", close: "Close menu", main: "Main menu",
    pending: "Today's puzzle is waiting for you",
    tagline: "Football puzzles from club to club, player to player",
    links: [["./#how", "How to play"], ["minigames.html", "Mini games"], ["scores.html", "Scores"], ["about.html", "About"]],
    legal: 'Match and squad data from <a href="https://www.api-football.com" rel="noopener">API-Football</a>. Club crests and player photos belong to their owners.',
  },
};

const here = () => (location.pathname.split("/").pop() || "index.html") + (new URLSearchParams(location.search).get("mode") === "free" ? "?mode=free" : "");

// The living stadium behind the table: a Mexican wave through the crowd now and
// then, and the pitch-side boards scrolling.
// Pure decoration (aria-hidden); style.css animates it with transform/opacity
// only and switches it off for reduced motion.
function buildStadium() {
  if (document.querySelector(".stadium")) return;
  const cols = Math.ceil(Math.max(screen.width, innerWidth, 1600) / 64) + 1;
  const wave = Array.from({ length: cols }, (_, i) => `<i style="--i:${i}"></i>`).join("");
  // Different words on each board so the drift is easy to see.
  // Night-stadium boards: dark panels in the stand's purples, dim LED-like text.
  const board = [["#1d1a3c", "#d6d0e6", "clubhopper"], ["#25204a", "#9d96c4", "günün zinciri"], ["#1d1a3c", "#b9a46a", "kulüpten kulübe"], ["#25204a", "#9d96c4", "oyuncudan oyuncuya"]]
    .map(([bg, ink, word]) => `<span style="--c:${bg};--ink:${ink}">${word}</span>`).join("");
  const el = document.createElement("div");
  el.className = "stadium";
  el.setAttribute("aria-hidden", "true");
  el.innerHTML = `<div class="stand"><div class="wave">${wave}</div></div>
    <div class="boards"><div class="track">${board.repeat(8)}</div></div>`;
  document.body.prepend(el);
}

export function initLayout(onLang = () => {}) {
  buildStadium();
  const top = document.getElementById("topbar");
  const bottom = document.getElementById("footer");
  let lang = getLang();
  let open = false;

  const render = () => {
    const t = TEXT[lang];
    const pending = (games) => games.some((g) => !getDaily(g));
    const anyPending = pending(["chain", ...MINI]);
    top.innerHTML = `
      <a class="brand" href="./" aria-label="Clubhopper"><img src="logo.svg" alt=""><span>clubhopper</span></a>
      <button class="menu-toggle" type="button" aria-expanded="${open}" aria-controls="main-menu" aria-label="${open ? t.close : t.menu}">
        ${open ? "✕" : "☰"}${!open && anyPending ? '<span class="nav-dot" aria-hidden="true"></span>' : ""}
      </button>
      <nav id="main-menu" class="nav${open ? " is-open" : ""}" aria-label="${t.main}">
        ${NAV.map(([href, games, label, pages]) => {
          const current = pages.includes(here()) ? ' aria-current="page"' : "";
          const dot = pending(games) ? `<span class="nav-dot" title="${t.pending}" aria-label="${t.pending}"></span>` : "";
          return `<a class="nav-link" href="${href}"${current}>${label[lang]}${dot}</a>`;
        }).join("")}
        <button class="lang-toggle" type="button" lang="${lang === "tr" ? "en" : "tr"}" aria-label="${t.otherLabel}">${t.other}</button>
      </nav>`;
    if (bottom) bottom.innerHTML = `
      <div class="footer-inner">
        <a class="footer-brand" href="./"><img src="logo.svg" alt=""><span><b>clubhopper</b><small>${t.tagline}</small></span></a>
        <nav class="footer-links" aria-label="${lang === "tr" ? "Alt menü" : "Footer menu"}">${t.links.map(([href, label]) => `<a href="${href}">${label}</a>`).join("")}</nav>
      </div>
      <p class="footer-legal">${t.legal}</p>`;
  };

  top.addEventListener("click", (e) => {
    if (e.target.closest(".menu-toggle")) { open = !open; render(); }
    else if (e.target.closest(".lang-toggle")) {
      lang = lang === "tr" ? "en" : "tr";
      setLang(lang);
      document.documentElement.lang = lang;
      render();
      onLang(lang);
    }
  });
  // A tap outside the bar or Escape folds the phone menu.
  document.addEventListener("pointerdown", (e) => { if (open && !top.contains(e.target)) { open = false; render(); } });
  document.addEventListener("keydown", (e) => { if (open && e.key === "Escape") { open = false; render(); } });

  document.documentElement.lang = lang;
  render();
  // Games call this after a daily result is saved so the menu dots update.
  return { refresh: render };
}
