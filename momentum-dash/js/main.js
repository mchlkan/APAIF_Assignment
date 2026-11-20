// Entry point: start every widget. Each widget is independent, so one failing
// (e.g. no network for weather) never blocks the others.
import { initClock } from "./clock.js";
import { initBackground } from "./background.js";
import { initFocus } from "./focus.js";
import { initPomodoro } from "./pomodoro.js";
import { initQuote } from "./quote.js";
import { initWeather } from "./weather.js";

const widgets = [initBackground, initClock, initFocus, initPomodoro, initQuote, initWeather];

for (const init of widgets) {
  init().catch((error) => console.error(`[${init.name}]`, error));
}
