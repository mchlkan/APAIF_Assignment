# Books to Scrape

> Work in progress: this README is filled in section by section during the build (see [docs/plan.md](docs/plan.md)).

Scrapes all 1,000 books from [books.toscrape.com](https://books.toscrape.com), a sandbox site made for
scraping practice, stores them in a Supabase (Postgres) database, and lets you browse, filter and
analyse them in a Streamlit app.

## Purpose
_To do (docs task)._

## Data collection
`scraper.py` crawls [books.toscrape.com](https://books.toscrape.com) with `requests` and parses the pages with
BeautifulSoup (`parse.py`, pure functions that are tested on saved HTML pages).

- **Crawl:** the 50 listing pages (`catalogue/page-1.html` … `page-50.html`, 20 books each) are followed through
  their "next" link. Each book's product page gives title, UPC, prices (incl./excl. tax, tax), stock text
  ("In stock (22 available)"), star rating (a CSS class such as `star-rating Three`), description, category
  (3rd breadcrumb item) and cover image URL. Relative links are made absolute with `urljoin`.
- **Incremental by default:** all listing pages are crawled, but a product page is only fetched if its URL is not
  in the database yet, so a repeated run costs ~50 requests instead of ~1,050. `--full` refetches everything
  and updates the stored rows. `--limit N` stops after N books (handy for a first test); `--delay` sets the pause.
- **Politeness:** a pause before every request (0.2 s by default), a 10 s timeout, 3 attempts with 2 s / 4 s backoff
  on network errors and 5xx answers, and a generic User-Agent (`APAIF-coursework-scraper/1.0 (educational)`).
- **Errors:** a book that fails is printed and counted in `errors`; the run continues.
- **Encoding trap:** `requests` guesses ISO-8859-1 for this site and would turn "£" into "Â£", so the parser
  receives the response bytes and BeautifulSoup reads the page's own UTF-8 declaration.
- Not stored: "Number of reviews" (always 0 on this site).

```bash
conda run -n apaif python scraper.py --limit 40   # test run
conda run -n apaif python scraper.py              # incremental
conda run -n apaif python scraper.py --full       # update everything
```

## Data persistence
Data lives in a Supabase (Postgres) project; the tables are created by [schema.sql](schema.sql).

| Table | Content |
|---|---|
| `categories` | `id`, `name` (unique): 50 rows. A separate table because the names repeat 1,000 times and the app needs the list. |
| `books` | `upc` (primary key, the site's own code), title, `category_id`, prices, stock, rating (1–5, checked by the database), description, image and product URL, `first_seen`, `last_scraped`. |
| `scrape_runs` | One row per run: mode, pages visited, new / updated / skipped books, errors, status (`running`, `ok`, `failed`). The app shows the latest one. |

- **Upserts:** books are written with `upsert(..., on_conflict="upc")`, once per listing page, so re-running never
  creates duplicates. `first_seen` is never sent, so the database default keeps the original date while
  `last_scraped` moves forward. New vs. updated is decided by comparing with the URLs already stored.
- **Supabase limit:** a request returns at most 1,000 rows, so the stored URLs are read in pages with `.range()`.
- **Keys and Row Level Security:** RLS is on for all tables with one policy, "anyone may SELECT". There is no
  insert/update policy, so the *publishable* key (used by the app) can only read. The *secret* key bypasses RLS and
  is used only by the scraper. Both live in `.env`, which is gitignored; `.env.example` holds placeholders.
- `db.py` write helpers take the client as an argument, so `tests/test_db.py` runs them against a fake client
  without touching the real database.

## User interaction
Start the app from inside `books-to-scrape/`: Streamlit reads the theme from `.streamlit/config.toml` in the folder
where it is started. It needs the Supabase keys in `.env`, or sample mode:

```bash
cd books-to-scrape
conda run -n apaif streamlit run app.py
BOOKS_SOURCE=sample conda run -n apaif streamlit run app.py   # no database needed
```

`BOOKS_SOURCE=sample` shows 60 synthetic books from `tests/fixtures/sample_books.csv` (no covers, so cards show a book
icon), so anyone can try the interface without a Supabase project. The app only ever uses the read-only publishable key.

The app looks like a small bookshop: a warm paper theme with a deep green accent and serif headings, set only in
`.streamlit/config.toml` (no custom CSS). Under the title, four tiles show books, median price, copies in stock and the
share of 5-star books. A switch below them chooses between two views, next to a **Surprise me** button that opens a
random book from the current selection:

- **Sidebar filters** (apply to the Shelf view): title search, categories, price range, minimum stars (Any, 2+ ... 5) and
  a sort order. There is no "in stock only" filter: every scraped book is in stock, so it would change nothing.
- **Shelf**: the matching books as a grid of cards (cover, title, rating, price, category), 24 per page with a page
  control. Every card is built from fixed-height zones, so covers, titles and buttons line up across a row.
  "x of y books" shows how many match. **Details** opens a dialog with the bigger cover, full description,
  prices with and without tax, copies available and a link to the book's page on the source site. A Grid/Table switch
  falls back to a plain table.
- **Insights** (the extra feature): short written findings computed from the data, each with a chart: the rating
  distribution, price bands of £5, whether rating drives price, and the average price per category (categories with at
  least 10 books; the cheapest and priciest are coloured, the site's placeholder categories greyed). Two shelves show
  the cheapest 5-star books and the books with the most copies in stock. These always describe the whole catalogue,
  not the filtered selection.
- **Footer**: the data source and, for Supabase, the date and mode of the latest scrape run.

Messages instead of crashes: missing or wrong keys (with the hint to use sample mode), an unreachable database, an
empty database ("run the scraper first") and a filter combination that matches nothing.

How it works: `queries.py` loads all books once (paged with `.range()`, because Supabase returns at most 1,000 rows per
request; the category name is joined in) and holds the filter and aggregate functions as plain pandas code, which
`tests/test_queries.py` checks offline. `app.py` only draws the interface (small functions: header, filters, cards, dialog, insights) and caches the loaded data for 10 minutes.

## Setup
_To do (docs task): fresh clone → conda env → `pip install -r requirements.txt` → Supabase project +
`schema.sql` → `.env` → scrape → run the app. Sample mode without Supabase._

## Learning
_To do: written by Michael at the end._

## Limitations and assistance
_To do (docs task): known limitations, AI tools used (including the multi-agent build setup)._

## Screenshot
_To do._
