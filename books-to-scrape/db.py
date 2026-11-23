"""Supabase connection for the scraper and the app.

Write helpers (categories, book upserts, scrape runs) are added below by the scraper work.
"""

import os
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
    return create_client(url, key)
