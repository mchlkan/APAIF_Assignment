// "Edit layout" mode, like rearranging apps on a phone home screen.
// Enter it from Settings → "Edit layout", or by pressing and holding on an empty part of the page.
// Widgets jiggle; drag them anywhere; "Done" (or Escape) saves; "Reset" puts everything back.
//
// Each widget keeps its normal place in the page layout and is only *shifted* with the CSS
// `translate` property. The shift is stored as a fraction of the window size, so a layout made
// on a big screen still roughly fits a smaller one.
// Stored data: layout = { [widgetId]: { fx, fy } }
import * as storage from "./storage.js";

const WIDGETS = {
  pomodoro: "pomodoro",
  weather: "weather",
  todos: "todo-panel",
  clock: "clock-view",
  quote: "quote",
};
const LONG_PRESS_MS = 600;

let layout = {};
let editing = false;
const bar = createEditBar();

const elementFor = (id) => document.getElementById(WIDGETS[id]);

// ---------- positioning ----------

// Keep at least part of every widget inside the window.
function clamp(el, x, y) {
  const current = currentOffset(el);
  const rect = el.getBoundingClientRect();
  const baseLeft = rect.left - current.x;
  const baseTop = rect.top - current.y;
  const margin = 8;
  const minX = margin - baseLeft;
  const maxX = innerWidth - margin - rect.width - baseLeft;
  const minY = margin - baseTop;
  const maxY = innerHeight - margin - rect.height - baseTop;
  return {
    x: Math.min(Math.max(x, Math.min(minX, maxX)), Math.max(minX, maxX)),
    y: Math.min(Math.max(y, Math.min(minY, maxY)), Math.max(minY, maxY)),
  };
}

function currentOffset(el) {
  const [x = "0", y = "0"] = (el.style.translate || "0px 0px").split(" ");
  return { x: parseFloat(x) || 0, y: parseFloat(y) || 0 };
}

function place(el, x, y) {
  el.style.translate = x || y ? `${Math.round(x)}px ${Math.round(y)}px` : "";
}

function applyLayout() {
  for (const id of Object.keys(WIDGETS)) {
    const el = elementFor(id);
    const saved = layout[id];
    if (!el) continue;
    if (!saved) { place(el, 0, 0); continue; }
    place(el, 0, 0); // measure from the natural position
    const { x, y } = clamp(el, saved.fx * innerWidth, saved.fy * innerHeight);
    place(el, x, y);
  }
}

// ---------- dragging ----------

function startDrag(event) {
  if (!editing) return;
  const el = event.currentTarget;
  event.preventDefault();
  el.setPointerCapture(event.pointerId);
  el.classList.add("dragging");
  const start = { px: event.clientX, py: event.clientY, ...currentOffset(el) };

  const move = (e) => {
    const { x, y } = clamp(el, start.x + e.clientX - start.px, start.y + e.clientY - start.py);
    place(el, x, y);
  };
  const end = () => {
    el.classList.remove("dragging");
    el.removeEventListener("pointermove", move);
    el.removeEventListener("pointerup", end);
    el.removeEventListener("pointercancel", end);
    const id = Object.keys(WIDGETS).find((key) => elementFor(key) === el);
    const { x, y } = currentOffset(el);
    layout[id] = { fx: x / innerWidth, fy: y / innerHeight };
  };
  el.addEventListener("pointermove", move);
  el.addEventListener("pointerup", end);
  el.addEventListener("pointercancel", end);
}

// ---------- edit mode ----------

function createEditBar() {
  const el = document.createElement("div");
  el.className = "edit-bar panel";
  el.hidden = true;
  el.innerHTML = `
    <span>Drag the widgets to move them</span>
    <button type="button" class="text-button" data-action="reset">Reset</button>
    <button type="button" class="pill-button" data-action="done">Done</button>`;
  document.body.append(el);
  el.querySelector("[data-action=done]").addEventListener("click", () => setEditing(false));
  el.querySelector("[data-action=reset]").addEventListener("click", () => {
    layout = {};
    applyLayout();
  });
  return el;
}

export function setEditing(on) {
  editing = on;
  document.body.classList.toggle("editing", on);
  bar.hidden = !on;
  if (!on) storage.set("layout", layout);
}

// Press and hold on an empty part of the page (not on a widget or button) to enter edit mode.
function enableLongPress() {
  let timer = null;
  let start = null;
  const cancel = () => { clearTimeout(timer); timer = null; };
  document.addEventListener("pointerdown", (e) => {
    if (editing || e.button !== 0) return;
    const onWidget = e.target.closest("[data-widget], button, input, a, .popover, .edit-bar, form");
    if (onWidget) return;
    start = { x: e.clientX, y: e.clientY };
    timer = setTimeout(() => setEditing(true), LONG_PRESS_MS);
  });
  document.addEventListener("pointermove", (e) => {
    if (timer && Math.hypot(e.clientX - start.x, e.clientY - start.y) > 8) cancel();
  });
  document.addEventListener("pointerup", cancel);
}

export async function initLayout() {
  layout = await storage.get("layout", {});
  for (const id of Object.keys(WIDGETS)) {
    const el = elementFor(id);
    if (!el) continue;
    el.dataset.widget = id;
    el.addEventListener("pointerdown", startDrag);
  }
  // Widgets fill in their content asynchronously (weather, quote…), so place them a moment later too.
  applyLayout();
  setTimeout(applyLayout, 800);
  addEventListener("resize", applyLayout);

  document.getElementById("settings-edit-layout")?.addEventListener("click", () => {
    document.getElementById("settings-panel").hidden = true;
    setEditing(true);
  });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && editing) setEditing(false); });
  enableLongPress();
  storage.onChange("layout", (next) => { if (!editing) { layout = next ?? {}; applyLayout(); } });
}
