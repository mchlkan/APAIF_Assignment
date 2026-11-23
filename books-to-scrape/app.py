"""Streamlit app: browse the scraped books. Start with: streamlit run app.py"""

import pandas as pd
import streamlit as st

import queries
from db import ConfigError

st.set_page_config(page_title="Books to Scrape", page_icon="📚", layout="wide")


@st.cache_data(ttl=600)  # reload from the database at most every 10 minutes
def get_books(source: str) -> pd.DataFrame:
    return queries.load_books(source)


def sidebar_filters(books: pd.DataFrame) -> pd.DataFrame:
    """Draw the sidebar widgets and return the books that match them."""
    st.sidebar.header("Filters")
    search = st.sidebar.text_input("Title contains")
    categories = st.sidebar.multiselect("Categories", sorted(books["category"].dropna().unique()))
    low, high = float(books["price"].min()), float(books["price"].max())
    price_range = st.sidebar.slider("Price (£)", low, high, (low, high))
    min_rating = st.sidebar.slider("Minimum rating (stars)", 1, 5, 1)
    in_stock_only = st.sidebar.checkbox("In stock only")
    sort = st.sidebar.selectbox("Sort by", list(queries.SORT_OPTIONS))
    return queries.filter_books(
        books, search, categories, price_range, min_rating, in_stock_only, sort
    )


def show_browse(results: pd.DataFrame, total: int) -> None:
    st.caption(f"{len(results)} of {total} books")
    if results.empty:
        st.info("No book matches the filters. Try loosening them in the sidebar.")
        return
    st.dataframe(
        results[["image_url", "title", "category", "price", "rating", "in_stock", "product_url"]],
        hide_index=True,
        width="stretch",
        column_config={
            "image_url": st.column_config.ImageColumn("Cover"),
            "title": "Title",
            "category": "Category",
            "price": st.column_config.NumberColumn("Price", format="£%.2f"),
            "rating": st.column_config.NumberColumn("Rating", format="%d ★"),
            "in_stock": st.column_config.CheckboxColumn("In stock"),
            "product_url": st.column_config.LinkColumn("Page", display_text="open"),
        },
    )


def show_detail(results: pd.DataFrame) -> None:
    """Pick one of the filtered books and show its details."""
    if results.empty:
        st.info("No book matches the filters.")
        return
    # Choose by upc (unique) but display the title; titles alone could repeat.
    titles = dict(zip(results["upc"], results["title"]))
    upc = st.selectbox("Choose a book", list(titles), format_func=titles.get)
    book = results[results["upc"] == upc].iloc[0]

    cover, info = st.columns([1, 3])
    if pd.notna(book["image_url"]):
        cover.image(book["image_url"], width=200)
    info.subheader(book["title"])
    info.write(f"**Category:** {book['category']}")
    info.write(f"**Rating:** {'★' * int(book['rating'])}{'☆' * (5 - int(book['rating']))}")
    info.write(f"**Price:** £{book['price']:.2f} (excl. tax £{book['price_excl_tax']:.2f})")
    if book["in_stock"]:
        info.write(f"**Availability:** in stock ({int(book['stock_count'])} available)")
    else:
        info.write("**Availability:** out of stock")
    # Some books have no description on the site, so the column can be empty.
    info.write(book["description"] if pd.notna(book["description"]) else "_No description._")
    info.link_button("Open book page", book["product_url"])


def bar_chart(series: pd.Series, x_label: str, y_label: str) -> None:
    """Bar chart that keeps the order of the series (Streamlit would sort labels A-Z)."""
    frame = series.rename_axis(x_label).reset_index(name=y_label)
    st.bar_chart(frame, x=x_label, y=y_label, sort=False)


def show_insights(books: pd.DataFrame) -> None:
    """Overview of the whole catalogue (deliberately ignores the sidebar filters)."""
    numbers = queries.kpis(books)
    tiles = st.columns(4)
    tiles[0].metric("Books", numbers["books"])
    tiles[1].metric("Categories", numbers["categories"])
    tiles[2].metric("Average price", f"£{numbers['avg_price']:.2f}")
    tiles[3].metric("In stock", f"{numbers['pct_in_stock']:.0f}%")

    left, right = st.columns(2)
    with left:
        st.subheader("Books per category (top 15)")
        bar_chart(queries.books_per_category(books), "Category", "Books")
        st.subheader("Average price by rating")
        bar_chart(queries.avg_price_by_rating(books), "Rating (stars)", "Average price (£)")
    with right:
        st.subheader("Price distribution (£10 bands)")
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

st.title("📚 Books to Scrape")
results = sidebar_filters(books)
browse_tab, detail_tab, insights_tab = st.tabs(["Browse", "Book detail", "Insights"])
with browse_tab:
    show_browse(results, len(books))
with detail_tab:
    show_detail(results)
with insights_tab:
    show_insights(books)

show_footer(source)
