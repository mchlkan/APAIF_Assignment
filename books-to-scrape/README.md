# Books to Scrape

> Work in progress: this README is filled in section by section during the build (see [docs/plan.md](docs/plan.md)).

Scrapes all 1,000 books from [books.toscrape.com](https://books.toscrape.com), a sandbox site made for
scraping practice, stores them in a Supabase (Postgres) database, and lets you browse, filter and
analyse them in a Streamlit app.

## Purpose
_To do (docs task)._

## Data collection
_To do (scraper stream): what is scraped, how pages are crawled, politeness, incremental runs._

## Data persistence
_To do (scraper stream): Supabase tables, why this schema, keys and Row Level Security._

## User interaction
Start the app from the repository root (it needs the Supabase keys in `books-to-scrape/.env`, or sample mode):

```bash
conda run -n apaif streamlit run books-to-scrape/app.py
BOOKS_SOURCE=sample conda run -n apaif streamlit run books-to-scrape/app.py   # no database needed
```

`BOOKS_SOURCE=sample` shows 60 synthetic books from `tests/fixtures/sample_books.csv`, so anyone can try the
interface without a Supabase project. The app only ever uses the read-only publishable key.

The app has three tabs and a sidebar:

- **Sidebar filters** (apply to Browse and Book detail): title search, categories, price range, minimum rating,
  "in stock only" and a sort order.
- **Browse**: a table of the matching books with cover thumbnail, category, price, rating, stock and a link to the
  book's page on the source site. The caption shows how many books match.
- **Book detail**: pick one of the filtered books to see its cover, rating, price, availability, description and link.
- **Insights** (the extra feature): headline numbers (books, categories, average price, share in stock) and charts of
  books per category (top 15), price distribution in £10 bands, and average price per star rating. These always
  describe the whole catalogue, not the filtered selection.
- **Footer**: the data source and, for Supabase, the date and mode of the latest scrape run.

Messages instead of crashes: missing or wrong keys (with the hint to use sample mode), an unreachable database, an
empty database ("run the scraper first") and a filter combination that matches nothing.

How it works: `queries.py` loads all books once (paged with `.range()`, because Supabase returns at most 1,000 rows per
request; the category name is joined in) and holds the filter and aggregate functions as plain pandas code, which
`tests/test_queries.py` checks offline. `app.py` only draws the interface and caches the loaded data for 10 minutes.

## Setup
_To do (docs task): fresh clone → conda env → `pip install -r requirements.txt` → Supabase project +
`schema.sql` → `.env` → scrape → run the app. Sample mode without Supabase._

## Learning
_To do: written by Michael at the end._

## Limitations and assistance
_To do (docs task): known limitations, AI tools used (including the multi-agent build setup)._

## Screenshot
_To do._
