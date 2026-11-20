// Pomodoro timer: 25 min focus → 5 min break, and a 15 min long break after every 4th focus round.
//
// Key idea: we store WHEN the phase ends (a timestamp), not a countdown. Every tab computes
// "endsAt - now" itself, so all open tabs show the same time, and closing a tab loses nothing.
//
// Stored data:
//   pomodoro    = { mode: "focus"|"short"|"long", status: "idle"|"running"|"paused",
//                   endsAt (when running), remaining (ms, when idle/paused), round (focus rounds done in this cycle) }
//   pomodoroLog = { date: "YYYY-MM-DD", count }   → completed focus rounds today
import * as storage from "./storage.js";
import { getSettings } from "./settings.js";
import { openGame } from "./game.js";

const MINUTE = 60_000;
// Phase lengths in ms; defaults 25/5/15 min, adjustable in the settings panel.
const DURATIONS = { focus: 25 * MINUTE, short: 5 * MINUTE, long: 15 * MINUTE };

async function loadDurations() {
  const { durations } = await getSettings();
  for (const mode of Object.keys(DURATIONS)) DURATIONS[mode] = durations[mode] * MINUTE;
}
const LABELS = { focus: "Focus", short: "Short break", long: "Long break" };
const ROUNDS_PER_CYCLE = 4;

const els = {
  root: document.getElementById("pomodoro"),
  ring: document.getElementById("pomo-ring-progress"),
  time: document.getElementById("pomo-time"),
  label: document.getElementById("pomo-label"),
  round: document.getElementById("pomo-round"),
  toggle: document.getElementById("pomo-toggle"),
  reset: document.getElementById("pomo-reset"),
  skip: document.getElementById("pomo-skip"),
  play: document.getElementById("pomo-play"),
};

const CIRCUMFERENCE = 2 * Math.PI * Number(els.ring.getAttribute("r"));
const defaultTitle = document.title;
let state = null;

// ---------- state transitions (pure: take a state, return a new one) ----------

const fresh = (mode, round = 0) => ({ mode, status: "idle", remaining: DURATIONS[mode], endsAt: null, round });

function remainingMs(s, now = Date.now()) {
  return s.status === "running" ? Math.max(0, s.endsAt - now) : s.remaining;
}

function start(s) {
  return { ...s, status: "running", endsAt: Date.now() + s.remaining, remaining: null };
}

function pause(s) {
  return { ...s, status: "paused", remaining: remainingMs(s), endsAt: null };
}

// Move to the next phase. Only a finished *focus* phase counts as a round.
export function nextPhase(s) {
  if (s.mode !== "focus") return fresh("focus", s.round % ROUNDS_PER_CYCLE);
  const round = s.round + 1;
  return fresh(round % ROUNDS_PER_CYCLE === 0 ? "long" : "short", round);
}

// ---------- side effects ----------

async function save(next) {
  state = next;
  await storage.set("pomodoro", next);
  render();
}

async function logCompletedFocus() {
  const today = storage.todayKey();
  const log = await storage.get("pomodoroLog");
  const count = log?.date === today ? log.count + 1 : 1;
  await storage.set("pomodoroLog", { date: today, count });
}

// Short two-note chime generated with the Web Audio API (no sound file needed).
let audio = null;
function chime() {
  if (!audio) return; // browsers only allow sound after the user interacted with this tab
  const notes = [880, 660];
  notes.forEach((frequency, i) => {
    const t = audio.currentTime + i * 0.28;
    const osc = audio.createOscillator();
    const gain = audio.createGain();
    osc.type = "sine";
    osc.frequency.value = frequency;
    gain.gain.setValueAtTime(0.0001, t);
    gain.gain.exponentialRampToValueAtTime(0.25, t + 0.02);
    gain.gain.exponentialRampToValueAtTime(0.0001, t + 0.6);
    osc.connect(gain).connect(audio.destination);
    osc.start(t);
    osc.stop(t + 0.65);
  });
}

async function completePhase() {
  // Several tabs may be open. Only the visible one finishes the phase, so a round
  // is never counted twice; the other tabs update through the storage listener.
  if (document.visibilityState !== "visible") return;
  const latest = await storage.get("pomodoro");
  if (latest?.status !== "running" || latest.endsAt !== state.endsAt) return; // another tab already did it
  if (latest.mode === "focus") await logCompletedFocus();
  chime();
  await save(nextPhase(latest));
}

// ---------- rendering ----------

function format(ms) {
  const total = Math.ceil(ms / 1000);
  return `${String(Math.floor(total / 60)).padStart(2, "0")}:${String(total % 60).padStart(2, "0")}`;
}

function render() {
  if (!state) return;
  const remaining = remainingMs(state);
  const progress = Math.min(1, Math.max(0, 1 - remaining / DURATIONS[state.mode]));

  els.time.textContent = format(remaining);
  els.ring.style.strokeDashoffset = String(CIRCUMFERENCE * (1 - progress));
  els.label.textContent = LABELS[state.mode];
  els.round.textContent = state.mode === "focus"
    ? `Round ${(state.round % ROUNDS_PER_CYCLE) + 1} of ${ROUNDS_PER_CYCLE}`
    : "Time to rest";
  els.toggle.textContent = state.status === "running" ? "Pause" : state.status === "paused" ? "Resume" : "Start";
  els.root.dataset.mode = state.mode;
  els.root.dataset.status = state.status;
  els.play.hidden = state.mode === "focus"; // break time → offer the mini game

  // Show the countdown in the tab title while running (visible even from other tabs).
  document.title = state.status === "running" ? `${format(remaining)} · ${LABELS[state.mode]}` : defaultTitle;
}

function loop() {
  if (state?.status === "running" && remainingMs(state) <= 0) completePhase();
  render();
}

// ---------- events ----------

function bindEvents() {
  els.toggle.addEventListener("click", () => {
    audio ??= new AudioContext(); // created on a click, so the browser allows the chime later
    save(state.status === "running" ? pause(state) : start(state));
  });
  els.reset.addEventListener("click", () => save(fresh(state.mode, state.round)));
  els.skip.addEventListener("click", () => save(nextPhase(state)));
  els.play.addEventListener("click", openGame);

  storage.onChange("pomodoro", (next) => { state = next ?? fresh("focus"); render(); });
  document.addEventListener("visibilitychange", loop); // finish a phase that ended while hidden
}

export async function initPomodoro() {
  await loadDurations();
  state = (await storage.get("pomodoro")) ?? fresh("focus");

  // New durations from the settings panel apply right away to a timer that hasn't started yet;
  // a running or paused phase keeps its length.
  storage.onChange("settings", async () => {
    await loadDurations();
    if (state.status === "idle" && state.remaining !== DURATIONS[state.mode]) {
      save(fresh(state.mode, state.round));
    }
  });
  els.ring.style.strokeDasharray = String(CIRCUMFERENCE);
  bindEvents();
  render();
  setInterval(loop, 250);
}
