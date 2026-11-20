// Quote of the day from a local JSON file (no API, works offline).
// The same quote shows all day; the next day moves to the next one.
import { dayOfYear } from "./storage.js";

const els = {
  quote: document.getElementById("quote"),
  text: document.getElementById("quote-text"),
  author: document.getElementById("quote-author"),
};

export async function initQuote() {
  const quotes = await (await fetch("data/quotes.json")).json();
  const quote = quotes[dayOfYear() % quotes.length];
  els.text.textContent = `“${quote.text}”`;
  els.author.textContent = `— ${quote.author}`;
  els.quote.hidden = false;
}
