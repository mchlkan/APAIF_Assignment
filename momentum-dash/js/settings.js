// Settings panel (gear icon, bottom right). Every change is saved immediately and
// the other widgets react through storage.onChange, in this tab and all other tabs.
//
// Stored data:
//   name     = "Michael"   (separate key, also edited from the greeting)
//   settings = { city, use24h, show: { pomodoro, weather, quote, todos }, durations: { focus, short, long } (minutes) }
import * as storage from "./storage.js";

export const DEFAULT_SETTINGS = {
  city: "Lisbon",
  use24h: true,
  show: { pomodoro: true, weather: true, quote: true, todos: true },
  durations: { focus: 25, short: 5, long: 15 },
};

// Stored settings merged over the defaults (so new options work for existing users).
export async function getSettings() {
  const saved = await storage.get("settings", {});
  return {
    ...DEFAULT_SETTINGS,
    ...saved,
    show: { ...DEFAULT_SETTINGS.show, ...saved.show },
    durations: { ...DEFAULT_SETTINGS.durations, ...saved.durations },
  };
}

const els = {
  toggle: document.getElementById("settings-toggle"),
  panel: document.getElementById("settings-panel"),
  form: document.getElementById("settings-form"),
  reset: document.getElementById("settings-reset"),
};

const field = (name) => els.form.elements.namedItem(name);

async function fillForm() {
  const s = await getSettings();
  field("name").value = await storage.get("name", "");
  field("city").value = s.city;
  field("use24h").checked = s.use24h;
  for (const key of Object.keys(s.show)) field(`show-${key}`).checked = s.show[key];
  for (const key of Object.keys(s.durations)) field(`duration-${key}`).value = s.durations[key];
}

// Hide/show widgets with a class on <body>, so it never fights with a widget's own `hidden` state.
function applyVisibility(show) {
  for (const [key, visible] of Object.entries(show)) {
    document.body.classList.toggle(`hide-${key}`, !visible);
  }
}

function clampMinutes(value, fallback) {
  const n = Math.round(Number(value));
  return Number.isFinite(n) && n >= 1 && n <= 180 ? n : fallback;
}

async function saveFromForm(event) {
  const s = await getSettings();

  if (event.target.name === "name") {
    const name = field("name").value.trim();
    if (name) await storage.set("name", name);
    return;
  }

  const next = {
    city: field("city").value.trim() || s.city,
    use24h: field("use24h").checked,
    show: Object.fromEntries(Object.keys(s.show).map((k) => [k, field(`show-${k}`).checked])),
    durations: Object.fromEntries(Object.keys(s.durations).map((k) =>
      [k, clampMinutes(field(`duration-${k}`).value, s.durations[k])])),
  };
  await storage.set("settings", next);
  applyVisibility(next.show);
}

function setOpen(open) {
  els.panel.hidden = !open;
  els.toggle.setAttribute("aria-expanded", String(open));
  if (open) fillForm();
}

export async function initSettings() {
  applyVisibility((await getSettings()).show);

  els.toggle.addEventListener("click", () => setOpen(els.panel.hidden));
  // "change" fires when a text field loses focus / Enter, and immediately for checkboxes.
  els.form.addEventListener("change", saveFromForm);
  els.form.addEventListener("submit", (e) => { e.preventDefault(); document.activeElement.blur(); });

  els.reset.addEventListener("click", async () => {
    if (!confirm("Delete your name, focus, streak, to-dos and settings from this browser?")) return;
    await storage.clearAll();
    location.reload();
  });

  document.addEventListener("keydown", (e) => { if (e.key === "Escape") setOpen(false); });
  document.addEventListener("click", (e) => {
    if (!els.panel.hidden && !els.panel.contains(e.target) && !els.toggle.contains(e.target)) setOpen(false);
  });

  storage.onChange("settings", async () => applyVisibility((await getSettings()).show));
}
