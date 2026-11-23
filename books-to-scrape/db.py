"""Supabase connection for the scraper and the app.

Write helpers (categories, book upserts, scrape runs) are at the bottom; the scraper uses them.
"""

import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from supabase import Client, create_client

# Always read the .env next to this file, so it works no matter which folder you start from.
ENV_PATH = Path(__file__).resolve().parent / ".env"


class ConfigError(RuntimeError):
    """Raised when the Supabase URL or key is missing, with a message saying how to fix it."""


def _setting(name: str) -> str | None:
    value = os.getenv(name, "").strip()
    # Values copied unchanged from .env.example count as missing.
    if not value or "your-" in value:
        return None
    return value


def get_client(write: bool = False) -> Client:
    """Return a Supabase client.

    write=False uses the publishable key: read-only because of the RLS policies (the app).
    write=True uses the secret key, which bypasses RLS (only the scraper uses it).
    """
    load_dotenv(ENV_PATH)  # does not override variables already set in the shell
    key_name = "SUPABASE_SECRET_KEY" if write else "SUPABASE_PUBLISHABLE_KEY"
    url, key = _setting("SUPABASE_URL"), _setting(key_name)
    missing = [name for name, value in (("SUPABASE_URL", url), (key_name, key)) if value is None]
    if missing:
        raise ConfigError(
            f"Missing {' and '.join(missing)}. Copy .env.example to {ENV_PATH} and fill in your "
            "Supabase project's values (Project Settings → API keys)."
        )
    # The dashboard also shows the REST endpoint (".../rest/v1/"); the client wants only the base URL.
    url = url.rstrip("/").removesuffix("/rest/v1")
    return create_client(url, key)


# ---------------------------------------------------------------- write helpers (scraper only)
# Each function takes the client as an argument, so tests can pass a small fake instead of the real database.

PAGE_SIZE = 1000  # Supabase returns at most 1,000 rows per request


def ensure_categories(client: Client, names: list[str]) -> dict[str, int]:
    """Make sure every category name exists and return {name: id}."""
    names = sorted(set(names))
    if not names:
        return {}
    # Upsert on the unique name: new names are inserted, existing ones are left as they are.
    response = client.table("categories").upsert([{"name": n} for n in names], on_conflict="name").execute()
    return {row["name"]: row["id"] for row in response.data}


def upsert_books(client: Client, rows: list[dict]) -> None:
    """Insert new books and update existing ones (matched on upc) in one request.

    Rows must already have category_id and last_scraped. first_seen is removed if present, so the
    database default sets it for new books and an update never overwrites the original date.
    """
    if not rows:
        return
    clean = [{k: v for k, v in row.items() if k != "first_seen"} for row in rows]
    client.table("books").upsert(clean, on_conflict="upc").execute()


def known_product_urls(client: Client) -> set[str]:
    """All product_url values already stored, fetched page by page because of the 1,000-row limit."""
    urls: set[str] = set()
    start = 0
    while True:
        response = client.table("books").select("product_url").range(start, start + PAGE_SIZE - 1).execute()
        urls.update(row["product_url"] for row in response.data)
        if len(response.data) < PAGE_SIZE:  # a short page means this was the last one
            return urls
        start += PAGE_SIZE


def start_run(client: Client, mode: str) -> int:
    """Record the start of a scrape run (mode: 'incremental' or 'full') and return its id."""
    response = client.table("scrape_runs").insert({"mode": mode}).execute()  # status defaults to 'running'
    return response.data[0]["id"]


def finish_run(client: Client, run_id: int, stats: dict) -> None:
    """Close a run. stats holds pages_visited, books_new, books_updated, books_skipped, errors, status."""
    finished = {"finished_at": datetime.now(timezone.utc).isoformat(), **stats}
    client.table("scrape_runs").update(finished).eq("id", run_id).execute()
