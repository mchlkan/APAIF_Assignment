// Photo of the day.
// 1. If today's photo is cached → show it (no API call).
// 2. Else, if an Unsplash key is configured → fetch one random photo, cache it for the day.
// 3. Otherwise (no key, offline, rate limit, error) → show a bundled fallback photo.
import * as storage from "./storage.js";

const SEARCH_QUERY = "dark forest mountains mist";
const UTM = "utm_source=verdant_tab&utm_medium=referral"; // required by Unsplash's attribution guidelines

const els = {
  background: document.getElementById("background"),
  credit: document.getElementById("photo-credit"),
};

// config.js is optional and gitignored, so load it dynamically and tolerate it missing.
async function loadAccessKey() {
  try {
    const { UNSPLASH_ACCESS_KEY: key } = await import("../config.js");
    return key && !key.startsWith("YOUR_") ? key : null;
  } catch {
    return null;
  }
}

function withUtm(url) {
  return `${url}${url.includes("?") ? "&" : "?"}${UTM}`;
}

async function fetchUnsplashPhoto(key) {
  const params = new URLSearchParams({ query: SEARCH_QUERY, orientation: "landscape", content_filter: "high" });
  const headers = { Authorization: `Client-ID ${key}`, "Accept-Version": "v1" };
  const response = await fetch(`https://api.unsplash.com/photos/random?${params}`, { headers });
  if (!response.ok) throw new Error(`Unsplash responded ${response.status}`);
  const photo = await response.json();

  // Unsplash asks apps to "trigger a download" when a photo is used; fire and forget.
  fetch(photo.links.download_location, { headers }).catch(() => {});

  // Request a size that fits the screen instead of the multi-MB original.
  const width = Math.min(2560, Math.round(screen.width * devicePixelRatio));
  return {
    url: `${photo.urls.raw}&w=${width}&q=80&fm=jpg&fit=max`,
    photographer: photo.user.name,
    profileUrl: withUtm(photo.user.links.html),
    photoUrl: withUtm(photo.links.html),
    source: "unsplash",
  };
}

async function pickFallbackPhoto() {
  const response = await fetch("assets/fallback/credits.json");
  const photos = await response.json();
  if (!photos.length) return null;
  // Same photo all day, different photo each day.
  const dayOfYear = Math.floor((Date.now() - new Date(new Date().getFullYear(), 0, 0)) / 86_400_000);
  const photo = photos[dayOfYear % photos.length];
  return {
    url: `assets/fallback/${photo.file}`,
    photographer: photo.photographer,
    profileUrl: withUtm(photo.profileUrl),
    photoUrl: withUtm(photo.photoUrl),
    source: "fallback",
  };
}

// Load the image off-screen first, so it fades in fully instead of painting line by line.
function preload(url) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = resolve;
    img.onerror = () => reject(new Error(`Could not load ${url}`));
    img.src = url;
  });
}

function link(href, text) {
  const a = document.createElement("a");
  a.href = href;
  a.textContent = text;
  a.target = "_blank";
  a.rel = "noopener noreferrer";
  return a;
}

function show(photo) {
  els.background.style.opacity = "0";
  requestAnimationFrame(() => {
    els.background.style.backgroundImage = `url("${photo.url}")`;
    els.background.style.opacity = "1";
  });
  els.credit.replaceChildren(
    "Photo by ", link(photo.profileUrl, photo.photographer),
    " on ", link(withUtm("https://unsplash.com/"), "Unsplash"),
  );
  els.credit.hidden = false;
}

async function showFallback() {
  const photo = await pickFallbackPhoto().catch(() => null);
  if (!photo) return; // no bundled photos either → keep the CSS gradient
  await preload(photo.url);
  show(photo);
}

export async function initBackground() {
  const today = storage.todayKey();
  const cached = await storage.get("background");

  if (cached?.date === today) {
    try {
      await preload(cached.photo.url);
      show(cached.photo);
      return;
    } catch {
      // cached URL broken (e.g. offline) → fall through
    }
  }

  const key = await loadAccessKey();
  if (key) {
    try {
      const photo = await fetchUnsplashPhoto(key);
      await preload(photo.url);
      await storage.set("background", { date: today, photo });
      show(photo);
      return;
    } catch (error) {
      console.warn("Unsplash photo unavailable, using fallback:", error.message);
    }
  }

  await showFallback();
}
