"""Crawler: books.toscrape.com -> Supabase.

Usage (from the books-to-scrape folder):
    python scraper.py --limit 40      # try it on the first 40 books
    python scraper.py                 # incremental: only fetch books not stored yet
    python scraper.py --full          # refetch every book and update the rows
"""

import argparse
import time
from datetime import datetime, timezone

import requests

import db
import parse

START_URL = "https://books.toscrape.com/catalogue/page-1.html"
# A generic, honest User-Agent: says what the script is, contains no personal data.
USER_AGENT = "APAIF-coursework-scraper/1.0 (educational)"
TIMEOUT = 10  # seconds
RETRIES = 3


def fetch(session: requests.Session, url: str, delay: float) -> bytes:
    """GET a page and return its bytes. Retries network errors and 5xx answers with a growing pause."""
    for attempt in range(1, RETRIES + 1):
        time.sleep(delay)  # politeness: a pause before every request
        try:
            response = session.get(url, timeout=TIMEOUT)
            if response.status_code < 500:
                response.raise_for_status()  # a 404 is not worth retrying: fail at once
                return response.content  # bytes, not .text: see parse.py about the encoding
        except (requests.ConnectionError, requests.Timeout):
            pass  # network problem: try again
        if attempt == RETRIES:
            raise RuntimeError(f"giving up on {url} after {RETRIES} attempts")
        time.sleep(2 ** attempt)  # backoff: 2 s, then 4 s
    raise AssertionError("unreachable")


def scrape(client, mode: str, limit: int | None, delay: float) -> dict:
    """Crawl the listing pages, fetch the books that are needed and store them. Returns the run stats."""
    full = mode == "full"
    known = db.known_product_urls(client)
    stats = {"pages_visited": 0, "books_new": 0, "books_updated": 0, "books_skipped": 0, "errors": 0}
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT

    seen = 0  # books looked at so far (new, updated or skipped); --limit stops the crawl here
    page_url = START_URL
    while page_url and (limit is None or seen < limit):
        listing = fetch(session, page_url, delay)
        book_urls, next_url = parse.parse_listing(listing, page_url)
        stats["pages_visited"] += 1
        if limit is not None:
            book_urls = book_urls[: limit - seen]
        seen += len(book_urls)

        books = []
        for url in book_urls:
            if url in known and not full:
                stats["books_skipped"] += 1  # incremental: already stored, no request needed
                continue
            try:
                books.append(parse.parse_book(fetch(session, url, delay), url))
            except Exception as error:  # one bad book must not stop the run
                stats["errors"] += 1
                print(f"  ! {url}: {error}")

        if books:
            category_ids = db.ensure_categories(client, [b["category"] for b in books])
            now = datetime.now(timezone.utc).isoformat()
            rows = []
            for book in books:
                row = {k: v for k, v in book.items() if k != "category"}
                row["category_id"] = category_ids[book["category"]]
                row["last_scraped"] = now
                rows.append(row)
            db.upsert_books(client, rows)  # one request per listing page
            for book in books:
                stats["books_updated" if book["product_url"] in known else "books_new"] += 1

        print(
            f"page {stats['pages_visited']}: new {stats['books_new']}, updated {stats['books_updated']}, "
            f"skipped {stats['books_skipped']}, errors {stats['errors']}"
        )
        page_url = next_url
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape books.toscrape.com into Supabase.")
    parser.add_argument("--limit", type=int, help="stop after looking at this many books")
    parser.add_argument("--full", action="store_true", help="refetch and update books that are already stored")
    parser.add_argument("--delay", type=float, default=0.2, help="seconds to wait before each request")
    args = parser.parse_args()

    client = db.get_client(write=True)  # the scraper is the only part that uses the secret key
    mode = "full" if args.full else "incremental"
    run_id = db.start_run(client, mode)
    stats = {}
    try:
        stats = scrape(client, mode, args.limit, args.delay)
        stats["status"] = "ok"
    except BaseException:  # also Ctrl+C: the run row must not stay on "running"
        stats["status"] = "failed"
        raise
    finally:
        db.finish_run(client, run_id, stats)
        print(f"run {run_id} finished: {stats}")


if __name__ == "__main__":
    main()
