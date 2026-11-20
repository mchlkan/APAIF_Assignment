// Entry point: start every widget. Each widget is independent, so one failing
// (e.g. no network for weather) never blocks the others.
import { initClock } from "./clock.js";
import { initBackground } from "./background.js";

const widgets = [initBackground, initClock];

for (const init of widgets) {
  init().catch((error) => console.error(`[${init.name}]`, error));
}
