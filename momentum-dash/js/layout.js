// Widget grid + "Edit layout" mode, like widgets on a phone home screen.
//
// The screen is divided into square slots (one unit, see --unit / --gap in styles.css).
// Every box has a size in whole slots (default: medium 2x1 = timer, weather; large 2x2 = game, to-dos),
// so boxes always line up. In edit mode the size can be changed with the handle in the bottom corner
// that faces the middle (boxes on the left grow to the right, boxes on the right grow to the left),
// within each box's limits (see WIDGETS). The clock in the middle blocks the slots behind it.
// Boxes never overlap: a box dropped on a taken slot moves to the nearest free one.
//
// Enter edit mode from Settings → "Edit layout", or press and hold on an empty part of the page.
// Boxes jiggle, empty slots appear; drag a box, "Tidy up" restores the symmetric default, "Done" saves.
//
// Positions are stored per side, so a box on the right stays on the right on a wider screen:
// Stored data: layout = { [widget]: { side: "l"|"r", col, row, w, h } }   (col counted from that side)
import * as storage from "./storage.js";

// Default size and allowed sizes (in slots) of every box.
const WIDGETS = {
  pomodoro: { id: "pomodoro", w: 2, h: 1, minW: 2, maxW: 3, minH: 1, maxH: 2 },
  weather: { id: "weather", w: 2, h: 1, minW: 1, maxW: 3, minH: 1, maxH: 2 },
  game: { id: "game-panel", w: 2, h: 2, minW: 2, maxW: 3, minH: 2, maxH: 3 },
  todos: { id: "todo-panel", w: 2, h: 2, minW: 1, maxW: 4, minH: 1, maxH: 4, minArea: 4 },
};
// Default ("Tidy up"): mirror-symmetric around the clock.
const DEFAULT_LAYOUT = {
  pomodoro: { side: "l", col: 0, row: 0 },
  game: { side: "l", col: 0, row: 1 },
  weather: { side: "r", col: 0, row: 0 },
  todos: { side: "r", col: 0, row: 1 },
};
const ORDER = ["pomodoro", "weather", "game", "todos"]; // who gets their slot first
const MARGIN = 20;
const LONG_PRESS_MS = 600;

let layout = {};
let editing = false;
let placedCells = {}; // widget → { col, row, w, h } where it is right now
const bar = createEditBar();
const slotLayer = document.createElement("div");
slotLayer.className = "grid-slots";
slotLayer.hidden = true;
document.body.prepend(slotLayer);

const elementFor = (key) => document.getElementById(WIDGETS[key].id);

// Is w x h an allowed size for this box?
function sizeAllowed(key, w, h) {
  const spec = WIDGETS[key];
  return w >= spec.minW && w <= spec.maxW && h >= spec.minH && h <= spec.maxH && w * h >= (spec.minArea ?? 1);
}

// Saved size if it is still allowed, otherwise the default size.
function sizeOf(key) {
  const saved = layout[key];
  if (saved?.w && saved?.h && sizeAllowed(key, saved.w, saved.h)) return { w: saved.w, h: saved.h };
  return { w: WIDGETS[key].w, h: WIDGETS[key].h };
}
const isShown = (el) => el.getClientRects().length > 0; // false when put away (display: none)

// ---------- grid geometry ----------

function cssPx(name) {
  return parseFloat(getComputedStyle(document.documentElement).getPropertyValue(name));
}

function geometry() {
  const unit = cssPx("--unit");
  const gap = cssPx("--gap");
  const pitch = unit + gap;
  const bottomBar = document.querySelector(".bottom-row").getBoundingClientRect().top;
  const cols = Math.max(2, Math.floor((innerWidth - 2 * MARGIN + gap) / pitch));
  const rows = Math.max(1, Math.floor((bottomBar - MARGIN - 8 + gap) / pitch));
  const left = (innerWidth - (cols * pitch - gap)) / 2; // grid centered horizontally
  return { unit, gap, pitch, cols, rows, left, top: MARGIN };
}

const cellX = (g, col) => g.left + col * g.pitch;
const cellY = (g, row) => g.top + row * g.pitch;

// Slots behind the clock / greeting / focus are not available.
function heroBlocked(g) {
  const hero = [...document.querySelector(".center").children].find((el) => !el.hidden);
  const r = hero?.getBoundingClientRect();
  const blocked = Array.from({ length: g.rows }, () => Array(g.cols).fill(false));
  if (!r || !r.width) return blocked;
  for (let row = 0; row < g.rows; row++) {
    for (let col = 0; col < g.cols; col++) {
      const x = cellX(g, col);
      const y = cellY(g, row);
      blocked[row][col] = x < r.right && r.left < x + g.unit && y < r.bottom && r.top < y + g.unit;
    }
  }
  return blocked;
}

const fits = (g, occ, col, row, w, h) => {
  if (col < 0 || row < 0 || col + w > g.cols || row + h > g.rows) return false;
  for (let r = row; r < row + h; r++) for (let c = col; c < col + w; c++) if (occ[r][c]) return false;
  return true;
};

function mark(occ, col, row, w, h) {
  for (let r = row; r < row + h; r++) for (let c = col; c < col + w; c++) if (occ[r]?.[c] !== undefined) occ[r][c] = true;
}

// Closest slot (by distance) where the box fits, or null if the screen is full.
function nearestFree(g, occ, col, row, w, h) {
  let best = null;
  let bestDistance = Infinity;
  for (let r = 0; r <= g.rows - h; r++) {
    for (let c = 0; c <= g.cols - w; c++) {
      const distance = (c - col) ** 2 + (r - row) ** 2;
      if (distance < bestDistance && fits(g, occ, c, r, w, h)) { best = { col: c, row: r }; bestDistance = distance; }
    }
  }
  return best;
}

// Side-relative position (stored) ↔ absolute column (on this screen).
const toCell = (g, spec, w) => ({ col: spec.side === "r" ? g.cols - w - spec.col : spec.col, row: spec.row });
function toSpec(g, col, row, w, h) {
  const fromRight = g.cols - w - col;
  return col <= fromRight ? { side: "l", col, row, w, h } : { side: "r", col: fromRight, row, w, h };
}

function setPosition(el, g, col, row) {
  el.style.left = `${cellX(g, col)}px`;
  el.style.top = `${cellY(g, row)}px`;
}

// Size in px from slots; data-w / data-h let the CSS adapt the content (see styles.css).
function setSize(el, g, w, h) {
  el.style.width = `${w * g.pitch - g.gap}px`;
  el.style.height = `${h * g.pitch - g.gap}px`;
  el.dataset.w = w;
  el.dataset.h = h;
}

// ---------- placing every box ----------

function applyLayout() {
  const g = geometry();
  const occ = heroBlocked(g);
  placedCells = {};
  for (const key of ORDER) {
    const el = elementFor(key);
    if (!el || !isShown(el)) continue;
    const { w, h } = sizeOf(key);
    const saved = layout[key]?.side ? layout[key] : DEFAULT_LAYOUT[key];
    let { col, row } = toCell(g, saved, w);
    if (!fits(g, occ, col, row, w, h)) {
      const free = nearestFree(g, occ, col, row, w, h);
      // Screen too small for every box: keep it as close as possible (may overlap).
      ({ col, row } = free ?? { col: Math.max(0, Math.min(col, g.cols - w)), row: Math.max(0, Math.min(row, g.rows - h)) });
    }
    setSize(el, g, w, h);
    setPosition(el, g, col, row);
    el.dataset.anchor = toSpec(g, col, row, w, h).side; // which side the box sticks to (handle faces the middle)
    mark(occ, col, row, w, h);
    placedCells[key] = { col, row, w, h };
    el.classList.add("placed");
  }
  if (editing) renderSlots(g);
}

function renderSlots(g) {
  const blocked = heroBlocked(g);
  const slots = [];
  for (let row = 0; row < g.rows; row++) {
    for (let col = 0; col < g.cols; col++) {
      if (blocked[row][col]) continue;
      const slot = document.createElement("div");
      slot.className = "grid-slot";
      slot.style.left = `${cellX(g, col)}px`;
      slot.style.top = `${cellY(g, row)}px`;
      slots.push(slot);
    }
  }
  slotLayer.replaceChildren(...slots);
}

// ---------- dragging ----------

// Slots taken by the clock and by every box except `key`.
function occupiedExcept(g, key) {
  const occ = heroBlocked(g);
  for (const [other, cell] of Object.entries(placedCells)) {
    if (other !== key) mark(occ, cell.col, cell.row, cell.w, cell.h);
  }
  return occ;
}

function landingOutline(g, w, h) {
  const target = document.createElement("div");
  target.className = "grid-target";
  target.style.width = `${w * g.pitch - g.gap}px`;
  target.style.height = `${h * g.pitch - g.gap}px`;
  slotLayer.append(target);
  return target;
}

function startDrag(event) {
  if (!editing) return;
  if (event.target.closest(".resize-handle")) return startResize(event);
  const el = event.currentTarget;
  const key = el.dataset.widget;
  const { w, h } = placedCells[key];
  event.preventDefault();
  el.setPointerCapture(event.pointerId);
  el.classList.add("dragging");

  const g = geometry();
  const occ = occupiedExcept(g, key);
  const startCell = placedCells[key];
  const grab = { x: event.clientX - el.offsetLeft, y: event.clientY - el.offsetTop };

  // Outline showing where the box will land (green = free, red = taken).
  const target = landingOutline(g, w, h);
  let cell = startCell;

  const move = (e) => {
    const x = Math.min(Math.max(e.clientX - grab.x, 0), innerWidth - el.offsetWidth);
    const y = Math.min(Math.max(e.clientY - grab.y, 0), innerHeight - el.offsetHeight);
    el.style.left = `${x}px`;
    el.style.top = `${y}px`;
    cell = {
      col: Math.min(Math.max(Math.round((x - g.left) / g.pitch), 0), g.cols - w),
      row: Math.min(Math.max(Math.round((y - g.top) / g.pitch), 0), Math.max(0, g.rows - h)),
    };
    target.style.left = `${cellX(g, cell.col)}px`;
    target.style.top = `${cellY(g, cell.row)}px`;
    target.classList.toggle("blocked", !fits(g, occ, cell.col, cell.row, w, h));
  };
  const end = () => {
    el.classList.remove("dragging");
    el.removeEventListener("pointermove", move);
    el.removeEventListener("pointerup", end);
    el.removeEventListener("pointercancel", end);
    target.remove();
    // Free slot → land there; taken → nearest free slot; no room at all → back to where it was.
    const landing = fits(g, occ, cell.col, cell.row, w, h) ? cell : (nearestFree(g, occ, cell.col, cell.row, w, h) ?? startCell);
    el.classList.add("snapping");
    setPosition(el, g, landing.col, landing.row);
    setTimeout(() => el.classList.remove("snapping"), 300);
    placedCells[key] = { col: landing.col, row: landing.row, w, h };
    layout[key] = toSpec(g, landing.col, landing.row, w, h);
  };
  el.addEventListener("pointermove", move);
  el.addEventListener("pointerup", end);
  el.addEventListener("pointercancel", end);
}

// ---------- resizing (handle in the bottom-right corner) ----------

function startResize(event) {
  const el = event.currentTarget;
  const key = el.dataset.widget;
  event.preventDefault();
  event.stopPropagation();
  el.setPointerCapture(event.pointerId);
  el.classList.add("resizing");

  const g = geometry();
  const occ = occupiedExcept(g, key);
  const start = placedCells[key];
  // Boxes on the left grow to the right; boxes on the right keep their right edge and grow to the left.
  const growsLeft = el.dataset.anchor === "r";
  const rightCol = start.col + start.w; // first column after the box
  const target = landingOutline(g, start.w, start.h);
  target.style.top = `${cellY(g, start.row)}px`;
  let next = { ...start };
  const valid = (n) => sizeAllowed(key, n.w, n.h) && fits(g, occ, n.col, n.row, n.w, n.h);

  const move = (e) => {
    // Size in slots under the pointer, kept within this box's limits.
    const spec = WIDGETS[key];
    const pulledW = growsLeft
      ? Math.round((cellX(g, rightCol) - g.gap - e.clientX + g.gap) / g.pitch)
      : Math.round((e.clientX - cellX(g, start.col) + g.gap) / g.pitch);
    const w = Math.min(Math.max(pulledW, spec.minW), spec.maxW);
    const h = Math.min(Math.max(Math.round((e.clientY - cellY(g, start.row) + g.gap) / g.pitch), spec.minH), spec.maxH);
    next = { col: growsLeft ? rightCol - w : start.col, row: start.row, w, h };
    target.style.left = `${cellX(g, next.col)}px`;
    target.style.width = `${w * g.pitch - g.gap}px`;
    target.style.height = `${h * g.pitch - g.gap}px`;
    target.classList.toggle("blocked", !valid(next)); // red: overlaps, off-grid or below the minimum
    setSize(el, g, w, h); // live preview: the content adapts while pulling
    setPosition(el, g, next.col, next.row);
  };
  const end = () => {
    el.classList.remove("resizing");
    el.removeEventListener("pointermove", move);
    el.removeEventListener("pointerup", end);
    el.removeEventListener("pointercancel", end);
    target.remove();
    const final = valid(next) ? next : start; // not allowed → back to the old size
    setSize(el, g, final.w, final.h);
    setPosition(el, g, final.col, final.row);
    placedCells[key] = { ...final };
    layout[key] = toSpec(g, final.col, final.row, final.w, final.h);
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
    <span>Drag boxes into free slots · pull the corner to resize</span>
    <button type="button" class="text-button" data-action="tidy">Tidy up</button>
    <button type="button" class="pill-button" data-action="done">Done</button>`;
  document.body.append(el);
  el.querySelector("[data-action=done]").addEventListener("click", () => setEditing(false));
  el.querySelector("[data-action=tidy]").addEventListener("click", () => {
    layout = {};
    applyLayout();
  });
  return el;
}

export function setEditing(on) {
  editing = on;
  document.body.classList.toggle("editing", on);
  bar.hidden = !on;
  slotLayer.hidden = !on;
  if (on) renderSlots(geometry());
  else storage.set("layout", layout);
}

// Press and hold on an empty part of the page (not on a box or button) to enter edit mode.
function enableLongPress() {
  let timer = null;
  let start = null;
  const cancel = () => { clearTimeout(timer); timer = null; };
  document.addEventListener("pointerdown", (e) => {
    if (editing || e.button !== 0) return;
    if (e.target.closest("[data-widget], button, input, a, .popover, .edit-bar, form")) return;
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
  for (const key of Object.keys(WIDGETS)) {
    const el = elementFor(key);
    el.dataset.widget = key;
    el.addEventListener("pointerdown", startDrag);
    const handle = document.createElement("span");
    handle.className = "resize-handle";
    handle.title = "Pull to resize";
    el.append(handle);
  }
  applyLayout();

  // Re-place boxes right away (same frame, so nothing flashes or jumps) when:
  document.addEventListener("widgets:visibility", applyLayout); // a box is shown / put away
  addEventListener("resize", applyLayout);                      // the window changes size
  const heroObserver = new ResizeObserver(applyLayout);         // the clock area changes size
  document.querySelectorAll(".center > *").forEach((el) => heroObserver.observe(el));

  document.getElementById("settings-edit-layout")?.addEventListener("click", () => {
    document.getElementById("settings-panel").hidden = true;
    setEditing(true);
  });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && editing) setEditing(false); });
  enableLongPress();
  storage.onChange("layout", (next) => { if (!editing) { layout = next ?? {}; applyLayout(); } });
}
