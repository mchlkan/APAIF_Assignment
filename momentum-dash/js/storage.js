// Small key-value wrapper around chrome.storage.local.
// When the page runs outside the extension (e.g. a local dev server for previewing),
// chrome.storage does not exist, so we fall back to localStorage with the same API.

const chromeStore = globalThis.chrome?.storage?.local;

export async function get(key, fallback = null) {
  if (chromeStore) {
    const result = await chromeStore.get(key);
    return result[key] ?? fallback;
  }
  const raw = localStorage.getItem(key);
  return raw === null ? fallback : JSON.parse(raw);
}

export async function set(key, value) {
  if (chromeStore) {
    await chromeStore.set({ [key]: value });
    return;
  }
  localStorage.setItem(key, JSON.stringify(value));
}

// Call `callback(newValue)` whenever `key` changes in another tab.
export function onChange(key, callback) {
  if (chromeStore) {
    chrome.storage.onChanged.addListener((changes, area) => {
      if (area === "local" && key in changes) callback(changes[key].newValue);
    });
    return;
  }
  window.addEventListener("storage", (event) => {
    if (event.key === key) callback(event.newValue === null ? null : JSON.parse(event.newValue));
  });
}

// "YYYY-MM-DD" in the user's local time zone (used for daily resets and streaks).
export function todayKey(date = new Date()) {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}
