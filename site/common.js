// Shared bits for the game pages: data loading, language, pictures, player
// search. Game rules live in their own modules (chain.js, career.js, ...).

import { buildGraph, rng } from "./chain.js";

export { rng };

export const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
export const el = (id) => document.getElementById(id);

// Language is shared by all pages.
export function getLang() {
  try { return localStorage.getItem("lang") || "tr"; } catch { return "tr"; }
}
export function setLang(lang) {
  try { localStorage.setItem("lang", lang); } catch {}
}

export const seasonLabel = (season) => `${season}/${String(season + 1).slice(2)}`;

// YYYY-MM-DD of today's puzzle. The day turns over at midnight Turkish time (+03:00).
export const puzzleDate = (now = Date.now()) => new Date(now + 3 * 3600e3).toISOString().slice(0, 10);
// Seed for the daily puzzle, plus the game's name so the games differ.
export const dailySeed = (game) => `${puzzleDate()}-${game}`;

const cache = {};
export async function loadJson(name) {
  cache[name] ??= fetch(`data/${name}.json`).then((r) => r.json());
  return cache[name];
}
export async function loadGraph() {
  const [game, flags] = await Promise.all([loadJson("game"), loadJson("flags").catch(() => ({}))]);
  FLAGS = flags;
  return buildGraph(game);
}

// Nationality flags from Kenney's Flag Pack (pipeline/flags.py). The name is
// the fallback for the few nationalities without a flag.
let FLAGS = {};
export function flag(nat, { withName = false } = {}) {
  const name = String(nat || "").trim();
  if (!name) return "";
  const code = FLAGS[name];
  if (!code) return esc(name);
  const img = `<img class="flag" src="img/flags/${code}.svg" alt="${esc(name)}" title="${esc(name)}" width="20" height="20">`;
  return withName ? `${img} ${esc(name)}` : img;
}

// Our own small copies from images.py; initials when there's no picture.
export function initials(name) {
  const words = name.replace(/\./g, " ").split(/\s+/).filter(Boolean);
  const pick = words.length > 1 ? [words[0], words[words.length - 1]] : words;
  return pick.map((w) => w[0]).join("").toLocaleUpperCase("tr");
}
// Initials as shown in hints: "Mauro Icardi" -> "M.I."
export const dottedInitials = (name) => [...initials(name)].map((c) => `${c}.`).join("");

export function avatar(data, kind, id, size = 32) {
  const item = kind === "players" ? data.players[id] : data.teams[id];
  const name = item?.name || "?";
  if (item?.img) return `<img class="pic ${kind}" src="img/${kind}/${id}.webp" alt="" loading="lazy" width="${size}" height="${size}">`;
  const hue = (Number(id) * 47) % 360;
  return `<span class="pic initials ${kind}" style="--hue:${hue}" aria-hidden="true">${esc(initials(name))}</span>`;
}

// "Çağlar Söyüncü" and "caglar soyuncu" should match.
export function normalize(s) {
  return String(s || "")
    .replace(/ı/g, "i").replace(/İ/g, "I").replace(/ø/gi, "o").replace(/ß/g, "ss")
    .replace(/æ/gi, "ae").replace(/đ/gi, "d").replace(/ł/gi, "l")
    .normalize("NFD").replace(/[̀-ͯ]/g, "")
    .toLowerCase().replace(/[^a-z0-9 ]+/g, " ").replace(/\s+/g, " ").trim();
}

// Player search: every typed word must start a word of the player's name
// (short name, first or last name). Best known players first.
export function playerIndex(graph) {
  const list = [];
  for (const [pid, p] of Object.entries(graph.data.players)) {
    const words = new Set(normalize(`${p.name} ${p.first || ""} ${p.last || ""}`).split(" "));
    list.push({ id: Number(pid), words: [...words], minutes: graph.minutes.get(Number(pid)) || 0 });
  }
  list.sort((a, b) => b.minutes - a.minutes);
  return list;
}
export function searchPlayers(index, query, limit = 8) {
  const q = normalize(query).split(" ").filter(Boolean);
  if (!q.length) return [];
  const out = [];
  for (const p of index) {
    if (q.every((t) => p.words.some((w) => w.startsWith(t)))) {
      out.push(p.id);
      if (out.length >= limit) break;
    }
  }
  return out;
}

// A text box with suggestions; calls onPick(player id).
export function playerSearch(container, graph, index, onPick, placeholder) {
  container.innerHTML = `<div class="search"><input type="search" autocomplete="off" placeholder="${esc(placeholder)}"><ul></ul></div>`;
  const input = container.querySelector("input");
  const list = container.querySelector("ul");
  let hits = [];
  const show = () => {
    hits = searchPlayers(index, input.value);
    list.innerHTML = hits.map((pid) => {
      const p = graph.data.players[pid];
      const born = p.born?.slice(0, 4);
      return `<li><button type="button" data-pick="${pid}">${avatar(graph.data, "players", pid)} ${esc(p.name)} ${flag(p.nat)} <small>${esc(born || "")}</small></button></li>`;
    }).join("");
  };
  const pick = (pid) => { input.value = ""; list.innerHTML = ""; onPick(pid); };
  input.addEventListener("input", show);
  input.addEventListener("keydown", (e) => { if (e.key === "Enter" && hits.length) pick(hits[0]); });
  list.addEventListener("click", (e) => {
    const b = e.target.closest("[data-pick]");
    if (b) pick(Number(b.dataset.pick));
  });
  input.focus();
}
