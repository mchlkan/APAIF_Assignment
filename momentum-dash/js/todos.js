// To-do list in a panel under the weather. Showing / putting it away is handled in settings.js.
// Stored data: todos = [{ id, text, done }]
import * as storage from "./storage.js";

const els = {
  count: document.getElementById("todo-count"),
  list: document.getElementById("todo-list"),
  empty: document.getElementById("todo-empty"),
  form: document.getElementById("todo-form"),
  input: document.getElementById("todo-input"),
  clear: document.getElementById("todo-clear"),
};

let todos = [];

async function save(next) {
  todos = next;
  await storage.set("todos", next);
  render();
}

function itemElement(todo) {
  const li = document.createElement("li");
  li.className = "todo-item";
  li.classList.toggle("is-done", todo.done);

  const checkbox = document.createElement("input");
  checkbox.type = "checkbox";
  checkbox.className = "focus-check todo-check";
  checkbox.checked = todo.done;
  checkbox.setAttribute("aria-label", `Mark "${todo.text}" as done`);
  checkbox.addEventListener("change", () =>
    save(todos.map((t) => (t.id === todo.id ? { ...t, done: checkbox.checked } : t))));

  const text = document.createElement("span");
  text.className = "todo-text";
  text.textContent = todo.text; // textContent (not innerHTML) so typed HTML is never executed

  const remove = document.createElement("button");
  remove.type = "button";
  remove.className = "icon-button";
  remove.textContent = "×";
  remove.setAttribute("aria-label", `Delete "${todo.text}"`);
  remove.addEventListener("click", () => save(todos.filter((t) => t.id !== todo.id)));

  li.append(checkbox, text, remove);
  return li;
}

function render() {
  els.list.replaceChildren(...todos.map(itemElement));
  const open = todos.filter((t) => !t.done).length;
  els.count.textContent = open ? String(open) : "";
  els.count.hidden = open === 0;
  els.empty.hidden = todos.length > 0;
  els.clear.hidden = !todos.some((t) => t.done);
}

export async function initTodos() {
  todos = await storage.get("todos", []);
  render();
  els.form.addEventListener("submit", (event) => {
    event.preventDefault();
    const text = els.input.value.trim();
    if (!text) return;
    els.input.value = "";
    save([...todos, { id: crypto.randomUUID(), text, done: false }]);
  });
  els.clear.addEventListener("click", () => save(todos.filter((t) => !t.done)));

  storage.onChange("todos", (next) => { todos = next ?? []; render(); });
}
