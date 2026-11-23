"""Load the books into pandas and answer the app's questions about them.

Everything except the two loading functions is a pure pandas function (DataFrame in,
DataFrame/number out). That keeps the logic easy to test offline on the sample CSV.
"""

import os
from pathlib import Path

import pandas as pd

SAMPLE_CSV = Path(__file__).resolve().parent / "tests" / "fixtures" / "sample_books.csv"
PAGE_SIZE = 1000  # Supabase returns at most 1,000 rows per request

# The columns every source must deliver (category as a name, not an id).
COLUMNS = [
    "upc", "title", "category", "price", "price_excl_tax", "tax", "in_stock", "stock_count",
    "rating", "description", "image_url", "product_url", "first_seen", "last_scraped",
]

# The site itself files these books under placeholder categories (not real genres).
PLACEHOLDER_CATEGORIES = ("Default", "Add a comment")

SORT_OPTIONS = {
    "Title (A to Z)": ("title", True),
    "Price (low to high)": ("price", True),
    "Price (high to low)": ("price", False),
    "Rating (high to low)": ("rating", False),
}


# --- loading -----------------------------------------------------------------------------

def default_source() -> str:
    """'sample' or 'supabase', taken from the BOOKS_SOURCE variable (default: supabase)."""
    source = os.getenv("BOOKS_SOURCE", "supabase").strip().lower()
    if source not in ("sample", "supabase"):
        raise ValueError(f"BOOKS_SOURCE must be 'sample' or 'supabase', not '{source}'.")
    return source


def _fetch_all(build_query) -> list[dict]:
    """Read a whole table in pages of 1,000 rows.

    build_query() must return a fresh query each time (a query object is used up once executed).
    A short page means we reached the end.
    """
    rows, start = [], 0
    while True:
        page = build_query().range(start, start + PAGE_SIZE - 1).execute().data
        rows.extend(page)
        if len(page) < PAGE_SIZE:
            return rows
        start += PAGE_SIZE


def load_books(source: str) -> pd.DataFrame:
    """Return all books as a DataFrame with the columns in COLUMNS."""
    if source == "sample":
        return pd.read_csv(SAMPLE_CSV)[COLUMNS]

    from db import get_client  # imported here so sample mode works without a .env

    client = get_client()  # publishable key: read-only
    # "categories(name)" asks PostgREST to embed the related category row (a join).
    # Order by upc so paging is stable: without an order, pages could overlap or skip rows.
    rows = _fetch_all(lambda: client.table("books").select("*, categories(name)").order("upc"))
    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(columns=COLUMNS)
    # Flatten {"categories": {"name": "Travel"}} into a plain "category" column.
    df["category"] = df["categories"].map(lambda c: c["name"] if isinstance(c, dict) else None)
    for column in ("price", "price_excl_tax", "tax"):
        df[column] = pd.to_numeric(df[column])  # Postgres numeric arrives as text or float
    return df[COLUMNS]


def latest_run(source: str) -> dict | None:
    """The most recent scrape run as a dict, or None (sample mode or no runs yet)."""
    if source == "sample":
        return None
    from db import get_client

    rows = (
        get_client().table("scrape_runs").select("*").order("started_at", desc=True).limit(1)
        .execute().data
    )
    return rows[0] if rows else None


# --- filtering ---------------------------------------------------------------------------

def filter_books(
    df: pd.DataFrame,
    search: str = "",
    categories: list[str] | None = None,
    price_range: tuple[float, float] | None = None,
    min_rating: int = 1,
    in_stock_only: bool = False,
    sort: str = "Title (A to Z)",
) -> pd.DataFrame:
    """Apply the sidebar filters, then sort. Empty/None filters mean 'no restriction'."""
    mask = pd.Series(True, index=df.index)
    if search.strip():
        # regex=False: treat what the user typed literally (e.g. "c++" must not be a pattern)
        mask &= df["title"].str.contains(search.strip(), case=False, regex=False)
    if categories:
        mask &= df["category"].isin(categories)
    if price_range:
        mask &= df["price"].between(price_range[0], price_range[1])
    mask &= df["rating"] >= min_rating
    if in_stock_only:
        mask &= df["in_stock"]
    column, ascending = SORT_OPTIONS[sort]
    # Ties are broken by title so the order is the same on every rerun.
    return df[mask].sort_values([column, "title"], ascending=[ascending, True]).reset_index(drop=True)


# --- shelf view --------------------------------------------------------------------------

def page_count(total: int, per_page: int) -> int:
    """Number of pages needed for `total` items (at least 1, so an empty shelf has a page 1)."""
    return max(1, -(-total // per_page))  # -(-a // b) is a ceiling division


def paginate(df: pd.DataFrame, page: int, per_page: int) -> pd.DataFrame:
    """The rows of one page (page numbers start at 1; out-of-range pages are clamped)."""
    page = min(max(page, 1), page_count(len(df), per_page))
    start = (page - 1) * per_page
    return df.iloc[start : start + per_page]


# --- aggregates for the header and the Insights tab --------------------------------------

def kpis(df: pd.DataFrame) -> dict:
    """The headline numbers. An empty DataFrame gives zeros instead of NaN."""
    if df.empty:
        return {"books": 0, "categories": 0, "median_price": 0.0, "copies": 0, "pct_five_star": 0.0}
    return {
        "books": len(df),
        "categories": df["category"].nunique(),
        "median_price": float(df["price"].median()),  # median: robust, prices are spread evenly
        "copies": int(df["stock_count"].sum()),  # copies on the shelves, not titles
        "pct_five_star": float((df["rating"] == 5).mean() * 100),
    }


def books_per_category(df: pd.DataFrame, top: int = 15) -> pd.Series:
    """Number of books in the `top` largest categories (index = category, sorted descending)."""
    return df["category"].value_counts().head(top)


def rating_distribution(df: pd.DataFrame) -> pd.Series:
    """Books per star rating; all of 1..5 are present, with 0 for stars nobody got."""
    return df["rating"].value_counts().reindex(range(1, 6), fill_value=0)


def category_prices(df: pd.DataFrame, min_books: int = 10) -> pd.DataFrame:
    """Average price per category (columns category, books, avg_price), cheapest first.

    Only categories with at least `min_books` books: an average of two books says little.
    """
    grouped = df.groupby("category")["price"].agg(books="count", avg_price="mean").reset_index()
    grouped = grouped[grouped["books"] >= min_books]
    grouped["avg_price"] = grouped["avg_price"].round(2)
    return grouped.sort_values(["avg_price", "category"]).reset_index(drop=True)


def price_distribution(df: pd.DataFrame, bin_width: int = 10) -> pd.Series:
    """Number of books per price band, e.g. '10-20' (index sorted by price, empty bands kept)."""
    if df.empty:
        return pd.Series(dtype=int)
    start = int(df["price"].min() // bin_width * bin_width)
    edges = list(range(start, int(df["price"].max()) + bin_width + 1, bin_width))
    bands = pd.cut(df["price"], bins=edges, right=False)
    counts = bands.value_counts(sort=False)
    # Plain-text labels (the chart needs strings, not pandas Interval objects).
    counts.index = [f"{int(i.left)}-{int(i.right)}" for i in counts.index]
    return counts


def avg_price_by_rating(df: pd.DataFrame) -> pd.Series:
    """Average price for each star rating (index = rating 1..5)."""
    return df.groupby("rating")["price"].mean().round(2)


def best_value(df: pd.DataFrame, n: int = 6) -> pd.DataFrame:
    """The `n` cheapest 5-star books (ties broken by title so the order is stable)."""
    return df[df["rating"] == 5].sort_values(["price", "title"]).head(n).reset_index(drop=True)


def low_stock(df: pd.DataFrame, n: int = 6) -> pd.DataFrame:
    """The `n` books with the fewest copies left (only books that are still in stock)."""
    available = df[df["in_stock"] & (df["stock_count"] > 0)]
    return available.sort_values(["stock_count", "title"]).head(n).reset_index(drop=True)


def takeaways(df: pd.DataFrame, min_books: int = 10) -> dict:
    """The numbers behind the written findings on the Insights tab (None where undefined)."""
    result = {"cheapest_category": None, "priciest_category": None, "rating_gap": None}
    prices = category_prices(df, min_books)
    if not prices.empty:
        result["cheapest_category"] = prices.iloc[0].to_dict()
        result["priciest_category"] = prices.iloc[-1].to_dict()
    by_rating = avg_price_by_rating(df)
    if len(by_rating) >= 2:
        low, high = by_rating.index.min(), by_rating.index.max()
        result["rating_gap"] = {
            "low_rating": int(low), "low_price": float(by_rating[low]),
            "high_rating": int(high), "high_price": float(by_rating[high]),
            "difference": float(by_rating[high] - by_rating[low]),
        }
    return result
