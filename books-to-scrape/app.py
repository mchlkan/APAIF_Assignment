"""Streamlit app: browse the scraped books. Start with: streamlit run app.py"""

import pandas as pd
import streamlit as st

import queries

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


source = queries.default_source()
books = get_books(source)

st.title("📚 Books to Scrape")
results = sidebar_filters(books)
(browse_tab,) = st.tabs(["Browse"])
with browse_tab:
    show_browse(results, len(books))
