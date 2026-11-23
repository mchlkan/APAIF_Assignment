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


# --- aggregates for the Insights tab -----------------------------------------------------

def kpis(df: pd.DataFrame) -> dict:
    """The four headline numbers. An empty DataFrame gives zeros instead of NaN."""
    if df.empty:
        return {"books": 0, "categories": 0, "avg_price": 0.0, "pct_in_stock": 0.0}
    return {
        "books": len(df),
        "categories": df["category"].nunique(),
        "avg_price": float(df["price"].mean()),
        "pct_in_stock": float(df["in_stock"].mean() * 100),
    }


def books_per_category(df: pd.DataFrame, top: int = 15) -> pd.Series:
    """Number of books in the `top` largest categories (index = category, sorted descending)."""
    return df["category"].value_counts().head(top)


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
