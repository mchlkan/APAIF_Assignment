"""Streamlit app: a small bookshop for the scraped books.

Start it from inside this folder (so .streamlit/config.toml, the theme, is found):
    cd books-to-scrape && streamlit run app.py
"""

import pandas as pd
import streamlit as st

import queries
from db import ConfigError

st.set_page_config(page_title="Books to Scrape", page_icon="📚", layout="wide")

PER_PAGE = 24  # divisible by 4, 3, 2 and 1 so the last full row of the grid is never ragged


@st.cache_data(ttl=600)  # reload from the database at most every 10 minutes
def get_books(source: str) -> pd.DataFrame:
    return queries.load_books(source)


# --- small helpers -------------------------------------------------------------------------

def shorten(text: str, limit: int) -> str:
    """Cut long titles so every card has about the same height (no CSS needed)."""
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def stars(rating: int) -> str:
    return "⭐" * int(rating)


def show_cover(url, title: str, width="stretch") -> None:
    """The cover image, or a book icon when the book has no image (e.g. the sample data)."""
    if pd.notna(url):
        st.image(url, width=width, alt=f"Cover of {title}")
    else:
        st.markdown("## :material/menu_book:", text_alignment="center")


# --- header --------------------------------------------------------------------------------

def show_header(books: pd.DataFrame) -> None:
    st.title("📚 Books to Scrape")
    st.caption("A cosy little shop with every book from books.toscrape.com: browse the shelves, or see what the catalogue says.")
    numbers = queries.kpis(books)
    # st.grid gives equal-width tiles that wrap on narrow screens.
    with st.grid(5, min_column_width=150):
        st.metric("Books", f"{numbers['books']:,}", border=True, help="Titles in the catalogue")
        st.metric("Categories", numbers["categories"], border=True)
        st.metric("Median price", f"£{numbers['median_price']:.2f}", border=True)
        st.metric("Copies in stock", f"{numbers['copies']:,}", border=True, help="Sum of the copies available over all titles")
        st.metric("5-star books", f"{numbers['pct_five_star']:.0f}%", border=True)


# --- sidebar filters -----------------------------------------------------------------------

def sidebar_filters(books: pd.DataFrame) -> pd.DataFrame:
    """Draw the sidebar widgets and return the books that match them."""
    with st.sidebar:
        st.header("Filters", icon=":material/tune:")
        search = st.text_input("Title contains", placeholder="e.g. winter", icon=":material/search:", key="search")
        categories = st.multiselect(
            "Categories", sorted(books["category"].dropna().unique()), placeholder="All categories", key="categories"
        )
        low, high = float(books["price"].min()), float(books["price"].max())
        price_range = st.slider("Price (£)", low, high, (low, high), format="£%.0f", key="price_range")
        # Pills keep all five options visible; required=True means one is always chosen.
        min_rating = st.pills(
            "Minimum rating", [1, 2, 3, 4, 5], default=1, required=True, format_func=lambda n: f"{n}★", key="min_rating"
        )
        sort = st.selectbox("Sort by", list(queries.SORT_OPTIONS), key="sort")
    # No "in stock only" filter: every scraped book is in stock, so it would change nothing.
    return queries.filter_books(books, search, categories, price_range, min_rating, sort=sort)


# --- shelf view ----------------------------------------------------------------------------

@st.dialog("Book details", width="large", icon=":material/menu_book:")
def show_book_dialog(book: pd.Series) -> None:
    """Full details of one book. A dialog keeps the shelf and its page where they were."""
    cover, info = st.columns([1, 2], gap="large")
    with cover:
        show_cover(book["image_url"], book["title"])
    with info:
        st.subheader(book["title"])
        st.markdown(f"{stars(book['rating'])} · :green-badge[{book['category']}]")
        with st.grid(3, min_column_width=120):
            st.metric("Price", f"£{book['price']:.2f}", help="Including tax")
            st.metric("Excl. tax", f"£{book['price_excl_tax']:.2f}")
            st.metric("Copies available", int(book["stock_count"]))
        # Some books have no description on the site, so the column can be empty.
        st.write(book["description"] if pd.notna(book["description"]) else "_No description._")
        st.link_button("Open book page", book["product_url"], icon=":material/open_in_new:")


def show_card(book: pd.Series) -> None:
    """One book on the shelf: cover, title, rating, price, category and a details button."""
    # height="stretch": cards in one grid row share the tallest height, so buttons line up.
    with st.container(border=True, height="stretch"):
        show_cover(book["image_url"], book["title"])
        st.markdown(f"**{shorten(book['title'], 44)}**")
        st.markdown(f"{stars(book['rating'])} · **£{book['price']:.2f}**")
        st.badge(shorten(book["category"], 22), color="green")
        # The key must be unique per card; the upc is unique per book.
        if st.button("Details", key=f"details_{book['upc']}", icon=":material/info:", width="stretch"):
            show_book_dialog(book)


def show_grid(results: pd.DataFrame) -> None:
    """Paginated grid of cards."""
    pages = queries.page_count(len(results), PER_PAGE)
    # A new key whenever the result list changes sends the pager back to page 1.
    page = st.pagination(pages, key=f"page_{hash(tuple(results['upc']))}") if pages > 1 else 1
    with st.grid(4, min_column_width=180, gap="small"):
        for _, book in queries.paginate(results, page, PER_PAGE).iterrows():
            show_card(book)


def show_table(results: pd.DataFrame) -> None:
    st.dataframe(
        results[["image_url", "title", "category", "price", "rating", "stock_count", "product_url"]],
        hide_index=True,
        width="stretch",
        alt="Table of the books that match the filters",
        column_config={
            "image_url": st.column_config.ImageColumn("Cover"),
            "title": "Title",
            "category": "Category",
            "price": st.column_config.NumberColumn("Price", format="£%.2f"),
            "rating": st.column_config.NumberColumn("Rating", format="%d ★"),
            "stock_count": st.column_config.NumberColumn("Copies"),
            "product_url": st.column_config.LinkColumn("Page", display_text="open"),
        },
    )


def show_shelf(results: pd.DataFrame, total: int) -> None:
    with st.container(horizontal=True, vertical_alignment="center"):
        st.markdown(f"**{len(results):,} of {total:,} books**")
        view = st.segmented_control(
            "View",
            ["Grid", "Table"],
            default="Grid",
            required=True,
            format_func=lambda v: f":material/grid_view: {v}" if v == "Grid" else f":material/table_rows: {v}",
            label_visibility="collapsed",
            key="view",
        )
    if results.empty:
        st.info("No book matches the filters. Try loosening them in the sidebar.", icon=":material/search_off:")
    elif view == "Grid":
        show_grid(results)
    else:
        show_table(results)


# --- insights ------------------------------------------------------------------------------

def bar_chart(series: pd.Series, x_label: str, y_label: str) -> None:
    """Bar chart that keeps the order of the series (Streamlit would sort labels A-Z)."""
    frame = series.rename_axis(x_label).reset_index(name=y_label)
    st.bar_chart(frame, x=x_label, y=y_label, sort=False, alt=f"{y_label} by {x_label.lower()}")


def show_insights(books: pd.DataFrame) -> None:
    """Overview of the whole catalogue (deliberately ignores the sidebar filters)."""
    bar_chart(queries.books_per_category(books), "Category", "Books")
    bar_chart(queries.avg_price_by_rating(books), "Rating (stars)", "Average price (£)")
    bar_chart(queries.price_distribution(books), "Price band (£)", "Books")


def load_or_stop() -> tuple[str, pd.DataFrame]:
    """Load the books, or show a clear message and stop the script (instead of a traceback)."""
    try:
        source = queries.default_source()
        books = get_books(source)
    except (ValueError, ConfigError) as error:
        st.error(f"{error}")
        st.info("To try the app without a database, start it with `BOOKS_SOURCE=sample`.")
        st.stop()
    except Exception as error:  # network down, wrong key, table missing ...
        st.error(f"Could not read the books from Supabase ({type(error).__name__}).")
        st.info("Check your internet connection and the values in `.env`, or use `BOOKS_SOURCE=sample`.")
        st.stop()
    if books.empty:
        st.warning("The database has no books yet. Run `python scraper.py` first, or use `BOOKS_SOURCE=sample`.")
        st.stop()
    return source, books


def show_footer(source: str) -> None:
    st.divider()
    text = f"Data source: {source}" + (" (synthetic sample data)" if source == "sample" else "")
    try:
        run = queries.latest_run(source)
    except Exception:  # the footer is optional, never let it break the page
        run = None
    if run:
        text += f" · latest scrape: {str(run['started_at'])[:16].replace('T', ' ')} UTC, {run['mode']}, {run['status']}"
    st.caption(text)


source, books = load_or_stop()

show_header(books)
results = sidebar_filters(books)
shelf_tab, insights_tab = st.tabs([":material/auto_stories: Shelf", ":material/insights: Insights"])
with shelf_tab:
    show_shelf(results, len(books))
with insights_tab:
    show_insights(books)

show_footer(source)
