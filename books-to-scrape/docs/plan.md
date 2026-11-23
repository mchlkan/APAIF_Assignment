# Books to Scrape: build plan

This plan is also the briefing for the coding agents, so each task is written to stand on its own.
It lives in the repo on purpose: it records the decisions made before the build.

## Goal
Scrape all books from <https://books.toscrape.com> (a sandbox site built for scraping practice),
store them in **Supabase** (hosted Postgres, as used in the lecture), and let the user explore them in a Streamlit app.
Aim: a small, polished MVP. One cherry on top: an **Insights** tab with charts.

## Stack and why
| Part | Choice | Why |
|---|---|---|
| Fetching | `requests` (one `Session`, timeout, retries) | Simple and synchronous. 1,050 pages don't need async. |
| Parsing | `beautifulsoup4` with the built-in `html.parser` | No compiled dependency like lxml, so it installs anywhere |
| Storage | Supabase (Postgres) via the `supabase` Python client | Same as the lecture; a real cloud database with access rules |
| Config | `python-dotenv`, `.env` (gitignored) + committed `.env.example` | Keys never land in Git |
| Interface | `streamlit` + `pandas` | A filterable table and charts in a few lines of Python |
| Tests | `pytest`, offline (saved HTML, sample CSV, fake client) | Tests never touch the network or the real database |

Run everything with `conda run -n apaif ...`. Install packages with
`conda run -n apaif pip install -r books-to-scrape/requirements.txt`.

## Keys and security
- `.env` holds `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY` (read-only use) and `SUPABASE_SECRET_KEY` (writes).
- **Row Level Security (RLS)** is on for every table. There is one policy: anyone may `SELECT`. There are no
  insert/update policies, so the publishable key can only read. The secret key bypasses RLS and is used **only by the scraper**.
- The app uses only the publishable key. Even if that key leaks, nobody can change the data.
- `.env` is gitignored (root `.gitignore` already has `.env` / `!.env.example`). Agents never print key values.
- Worktrees don't contain gitignored files: a stream that needs keys copies `books-to-scrape/.env` from the main checkout.

## Folder layout
```
books-to-scrape/
  README.md            all required sections (skeleton from task 0)
  AUDIT.md             after the audit loop
  requirements.txt
  .env.example         placeholders only
  schema.sql           tables + RLS, run once in the Supabase SQL editor (task 0, shared, do not change without asking)
  db.py                client creation (task 0), write functions (stream A)
  parse.py             pure HTML -> dict functions (stream A)
  scraper.py           CLI crawler (stream A)
  queries.py           load data into pandas + filter/aggregate functions (stream B)
  app.py               Streamlit app (stream B)
  pytest.ini           pythonpath = . so tests can `import db, parse, queries`
  tools/make_sample_data.py  writes tests/fixtures/sample_books.csv: 60 synthetic books (task 0)
                       Its columns are the contract for queries.load_books(): upc, title, category, price,
                       price_excl_tax, tax, in_stock, stock_count, rating, description, image_url, product_url,
                       first_seen, last_scraped (category = name, not id)
  tests/               test_parse.py, test_db.py (A), test_queries.py (B), fixtures/
  docs/                plan.md, screenshots
```

## Site facts (checked by hand, verify in A1)
- 1,000 books, 50 categories, 50 listing pages: `/catalogue/page-1.html` … `page-50.html`, 20 books each. The "next" link is `li.next a`.
- Product page: title `h1`; the table rows hold UPC, Price (excl. tax), Price (incl. tax), Tax, Availability "In stock (22 available)" and Number of reviews.
  The rating is a CSS class: `p.star-rating.Three` → 3. The description is the `p` after `#product_description` and is sometimes missing.
  The category is the 3rd breadcrumb `li`. The cover image is `#product_gallery img`, and its `src` is relative.
- All links are relative, so join them with `urllib.parse.urljoin`.
- Encoding trap: `requests` guesses ISO-8859-1, which turns "£" into "Â£". Pass `resp.content` (bytes) to BeautifulSoup.
- Number of reviews is always 0 on this site, so it is not stored (documented as a limitation).

## Database (schema.sql, Postgres)
```sql
categories(id bigint generated always as identity primary key, name text unique not null)
books(
  upc text primary key,                 -- stable unique id on the site
  title text not null,
  category_id bigint not null references categories(id),
  price numeric(8,2) not null,          -- GBP incl. tax
  price_excl_tax numeric(8,2), tax numeric(8,2),
  in_stock boolean not null,
  stock_count integer,                  -- the "(22 available)" number
  rating smallint not null check (rating between 1 and 5),
  description text,
  image_url text, product_url text unique not null,
  first_seen timestamptz not null default now(),   -- never sent by the scraper, so an upsert keeps it
  last_scraped timestamptz not null
)
scrape_runs(id bigint identity pk, started_at timestamptz, finished_at timestamptz, mode text,
  pages_visited int, books_new int, books_updated int, books_skipped int, errors int,
  status text)                          -- running/ok/failed
-- RLS on for all three tables + one "public read" SELECT policy each
-- Explicit grants (select to anon/authenticated, all to service_role): new projects may not expose
-- new tables to the Data API automatically, so the script works whatever that project setting is
```
Why a separate categories table: categories repeat 1,000 times, and the UI needs the list of categories.
Why scrape_runs: the app can show "data from <date>", and it shows how incremental runs behave.

## Scraper behaviour
- `python scraper.py [--limit N] [--full] [--delay 0.2]`
- Default is **incremental**: all 50 listing pages are crawled, but a product page is only fetched if its
  `product_url` is not in the database yet. `--full` refetches everything (an upsert on `upc` updates rows).
- Writes go in batches (e.g. one upsert per listing page) rather than 1,000 single calls.
- Politeness: a fixed delay between requests, a 10 s timeout, 3 retries with backoff on network errors or 5xx,
  and a generic User-Agent `APAIF-coursework-scraper/1.0 (educational)` (no personal data).
- One failed book is logged and counted in `errors`, and the run continues. Each run is recorded in `scrape_runs`.
- Progress is printed (page x/50, counts). A full run takes ~1,050 requests, a few minutes.

## App behaviour
- **Data source**: `BOOKS_SOURCE=supabase` (default when `.env` has keys) or `sample` (the bundled synthetic CSV).
  The sample mode lets someone without a Supabase project still open the app, and lets stream B build before stream A has data.
- `queries.load_books()` fetches all rows once (~1,000, so it fits in memory), cached with `st.cache_data(ttl=600)`.
  Trap: Supabase returns at most 1,000 rows per request by default → page with `.range()`.
  Filtering and aggregates are pure pandas functions, so they are easy to test.
- **Browse**: sidebar filters (title search, categories, price range, min rating, in stock only), a sort option,
  a result count, and a table with a cover thumbnail and a link to the book page.
- **Book detail**: pick a book → cover, description, price, stock, rating, category, link.
- **Insights** (cherry on top): KPI tiles (books, categories, average price, % in stock), books per category
  (top 15), price distribution, average price by rating.
- Footer: the data source, plus the date and mode of the latest scrape run.

---

## Tasks

### Task 0: foundation (Opus, main session, on `main`)
Folder skeleton, `requirements.txt`, `.env.example`, `schema.sql`, `db.py` (`get_client(write=False)` reads `.env`),
`tools/make_sample_data.py` + generated `tests/fixtures/sample_books.csv` (60 synthetic books, fixed seed, labelled synthetic),
README skeleton with all required headings, this plan.
**Michael:** creates the Supabase project, runs `schema.sql` in the SQL editor, fills in `.env`. Opus checks the
connection (read with the publishable key, write rejected with it, write allowed with the secret key).
After this, the two streams branch off `main` and run in parallel.

### Stream A: scraper + database writes (Sonnet session, own worktree/branch)
Owns: `parse.py`, `scraper.py`, write functions in `db.py`, `tests/test_parse.py`, `tests/test_db.py`,
`tests/fixtures/*.html`, and the README sections **Data collection** and **Data persistence**.
Needs `.env` (copy it from the main checkout into the worktree; never commit it).
- **A1** Save one listing page and two product pages (one without a description) to `tests/fixtures/`.
  Write `parse.py`: `parse_listing(html, page_url) -> (book_urls, next_url|None)` and
  `parse_book(html, url) -> dict` matching the books columns + `category` name. Tests: `tests/test_parse.py`.
- **A2** `db.py` write functions (each takes the client as an argument so tests can pass a fake):
  `ensure_categories(names) -> {name: id}`, `upsert_books(rows)` (omits `first_seen`), `known_product_urls()`
  (paged), `start_run(mode)` / `finish_run(id, stats)`. Tests with a small fake client, offline.
- **A3** `scraper.py`: Session, delay, retries, crawl the listing pages, then product pages, batch upserts, record the run, CLI flags.
  First real run: `--limit 40`.
- **A4** Incremental default + `--full` + `--limit`. Show that a second run skips everything already stored.
- **A5** Full scrape. Verify in Supabase: 1,000 books, 50 categories, ratings 1–5, no null prices. Write the README sections.

### Stream B: queries + Streamlit app (Sonnet session, own worktree/branch)
Owns: `queries.py`, `app.py`, `tests/test_queries.py`, and the README section **User interaction**.
Builds with `BOOKS_SOURCE=sample` and switches to Supabase once stream A has data (`.env` copy as above).
Must not edit stream A's files, `db.py` or `schema.sql`.
- **B1** `queries.py`: `load_books(source)` → DataFrame (Supabase: paged select joining the category name; sample: the CSV),
  `filter_books(df, search, categories, price_range, min_rating, in_stock_only, sort)`, the aggregates for Insights,
  `latest_run(source)`. Tests on the sample CSV.
- **B2** `app.py` Browse tab with sidebar filters and the table (`st.column_config.ImageColumn` / `LinkColumn`).
- **B3** Book detail view.
- **B4** Insights tab.
- **B5** States: missing keys → a clear message + hint to use `BOOKS_SOURCE=sample`, empty filter result, Supabase unreachable.
  Footer with the source and the latest run. README section.

### Checkpoint 2: merge + try (Michael)
Checker agent (Haiku): pytest, `scraper.py --limit 20` (incremental, harmless on the real database), app starts in both sources
without errors. Opus merges both branches into `main` with `--no-ff`. Michael tries the app.

### Task C: docs (Sonnet)
README Setup (fresh clone, how a grader creates their own Supabase project + runs `schema.sql`, or uses sample mode), Purpose,
Limitations and assistance (honest AI statement, including the agent setup), Learning draft (from the build log, for Michael
to rewrite himself), screenshot, root README link.

### Audit loop (checkpoints 3–4)
A fresh read-only auditor agent runs the course audit prompt verbatim from `books-to-scrape/` →
findings go to `_work/audit-log.md` → fixes → re-run → `AUDIT.md`.

---

## Rules for every coding agent
- Work only on your own task and your own files. If you need a change elsewhere (schema, another stream's file),
  **stop and report it** instead of making it.
- Python: `conda run -n apaif python ...`. New package → add it to `requirements.txt` by hand, then `pip install -r`.
  Never `conda install` packages.
- Never print, log or commit key values. Never commit `.env`. Only the scraper may use the secret key.
- Commit after **each** task (small commits are graded), message `Books: <what changed>` with a short body
  saying why, plus the Co-Authored-By trailer. Never push.
- Before each commit: tests pass (`conda run -n apaif python -m pytest books-to-scrape/tests -q`).
- Comments explain *why*, not *what*. Keep code simple enough for a student to explain line by line.
- Report at the end of each task in 10 lines or fewer: commit hash, files changed, commands run + result,
  one "learning" sentence (a trap or decision worth logging), open questions.
