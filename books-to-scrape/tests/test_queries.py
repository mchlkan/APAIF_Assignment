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
    assert result["median_price"] == pytest.approx(books["price"].median())
    assert result["copies"] == books["stock_count"].sum()
    assert result["pct_five_star"] == pytest.approx((books["rating"] == 5).mean() * 100)
    empty = queries.kpis(books.iloc[0:0])
    assert empty["books"] == 0 and empty["copies"] == 0


def test_books_per_category(books):
    counts = queries.books_per_category(books, top=3)
    assert len(counts) <= 3
    assert counts.is_monotonic_decreasing
    assert counts.sum() <= len(books)


def test_page_count_and_paginate(books):
    assert queries.page_count(0, 24) == 1
    assert queries.page_count(24, 24) == 1
    assert queries.page_count(25, 24) == 2
    first, last = queries.paginate(books, 1, 24), queries.paginate(books, 3, 24)
    assert len(first) == 24 and len(last) == 12
    assert first["upc"].iloc[0] == books["upc"].iloc[0]
    assert queries.paginate(books, 99, 24).equals(last)  # clamped to the last page
    assert queries.paginate(books, 0, 24).equals(first)  # clamped to the first page
    assert queries.paginate(books.iloc[0:0], 1, 24).empty


def test_rating_distribution_has_all_stars(books):
    result = queries.rating_distribution(books)
    assert list(result.index) == [1, 2, 3, 4, 5]
    assert result.sum() == len(books)
    only_threes = books[books["rating"] == 3]
    assert queries.rating_distribution(only_threes)[[1, 2, 4, 5]].eq(0).all()


def test_category_prices_threshold_and_order(books):
    result = queries.category_prices(books, min_books=8)
    assert set(result.columns) == {"category", "books", "avg_price"}
    assert (result["books"] >= 8).all()
    assert result["avg_price"].is_monotonic_increasing
    expected = books[books["category"] == result["category"].iloc[0]]["price"].mean()
    assert result["avg_price"].iloc[0] == pytest.approx(expected, abs=0.01)
    assert queries.category_prices(books, min_books=1000).empty


def test_price_distribution_counts_every_book(books):
    distribution = queries.price_distribution(books)
    assert distribution.sum() == len(books)
    assert all("-" in label for label in distribution.index)
    assert queries.price_distribution(books.iloc[0:0]).empty
    five = queries.price_distribution(books, bin_width=5)
    assert five.sum() == len(books)
    assert len(five) > len(distribution)  # narrower bands, more of them


def test_avg_price_by_rating(books):
    result = queries.avg_price_by_rating(books)
    assert set(result.index) <= {1, 2, 3, 4, 5}
    assert result.between(books["price"].min(), books["price"].max()).all()


def test_best_value_is_cheapest_five_star(books):
    result = queries.best_value(books, n=3)
    assert len(result) == 3
    assert (result["rating"] == 5).all()
    assert result["price"].is_monotonic_increasing
    assert result["price"].iloc[0] == books[books["rating"] == 5]["price"].min()


def test_most_stocked_has_the_most_copies(books):
    result = queries.most_stocked(books, n=4)
    assert len(result) == 4
    assert result["stock_count"].is_monotonic_decreasing
    assert result["stock_count"].iloc[0] == books["stock_count"].max()


def test_mark_category_prices(books):
    prices = queries.category_prices(books, min_books=5)
    marked = queries.mark_category_prices(prices)
    assert marked["kind"].iloc[0] == "cheapest" and marked["kind"].iloc[-1] == "priciest"
    assert (marked["kind"].iloc[1:-1] == "other").all()  # the sample has no placeholder categories
    fake = pd.DataFrame({"category": ["A", "Default", "B", "C"], "books": 10, "avg_price": [1, 2, 3, 4]})
    assert list(queries.mark_category_prices(fake)["kind"]) == ["cheapest", "placeholder", "other", "priciest"]
    assert queries.mark_category_prices(prices.iloc[0:0]).empty


def test_takeaways(books):
    result = queries.takeaways(books, min_books=8)
    cheapest, priciest = result["cheapest_category"], result["priciest_category"]
    assert cheapest["avg_price"] <= priciest["avg_price"]
    gap = result["rating_gap"]
    assert gap["low_rating"] == 1 and gap["high_rating"] == 5
    assert gap["difference"] == pytest.approx(gap["high_price"] - gap["low_price"])
    assert result["top_rating"]["stars"] == books["rating"].mode().iloc[0]
    assert result["busiest_band"]["books"] == queries.price_distribution(books, 5).max()
    empty = queries.takeaways(books.iloc[0:0])
    assert empty["cheapest_category"] is None and empty["rating_gap"] is None


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
