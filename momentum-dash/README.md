# Verdant Tab — a Momentum Dash replica

A Chrome extension that replaces the new-tab page with a calm personal dashboard: a daily nature photo, a clock with a personal greeting, your **main focus for the day**, a **Pomodoro timer**, a **focus streak**, the weather, a quote and a small to-do list. Minimal design in dark, silver and dark green.

![Verdant Tab screenshot](docs/screenshot.png)

## Purpose

Inspired by the [Momentum](https://momentumdash.com/) extension: every new tab reminds you what you want to get done today instead of opening on a blank page.

The extra idea in my version is a small **focus loop**:

1. **Set** one main focus for the day.
2. **Work** on it in Pomodoro rounds (25 min focus / 5 min break / 15 min long break after 4 rounds). The rounds completed today are shown next to the focus.
3. **Tick it off** to keep your **streak** going: the number of days in a row you completed your focus.

| Feature | What it does |
|---|---|
| Photo of the day | One Unsplash photo per day (dark forest / mountain mood) with photographer credit; bundled photos as an offline fallback |
| Clock + greeting | "Good evening, Michael." Asks for your name on first use; double-click the name to change it |
| Daily focus | "What is your main focus for today?" Resets every day |
| Focus streak | +1 for every consecutive day you complete your focus; shows your best streak on hover |
| Pomodoro timer | Ring timer, the same in every open tab, countdown in the tab title, chime at the end |
| Weather | Current temperature and conditions for your city (click the city to change it) |
| Quote | A short quote of the day; the author appears on hover |
| To-dos | Pop-up list: add, tick, delete, clear completed |
| Settings | Name, city, 12/24-hour clock, show or hide widgets, Pomodoro lengths, reset all data |

## Data collection

| Data | Source | How |
|---|---|---|
| Background photo | [Unsplash API](https://unsplash.com/documentation) `GET /photos/random` | `fetch` with the user's own Access Key, **once per day**. As the [Unsplash guidelines](https://help.unsplash.com/en/articles/2511245-unsplash-api-guidelines) require, the image is hotlinked, the photographer is credited with links, and the photo's `download_location` is called |
| Fallback photos | 5 Unsplash photos bundled in `assets/fallback/` | Downloaded once with `tools/fetch_fallback_photos.py`; credits in `assets/fallback/credits.json` |
| Weather | [Open-Meteo](https://open-meteo.com/) (free, no key) | The geocoding API turns the city name into coordinates, then the forecast API returns the current temperature and weather code. Fetched at most every 30 min |
| Quotes | Local file `data/quotes.json` (32 quotes) | Read with `fetch`; quote = day of the year modulo the number of quotes |
| Name, focus, to-dos, settings | The user | Typed into the page |

The only data that leaves the browser is the **city name** (sent to Open-Meteo) and the Unsplash request (search words + your key). Nothing is sent to any server of mine; there is none.

## Data persistence

Everything is stored **locally in the browser** with `chrome.storage.local`. There is no account and no server, so the data stays on this computer.

| Key | Content | Why it is stored |
|---|---|---|
| `name` | Your first name | Greeting |
| `settings` | City, 12/24h, visible widgets, Pomodoro minutes | Preferences survive restarts |
| `focus` | `{ date, text, done }` | Today's focus; ignored when `date` is not today, which is how it resets daily |
| `streak` | `{ count, lastDoneDate, best, previous }` | Streak continues only if `lastDoneDate` is yesterday; `previous` allows undo |
| `pomodoro` | `{ mode, status, endsAt, remaining, round }` | The timer stores **when it ends**, not a countdown, so every tab shows the same time and closing a tab loses nothing |
| `pomodoroLog` | `{ date, count }` | Focus rounds completed today |
| `todos` | `[{ id, text, done }]` | To-do list |
| `background` | `{ date, photo }` | Today's photo, so new tabs don't call the API again (Unsplash allows 50 requests/hour) |
| `weather` | `{ query, place, current, fetchedAt }` | 30-minute cache, plus last known weather when offline |

Why `chrome.storage.local` and not a database: the data is small, personal and only needed in this browser. All open tabs are notified when a value changes (`chrome.storage.onChanged`), which keeps the focus, timer and settings in sync across tabs.

**Settings → Reset all data** deletes all of it.

## User interaction

1. Open a new tab. The first time, type your name and press **Enter**.
2. Type your **main focus** for today and press **Enter**. Tick the circle when it's done to grow your streak; hover and click **×** to clear it.
3. **Pomodoro** (top left): **Start / Pause**, **↺** restarts the current phase, **⏭** skips to the next one. When a phase ends you hear a chime and the next phase waits for you to press Start.
4. **Weather** (top right): click the city name, type another city, press **Enter**.
5. **Todo** (bottom right): add items, tick them, delete them, **Clear completed**. The green badge counts open items.
6. **⚙︎ Settings** (bottom right): every change is saved immediately. **Escape** or a click outside closes the panels.
7. Hover the quote to see the author; click the photo credit to open the photo on Unsplash.

## Setup

**Requirements:** Google Chrome (or another Chromium browser such as Edge or Brave). No build step and no dependencies: the extension is plain HTML, CSS and JavaScript (ES modules).

1. **Get the code**
   ```bash
   git clone https://github.com/mchlkan/APAIF_Assignment.git
   cd APAIF_Assignment/momentum-dash
   ```
2. **Optional: add an Unsplash key** for a new photo every day. Without a key the extension works and rotates the bundled photos.
   - Create a free app at [unsplash.com/developers](https://unsplash.com/developers) → *New Application* and copy the **Access Key** (never the Secret Key).
   - Copy the config template and paste the key:
     ```bash
     cp config.example.js config.js
     ```
     `config.js` is listed in `.gitignore`, so the key is never committed.
3. **Load the extension:** open `chrome://extensions`, switch on **Developer mode** (top right), click **Load unpacked** and select the `momentum-dash` folder.
4. **Open a new tab.** If Chrome asks whether to keep the changed new-tab page, choose **Keep it**.
5. After changing code, click the **reload** icon on the extension card in `chrome://extensions`.

**Developer tools (optional, Python 3, standard library only):**

| Script | Purpose |
|---|---|
| `python tools/fetch_fallback_photos.py` | Re-download the bundled fallback photos (needs `config.js` or an `UNSPLASH_ACCESS_KEY` environment variable) |
| `python tools/make_icons.py` | Regenerate the extension icons |
| `python -m http.server 5173` | Preview the page in a normal browser tab at `http://localhost:5173`; the code falls back to `localStorage` when `chrome.storage` is not available |

**Project structure**

```
momentum-dash/
├── manifest.json          # Chrome extension config (Manifest V3): overrides the new tab, only "storage" permission
├── index.html             # page layout
├── styles.css             # design tokens + all styles
├── config.example.js      # template for the optional Unsplash key (copy to config.js)
├── js/
│   ├── main.js            # starts every widget independently (one failing never blocks the others)
│   ├── storage.js         # chrome.storage wrapper with localStorage fallback, change listeners, date helpers
│   ├── background.js      # photo of the day, cache, fallback, attribution
│   ├── clock.js           # clock, greeting, name
│   ├── focus.js           # daily focus + streak logic
│   ├── pomodoro.js        # timer state machine
│   ├── weather.js         # Open-Meteo geocoding + current weather
│   ├── quote.js           # quote of the day
│   ├── todos.js           # to-do list
│   └── settings.js        # settings panel + defaults
├── data/quotes.json
├── assets/fallback/       # 5 bundled photos + credits.json
├── icons/                 # 16/48/128 px icons
├── tools/                 # developer scripts (not used by the extension at runtime)
└── docs/screenshot.png
```

## Learning

- **A Chrome extension is just a folder.** `manifest.json` tells Chrome what the extension does. Overriding the new-tab page is one line (`chrome_url_overrides`), and the only permission needed is `storage`. I also learned that fewer permissions is better, both for users and for security.
- **`.env` files don't work here.** I wanted to keep the Unsplash key in a `.env` file like in Python projects. A browser extension has no server and no build step, so nothing would read that file. The equivalent is a gitignored `config.js` plus a committed `config.example.js`. I also learned that the Unsplash *Access Key* is meant to be used client-side, while the *Secret Key* must never be shipped.
- **Store when something ends, not how much time is left.** My first idea for the Pomodoro timer was a countdown. Storing the end timestamp instead means every tab can calculate the remaining time itself, so the timer survives closing the tab and stays identical across tabs.
- **Challenge: a bug that only existed outside the extension.** To preview the page in a normal browser I wrote a `localStorage` fallback. While testing the Pomodoro, the "pomodoros today" counter didn't update, although the timer worked. The cause: `chrome.storage` notifies the *same* tab about changes, but the browser's `storage` event only notifies *other* tabs. I fixed it by notifying same-tab listeners in `storage.js`, so the preview behaves like the real extension.
- **Daily logic needs careful date handling.** Focus reset and streaks compare dates as `YYYY-MM-DD` in local time, built from calendar fields so daylight-saving days can't skip or repeat a day. Keeping the streak logic in small pure functions let me test edge cases (continue, double tick, undo, missed day) directly in the browser console.

## Limitations and assistance

**Limitations**

- **The chime only plays in the tab where you pressed Start.** Browsers block sound until the user has interacted with that page. There are no system notifications: those would need a background service worker with `chrome.alarms` and `chrome.notifications`, which I left out to keep the extension simple.
- **A finished phase is processed by the next visible tab.** If no new tab is visible when a phase ends, the switch to the break happens when you next look at one.
- **Without `config.js`, Chrome logs one "file not found" message** in the console when the extension checks for the optional key. It is caught and the fallback photos are used.
- **The Unsplash key is readable by anyone you give your copy to.** Access Keys are designed for client-side use, but don't share a copy that contains your `config.js`.
- **Weather** is in °C only, and the city search uses the first match (e.g. "Paris" → Paris, France).
- **No automated test suite.** I tested manually in Chrome and in a local preview, and checked the streak and Pomodoro rules in the browser console.
- **Chrome only** (Chromium-based browsers); not published on the Chrome Web Store.

**Assistance and external sources**

- **AI:** I built this project with **Claude Code (Anthropic)** as a coding assistant. It explained the extension concepts, helped plan the milestones, wrote most of the code following my feature and design decisions, and tested each milestone in a preview browser. I reviewed and tried every milestone, asked for changes, and made all the Git commits myself.
- **Documentation:**
  - [Chrome Extensions (Manifest V3)](https://developer.chrome.com/docs/extensions)
  - [Unsplash API documentation](https://unsplash.com/documentation) and [API guidelines](https://help.unsplash.com/en/articles/2511245-unsplash-api-guidelines)
  - [Open-Meteo API docs](https://open-meteo.com/en/docs)
- **Photos:** from Unsplash under the [Unsplash License](https://unsplash.com/license). Photographers are credited in the page and in `assets/fallback/credits.json`.
- **Weather data:** [Open-Meteo.com](https://open-meteo.com/) (CC BY 4.0).
- **Inspiration:** [Momentum](https://momentumdash.com/). No code, text or images were copied from it; the name, design and code are my own.
- **Quotes:** short, attributed quotes, mostly by historical authors.
