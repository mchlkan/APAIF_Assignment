"""Checks for the shared foundation: sample data contract and the Supabase config error."""

import csv
from pathlib import Path

import pytest

import db
from tools.make_sample_data import COLUMNS, make_rows

SAMPLE_CSV = Path(__file__).parent / "fixtures" / "sample_books.csv"


def test_sample_csv_matches_generator():
    # The committed CSV must be exactly what the script produces (no hand edits drifting apart).
    with SAMPLE_CSV.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert list(rows[0].keys()) == COLUMNS
    assert [r["upc"] for r in rows] == [r["upc"] for r in make_rows()]


def test_sample_data_is_valid():
    rows = make_rows()
    assert len(rows) == 60
    assert len({r["upc"] for r in rows}) == 60
    assert all(1 <= r["rating"] <= 5 for r in rows)
    assert all(r["price"] > 0 for r in rows)
    assert {r["in_stock"] for r in rows} == {True, False}  # both cases present for filter tests


@pytest.mark.parametrize("write, key_name", [(False, "SUPABASE_PUBLISHABLE_KEY"), (True, "SUPABASE_SECRET_KEY")])
def test_missing_config_gives_clear_error(monkeypatch, tmp_path, write, key_name):
    monkeypatch.setattr(db, "ENV_PATH", tmp_path / "no.env")  # ignore any real .env
    for name in ("SUPABASE_URL", "SUPABASE_PUBLISHABLE_KEY", "SUPABASE_SECRET_KEY"):
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(db.ConfigError, match=key_name):
        db.get_client(write=write)


def test_placeholder_values_count_as_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "ENV_PATH", tmp_path / "no.env")
    monkeypatch.setenv("SUPABASE_URL", "https://your-project-ref.supabase.co")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "your-publishable-key")
    with pytest.raises(db.ConfigError, match="SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY"):
        db.get_client()


def test_client_is_created_from_valid_settings(monkeypatch, tmp_path):
    # No network call happens when the client is created.
    monkeypatch.setattr(db, "ENV_PATH", tmp_path / "no.env")
    monkeypatch.setenv("SUPABASE_URL", "https://abcdefghijklmnop.supabase.co")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "sb_publishable_test")
    assert db.get_client() is not None


def test_rest_endpoint_url_is_accepted(monkeypatch, tmp_path):
    # Users often copy the REST endpoint from the dashboard instead of the base project URL.
    monkeypatch.setattr(db, "ENV_PATH", tmp_path / "no.env")
    monkeypatch.setenv("SUPABASE_URL", "https://abcdefghijklmnop.supabase.co/rest/v1/")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "sb_publishable_test")
    client = db.get_client()
    # Without the fix the client would call ".../rest/v1/rest/v1".
    assert str(client.rest_url).rstrip("/") == "https://abcdefghijklmnop.supabase.co/rest/v1"
