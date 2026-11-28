// Daily puzzle results, kept only in this browser (no account, nothing sent anywhere).
// One record per game per day; the first finish of the day is the one that counts.
// The puzzle day follows Turkish time (+03:00), like Starlinked.

import { esc, puzzleDate } from "./common.js";

export { puzzleDate };

const KEY = "clubhopper:daily:v1";
const MAX = 4 * 365;
export const GAMES = ["chain", "career", "lineup", "quiz"];

const read = () => {
  try {
    const list = JSON.parse(localStorage.getItem(KEY) || "[]");
    return Array.isArray(list) ? list : [];
  } catch { return []; }
};
const write = (list) => {
  try { localStorage.setItem(KEY, JSON.stringify(list.slice(-MAX))); } catch { /* no storage: still playable */ }
};


const shift = (date, days) => {
  const [y, m, d] = date.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, d + days)).toISOString().slice(0, 10);
};

// Seconds until the next puzzle (midnight in Turkey).
export function secondsToNext(now = Date.now()) {
  const [y, m, d] = puzzleDate(now).split("-").map(Number);
  const next = Date.UTC(y, m - 1, d + 1) - 3 * 3600e3;
  return Math.max(0, Math.ceil((next - now) / 1000));
}
export const formatCountdown = (s) =>
  [Math.floor(s / 3600), Math.floor((s % 3600) / 60), s % 60].map((n) => String(n).padStart(2, "0")).join(":");
export const formatDay = (date) => date.split("-").reverse().join(".");

export const getDaily = (game, date = puzzleDate()) => read().find((r) => r.game === game && r.date === date) || null;
export const allResults = () => read();

// result: { won, ...game fields }. Keeps the first result of the day.
export function recordDaily(game, result, date = puzzleDate()) {
  const list = read();
  if (list.some((r) => r.game === game && r.date === date)) return;
  list.push({ game, date, at: Date.now(), ...result });
  list.sort((a, b) => a.date.localeCompare(b.date) || a.at - b.at);
  write(list);
}

// Streaks count consecutive days played. Today not played yet doesn't break the
// streak: it runs through yesterday.
function streaks(dates, today) {
  const set = new Set(dates);
  let current = 0;
  for (let day = set.has(today) ? today : shift(today, -1); set.has(day); day = shift(day, -1)) current++;
  let best = 0, run = 0, prev = null;
  for (const day of [...set].sort()) {
    run = prev && shift(prev, 1) === day ? run + 1 : 1;
    best = Math.max(best, run);
    prev = day;
  }
  return { current, best };
}

// game: one game's stats; null: any game counts for the day.
export function stats(game = null, today = puzzleDate()) {
  const list = read().filter((r) => !game || r.game === game);
  const won = list.filter((r) => r.won).length;
  const { current, best } = streaks(list.map((r) => r.date), today);
  return {
    played: list.length, won,
    winRate: list.length ? Math.round((won / list.length) * 100) : 0,
    currentStreak: current, bestStreak: best,
    days: new Set(list.map((r) => r.date)).size,
    recent: [...list].reverse(),
  };
}

const TEXT = {
  tr: {
    name: { chain: "Zincir", career: "Kariyer yolu", lineup: "Kadroyu tamamla", quiz: "Maç quiz'i" },
    won: "Bugünkü bulmacayı çözdün", lost: "Bugün olmadı",
    already: "Bugünün bulmacasını oynadın",
    played: "oynandı", winRate: "kazanma", streak: "seri", best: "en iyi seri",
    next: "Sonraki bulmaca", ready: "Yeni bulmaca hazır, yenile",
    share: "Paylaş", copied: "Sonuç panoya kopyalandı", shareFail: "Paylaşılamadı, metni elle kopyalayabilirsin",
    free: "Beklemek istemiyor musun? Serbest modda oyna", scores: "Tüm skorlar",
    summary: {
      chain: (r) => r.won ? `${r.links} adımda bağladın (en kısa ${r.best})` : `Pes ettin (en kısa ${r.best} adım)`,
      career: (r) => r.won ? `${r.guesses}. tahminde bildin` : "Oyuncuyu bulamadın",
      lineup: (r) => `${r.found}/11 oyuncu, ${r.wrong} yanlış, ${r.hints} ipucu`,
      quiz: (r) => r.won ? `${r.points} puan` : "Maçı bilemedin",
    },
  },
  en: {
    name: { chain: "Chain", career: "Career path", lineup: "Complete the lineup", quiz: "Match quiz" },
    won: "You solved today's puzzle", lost: "Not today",
    already: "You've played today's puzzle",
    played: "played", winRate: "won", streak: "streak", best: "best streak",
    next: "Next puzzle in", ready: "New puzzle ready, refresh",
    share: "Share", copied: "Result copied to clipboard", shareFail: "Couldn't share, you can copy the text by hand",
    free: "Don't want to wait? Play free mode", scores: "All scores",
    summary: {
      chain: (r) => r.won ? `Linked in ${r.links} (shortest ${r.best})` : `Gave up (shortest ${r.best})`,
      career: (r) => r.won ? `Got it on guess ${r.guesses}` : "Didn't find the player",
      lineup: (r) => `${r.found}/11 players, ${r.wrong} wrong, ${r.hints} hints`,
      quiz: (r) => r.won ? `${r.points} points` : "Didn't get the match",
    },
  },
};
export const gameName = (game, lang) => TEXT[lang].name[game];
export const summaryText = (r, lang) => TEXT[lang].summary[r.game](r);

// The card shown under a finished daily puzzle: result, streaks, countdown.
// `freeButton` is the id of a button the page wires to free mode.
export function resultCard(game, lang, { already = false } = {}) {
  const t = TEXT[lang];
  const r = getDaily(game);
  if (!r) return "";
  const s = stats(game);
  const tile = (value, label) => `<div class="tile"><b>${value}</b><span>${label}</span></div>`;
  return `<section class="result-card" aria-label="${esc(t.next)}">
    <h2>${already ? t.already : r.won ? t.won : t.lost}</h2>
    <p class="result-summary">${esc(gameName(game, lang))} ${formatDay(r.date)}: ${esc(summaryText(r, lang))}</p>
    <div class="tiles">${tile(s.played, t.played)}${tile(lang === "tr" ? `%${s.winRate}` : `${s.winRate}%`, t.winRate)}${tile(s.currentStreak, t.streak)}${tile(s.bestStreak, t.best)}</div>
    <p class="next"><span>${t.next}</span> <b data-countdown>${formatCountdown(secondsToNext())}</b></p>
    <p class="result-actions"><button type="button" data-share>${t.share}</button> <button type="button" id="go-free">${t.free}</button></p>
    <p class="share-note" role="status" data-share-note></p>
    <p class="result-more"><a href="scores.html">${t.scores}</a></p>
  </section>`;
}

// Wires the card's countdown and share button; call after it is in the page.
let ticker = null;
export function wireResultCard(root, game, lang) {
  clearInterval(ticker);
  const clock = root.querySelector("[data-countdown]");
  if (clock) {
    ticker = setInterval(() => {
      const s = secondsToNext();
      if (!document.body.contains(clock)) return clearInterval(ticker);
      if (s > 0) clock.textContent = formatCountdown(s);
      else {
        clearInterval(ticker);
        clock.outerHTML = `<button type="button" onclick="location.reload()">${TEXT[lang].ready}</button>`;
      }
    }, 1000);
  }
  const share = root.querySelector("[data-share]");
  if (share) share.onclick = async () => {
    const r = getDaily(game);
    const note = root.querySelector("[data-share-note]");
    const text = [`clubhopper · ${gameName(game, lang)} ${formatDay(r.date)}`, summaryText(r, lang), location.origin + location.pathname].join("\n");
    try {
      if (navigator.share) { await navigator.share({ text }); return; }
      await navigator.clipboard.writeText(text);
      note.textContent = TEXT[lang].copied;
    } catch (err) {
      if (err?.name !== "AbortError") note.textContent = TEXT[lang].shareFail;
    }
  };
}
