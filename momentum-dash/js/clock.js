// Clock + greeting ("Good evening, Michael") + first-run name prompt.
import * as storage from "./storage.js";

const els = {
  prompt: document.getElementById("name-prompt"),
  input: document.getElementById("name-input"),
  view: document.getElementById("clock-view"),
  clock: document.getElementById("clock"),
  greeting: document.getElementById("greeting-text"),
  name: document.getElementById("greeting-name"),
};

function greetingFor(hour) {
  if (hour >= 5 && hour < 12) return "Good morning";
  if (hour >= 12 && hour < 18) return "Good afternoon";
  if (hour >= 18 && hour < 22) return "Good evening";
  return "Good night";
}

function formatTime(date, use24h) {
  const minutes = String(date.getMinutes()).padStart(2, "0");
  if (use24h) return `${String(date.getHours()).padStart(2, "0")}:${minutes}`;
  const hours = date.getHours() % 12 || 12;
  return `${hours}:${minutes}`;
}

let use24h = true;

function tick() {
  const now = new Date();
  els.clock.textContent = formatTime(now, use24h);
  els.clock.dateTime = now.toISOString();
  els.greeting.textContent = `${greetingFor(now.getHours())}, `;
}

function showClock(name) {
  els.name.textContent = name;
  els.prompt.hidden = true;
  els.view.hidden = false;
  els.view.classList.add("fade-in");
  tick();
}

function askForName() {
  els.view.hidden = true;
  els.prompt.hidden = false;
  els.prompt.classList.add("fade-in");
  els.input.focus();
  els.prompt.addEventListener("submit", async (event) => {
    event.preventDefault();
    const name = els.input.value.trim();
    if (!name) return;
    await storage.set("name", name);
    showClock(name);
  }, { once: false });
}

// Double-click the name to edit it in place; Enter saves, Escape cancels.
function enableNameEditing() {
  els.name.addEventListener("dblclick", () => {
    els.name.contentEditable = "true";
    els.name.focus();
    document.getSelection().selectAllChildren(els.name);
  });
  els.name.addEventListener("keydown", async (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      els.name.blur();
    } else if (event.key === "Escape") {
      els.name.textContent = await storage.get("name", "");
      els.name.blur();
    }
  });
  els.name.addEventListener("blur", async () => {
    els.name.contentEditable = "false";
    const name = els.name.textContent.trim();
    if (name) await storage.set("name", name);
    else els.name.textContent = await storage.get("name", "");
  });
}

export async function initClock() {
  use24h = (await storage.get("settings", {})).use24h ?? true;
  const name = await storage.get("name");
  if (name) showClock(name);
  else askForName();

  enableNameEditing();
  // Update on the next full second, then every second (cheap, keeps the minute change exact).
  setTimeout(() => { tick(); setInterval(tick, 1000); }, 1000 - (Date.now() % 1000));
}
