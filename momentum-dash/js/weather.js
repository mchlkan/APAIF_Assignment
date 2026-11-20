// Current weather from Open-Meteo (free, no API key).
// 1. City name → coordinates via the Open-Meteo geocoding API (cached with the weather).
// 2. Coordinates → current temperature + weather code.
// Cached for 30 minutes so opening many tabs doesn't call the API every time.
// Click the city name to change it (Enter saves, Escape cancels).
import * as storage from "./storage.js";

const CACHE_MS = 30 * 60_000;
const DEFAULT_CITY = "Lisbon";

const els = {
  root: document.getElementById("weather"),
  temp: document.getElementById("weather-temp"),
  icon: document.getElementById("weather-icon"),
  city: document.getElementById("weather-city"),
  desc: document.getElementById("weather-desc"),
};

// WMO weather codes used by Open-Meteo → short description + monochrome symbol.
const CODES = [
  [[0], "Clear sky", "☀︎", "☾"],
  [[1, 2], "Partly cloudy", "☁︎", "☁︎"],
  [[3], "Overcast", "☁︎", "☁︎"],
  [[45, 48], "Fog", "≋", "≋"],
  [[51, 53, 55, 56, 57], "Drizzle", "☂︎", "☂︎"],
  [[61, 63, 65, 66, 67, 80, 81, 82], "Rain", "☂︎", "☂︎"],
  [[71, 73, 75, 77, 85, 86], "Snow", "❄︎", "❄︎"],
  [[95, 96, 99], "Thunderstorm", "ϟ", "ϟ"],
];

export function describe(code, isDay = true) {
  const match = CODES.find(([codes]) => codes.includes(code));
  if (!match) return { text: "Unknown", symbol: "·" };
  return { text: match[1], symbol: isDay ? match[2] : match[3] };
}

async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}

async function geocode(city) {
  const params = new URLSearchParams({ name: city, count: 1, language: "en", format: "json" });
  const data = await fetchJson(`https://geocoding-api.open-meteo.com/v1/search?${params}`);
  const place = data.results?.[0];
  if (!place) throw new Error("CITY_NOT_FOUND");
  return { name: place.name, country: place.country_code, latitude: place.latitude, longitude: place.longitude };
}

async function fetchWeather(place) {
  const params = new URLSearchParams({
    latitude: place.latitude,
    longitude: place.longitude,
    current: "temperature_2m,weather_code,is_day",
    timezone: "auto",
  });
  const data = await fetchJson(`https://api.open-meteo.com/v1/forecast?${params}`);
  return { temperature: data.current.temperature_2m, code: data.current.weather_code, isDay: data.current.is_day === 1 };
}

async function getCity() {
  return (await storage.get("settings", {})).city || DEFAULT_CITY;
}

async function load({ force = false } = {}) {
  const city = await getCity();
  const cached = await storage.get("weather");
  const fresh = cached && cached.query === city && Date.now() - cached.fetchedAt < CACHE_MS;
  if (fresh && !force) return render(cached);

  try {
    const place = cached?.query === city ? cached.place : await geocode(city);
    const current = await fetchWeather(place);
    const entry = { query: city, place, current, fetchedAt: Date.now() };
    await storage.set("weather", entry);
    render(entry);
  } catch (error) {
    if (error.message === "CITY_NOT_FOUND") return renderMessage(city, "City not found — click to change");
    if (cached?.query === city) return render(cached, { stale: true }); // offline → show last known
    renderMessage(city, "Weather unavailable");
  }
}

function render(entry, { stale = false } = {}) {
  const { text, symbol } = describe(entry.current.code, entry.current.isDay);
  els.temp.textContent = `${Math.round(entry.current.temperature)}°`;
  els.icon.textContent = symbol;
  els.city.textContent = entry.place.name;
  els.desc.textContent = stale ? `${text} · last update ${new Date(entry.fetchedAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}` : text;
  els.root.title = `${entry.place.name}, ${entry.place.country} · data by Open-Meteo.com`;
  els.root.hidden = false;
}

function renderMessage(city, message) {
  els.temp.textContent = "";
  els.icon.textContent = "";
  els.city.textContent = city;
  els.desc.textContent = message;
  els.root.hidden = false;
}

function enableCityEditing() {
  els.city.addEventListener("click", () => {
    if (els.city.isContentEditable) return;
    els.city.contentEditable = "true";
    els.city.focus();
    document.getSelection().selectAllChildren(els.city);
  });
  els.city.addEventListener("keydown", (event) => {
    if (event.key === "Enter") { event.preventDefault(); els.city.blur(); }
    if (event.key === "Escape") { els.city.dataset.cancel = "1"; els.city.blur(); }
  });
  els.city.addEventListener("blur", async () => {
    els.city.contentEditable = "false";
    const cancelled = els.city.dataset.cancel === "1";
    delete els.city.dataset.cancel;
    const city = els.city.textContent.trim();
    if (cancelled || !city || city === (await getCity())) return load();
    const settings = await storage.get("settings", {});
    await storage.set("settings", { ...settings, city });
    load({ force: true });
  });
}

export async function initWeather() {
  enableCityEditing();
  storage.onChange("weather", (entry) => entry && render(entry)); // other tabs
  await load();
  setInterval(load, CACHE_MS); // refresh while a tab stays open
}
