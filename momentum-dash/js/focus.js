// Daily focus ("What is your main focus for today?") + focus streak.
//
// Stored data:
//   focus  = { date: "YYYY-MM-DD", text, done }           → resets automatically on a new day
//   streak = { count, lastDoneDate, best, previous }       → previous = state before today's tick (for undo)
import * as storage from "./storage.js";

const els = {
  form: document.getElementById("focus-form"),
  input: document.getElementById("focus-input"),
  view: document.getElementById("focus-view"),
  checkbox: document.getElementById("focus-done"),
  text: document.getElementById("focus-text"),
  remove: document.getElementById("focus-remove"),
  streak: document.getElementById("streak"),
  praise: document.getElementById("focus-praise"),
};

const PRAISE = ["Nice work.", "Well done.", "Great job.", "That's it for today.", "Focus achieved."];

// ---------- streak logic (pure functions, easy to reason about) ----------

// Streak still "alive" if the focus was completed today or yesterday.
export function currentStreak(streak) {
  if (!streak) return 0;
  const alive = [storage.todayKey(), storage.dayOffset(-1)].includes(streak.lastDoneDate);
  return alive ? streak.count : 0;
}

export function completeToday(streak) {
  const today = storage.todayKey();
  if (streak?.lastDoneDate === today) return streak; // already counted today
  const continues = streak?.lastDoneDate === storage.dayOffset(-1);
  const count = continues ? streak.count + 1 : 1;
  return {
    count,
    lastDoneDate: today,
    best: Math.max(count, streak?.best ?? 0),
    previous: streak ? { count: streak.count, lastDoneDate: streak.lastDoneDate, best: streak.best ?? 0 } : null,
  };
}

export function undoToday(streak) {
  if (streak?.lastDoneDate !== storage.todayKey()) return streak; // nothing counted today
  return streak.previous ? { ...streak.previous, previous: null } : null;
}

// ---------- rendering ----------

async function getTodaysFocus() {
  const focus = await storage.get("focus");
  return focus?.date === storage.todayKey() ? focus : null; // yesterday's focus = no focus
}

async function render() {
  const focus = await getTodaysFocus();
  const streak = await storage.get("streak");

  els.form.hidden = Boolean(focus);
  els.view.hidden = !focus;

  if (focus) {
    els.text.textContent = focus.text;
    els.checkbox.checked = focus.done;
    els.view.classList.toggle("is-done", focus.done);
    els.praise.textContent = focus.done ? PRAISE[new Date().getDate() % PRAISE.length] : "";
  } else {
    els.input.value = "";
  }

  const days = currentStreak(streak);
  els.streak.hidden = days === 0;
  els.streak.textContent = `${days}-day streak`;
  els.streak.title = `Days in a row you completed your focus. Best: ${streak?.best ?? days} days`;
}

// ---------- events ----------

function bindEvents() {
  els.form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const text = els.input.value.trim();
    if (!text) return;
    await storage.set("focus", { date: storage.todayKey(), text, done: false });
    render();
  });

  els.checkbox.addEventListener("change", async () => {
    const focus = await getTodaysFocus();
    if (!focus) return;
    const done = els.checkbox.checked;
    const streak = await storage.get("streak");
    await storage.set("focus", { ...focus, done });
    await storage.set("streak", done ? completeToday(streak) : undoToday(streak));
    render();
  });

  els.remove.addEventListener("click", async () => {
    const focus = await getTodaysFocus();
    if (focus?.done) await storage.set("streak", undoToday(await storage.get("streak")));
    await storage.set("focus", null);
    render();
    els.input.focus();
  });

  // Keep every open tab in sync.
  storage.onChange("focus", render);
  storage.onChange("streak", render);
}

export async function initFocus() {
  // The focus section lives inside the clock view, so it appears together with
  // the clock once the user has entered a name.
  bindEvents();
  await render();
  // If the tab stays open past midnight, reset the focus for the new day.
  let day = storage.todayKey();
  setInterval(() => {
    if (storage.todayKey() !== day) { day = storage.todayKey(); render(); }
  }, 60_000);
}
