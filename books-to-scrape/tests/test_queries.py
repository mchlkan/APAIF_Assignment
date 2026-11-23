"""Offline tests for queries.py: everything runs on the bundled sample CSV or a fake client."""

import pandas as pd
import pytest

import queries


@pytest.fixture(scope="module")
def books():
    return queries.load_books("sample")


def test_load_books_sample_has_contract_columns(books):
    assert list(books.columns) == queries.COLUMNS
    assert len(books) == 60
    assert books["category"].notna().all()


def test_default_source(monkeypatch):
    monkeypatch.delenv("BOOKS_SOURCE", raising=False)
    assert queries.default_source() == "supabase"
    monkeypatch.setenv("BOOKS_SOURCE", "Sample")
    assert queries.default_source() == "sample"
    monkeypatch.setenv("BOOKS_SOURCE", "nonsense")
    with pytest.raises(ValueError):
        queries.default_source()


def test_filter_without_arguments_returns_everything(books):
    assert len(queries.filter_books(books)) == len(books)


def test_filter_search_is_case_insensitive_and_literal(books):
    result = queries.filter_books(books, search="NORTHERN")
    assert len(result) > 0
    assert result["title"].str.contains("northern", case=False).all()
    assert queries.filter_books(books, search="(").empty  # not treated as a regex


def test_filter_category_price_rating_stock(books):
    category = books["category"].iloc[0]
    result = queries.filter_books(
        books, categories=[category], price_range=(20, 40), min_rating=2, in_stock_only=True
    )
    assert (result["category"] == category).all()
    assert result["price"].between(20, 40).all()
    assert (result["rating"] >= 2).all()
    assert result["in_stock"].all()


def test_filter_sort_orders(books):
    low_first = queries.filter_books(books, sort="Price (low to high)")["price"]
    high_first = queries.filter_books(books, sort="Price (high to low)")["price"]
    assert low_first.is_monotonic_increasing
    assert high_first.is_monotonic_decreasing
    assert queries.filter_books(books, sort="Rating (high to low)")["rating"].is_monotonic_decreasing


def test_filter_no_match_gives_empty_frame_with_columns(books):
    result = queries.filter_books(books, search="no such book xyz")
    assert result.empty
    assert list(result.columns) == queries.COLUMNS


def test_kpis(books):
    result = queries.kpis(books)
    assert result["books"] == 60
    assert result["categories"] == books["category"].nunique()
    assert result["avg_price"] == pytest.approx(books["price"].mean())
    assert 0 <= result["pct_in_stock"] <= 100
    assert queries.kpis(books.iloc[0:0])["books"] == 0


def test_books_per_category(books):
    counts = queries.books_per_category(books, top=3)
    assert len(counts) <= 3
    assert counts.is_monotonic_decreasing
    assert counts.sum() <= len(books)


def test_price_distribution_counts_every_book(books):
    distribution = queries.price_distribution(books)
    assert distribution.sum() == len(books)
    assert all("-" in label for label in distribution.index)
    assert queries.price_distribution(books.iloc[0:0]).empty


def test_avg_price_by_rating(books):
    result = queries.avg_price_by_rating(books)
    assert set(result.index) <= {1, 2, 3, 4, 5}
    assert result.between(books["price"].min(), books["price"].max()).all()


def test_latest_run_sample_is_none():
    assert queries.latest_run("sample") is None


class FakeQuery:
    """Mimics the part of the supabase query builder that _fetch_all uses."""

    def __init__(self, rows):
        self.rows, self.window = rows, None

    def range(self, start, end):
        self.window = (start, end)
        return self

    def execute(self):
        start, end = self.window
        return type("Response", (), {"data": self.rows[start : end + 1]})()


def test_fetch_all_pages_past_the_1000_row_limit():
    rows = [{"n": i} for i in range(2350)]
    assert queries._fetch_all(lambda: FakeQuery(rows)) == rows
    assert queries._fetch_all(lambda: FakeQuery([])) == []
    exactly_one_page = rows[:1000]
    assert queries._fetch_all(lambda: FakeQuery(exactly_one_page)) == exactly_one_page
