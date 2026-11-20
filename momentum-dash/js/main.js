// Entry point: start every widget. Each widget is independent, so one failing
// (e.g. no network for weather) never blocks the others.
import { initClock } from "./clock.js";
import { initBackground } from "./background.js";
import { initFocus } from "./focus.js";

const widgets = [initBackground, initClock, initFocus];

for (const init of widgets) {
  init().catch((error) => console.error(`[${init.name}]`, error));
}
