"""Streamlit app: a small bookshop for the scraped books.

Start it from inside this folder (so .streamlit/config.toml, the theme, is found):
    cd books-to-scrape && streamlit run app.py
"""

import altair as alt
import pandas as pd
import streamlit as st

import queries
from db import ConfigError

st.set_page_config(page_title="Books to Scrape", page_icon="📚", layout="wide")

# Card layout: every card is built from fixed-height zones so the same element sits at the same
# height in every card, whatever the cover shape or title length.
COVER_WIDTH, COVER_ZONE = 140, 236  # covers are at most ~1.6x taller than wide
TITLE_ZONE, TITLE_CHARS = 72, 40  # room for exactly two lines of bold text
MINI_COVER_WIDTH, MINI_COVER_ZONE, MINI_TITLE_ZONE = 90, 148, 66
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


def show_cover(url, title: str, width) -> None:
    """The cover image at a fixed width, or a book icon when there is no image (sample data)."""
    if pd.notna(url):
        st.image(url, width=width, alt=f"Cover of {title}")
    else:
        st.markdown("## :material/menu_book:", text_alignment="center")


def cover_zone(url, title: str, width: int, height: int) -> None:
    """Cover in a fixed-height, centred zone: the next element then always starts at the same y."""
    with st.container(height=height, border=False, horizontal_alignment="center"):
        show_cover(url, title, width)


def title_zone(text: str, height: int, chars: int, small: bool = False) -> None:
    """Title in a fixed-height zone; the text is cut so it never needs a third line."""
    shown = shorten(text, chars)
    with st.container(height=height, border=False):
        if small:
            st.caption(f"**{shown}**")
        else:
            st.markdown(f"**{shown}**")


# --- header --------------------------------------------------------------------------------

def show_header(books: pd.DataFrame) -> None:
    st.title("📚 Books to Scrape")
    st.caption("A cosy little shop with every book from books.toscrape.com: browse the shelves, or see what the catalogue says.")
    numbers = queries.kpis(books)
    # st.grid gives equal-width tiles that wrap together. Four tiles stay on one row even in a
    # narrow window (five wrapped 4+1); the category count is already visible in the sidebar filter.
    with st.grid(4, min_column_width=80, gap="xsmall"):
        st.metric("Books", f"{numbers['books']:,}", border=True, help="Titles in the catalogue")
        st.metric("Median price", f"£{numbers['median_price']:.2f}", border=True)
        st.metric("In stock", f"{numbers['copies']:,}", border=True, help="Copies available, summed over all titles")
        st.metric("5-star", f"{numbers['pct_five_star']:.0f}%", border=True, help="Share of books rated 5 stars")


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
        # One compact row: "Any" means no minimum, "3+" means three stars or more.
        min_rating = st.segmented_control(
            "Minimum stars", [1, 2, 3, 4, 5], default=1, required=True, width="stretch",
            format_func=lambda n: "Any" if n == 1 else f"{n}+" if n < 5 else "5", key="min_rating",
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
        show_cover(book["image_url"], book["title"], "stretch")
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
    """One book on the shelf, as fixed-height zones: cover, title, rating and price, category, button."""
    # height="stretch": cards in one grid row share the tallest height.
    with st.container(border=True, height="stretch"):
        cover_zone(book["image_url"], book["title"], COVER_WIDTH, COVER_ZONE)
        title_zone(book["title"], TITLE_ZONE, TITLE_CHARS)
        st.markdown(f"{stars(book['rating'])} · **£{book['price']:.2f}**")
        st.badge(shorten(book["category"], 20), color="green")
        st.space("stretch")  # pushes the button to the bottom of every card
        # The key must be unique per card; the upc is unique per book.
        if st.button("Details", key=f"details_{book['upc']}", icon=":material/info:", width="stretch"):
            show_book_dialog(book)


def show_grid(results: pd.DataFrame) -> None:
    """Paginated grid of cards."""
    pages = queries.page_count(len(results), PER_PAGE)
    # A new key whenever the result list changes sends the pager back to page 1.
    page = st.pagination(pages, key=f"page_{hash(tuple(results['upc']))}") if pages > 1 else 1
    with st.grid(4, min_column_width=220, gap="small"):
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

def insight_card(title: str, icon: str, takeaway: str):
    """A bordered card with a heading and a one-sentence takeaway; the caller adds the chart."""
    box = st.container(border=True)
    with box:
        st.markdown(f"#### {icon} {title}")  # smaller than st.subheader, so it fits on one line
        st.markdown(takeaway)
    return box


def show_mini_shelf(books: pd.DataFrame, detail) -> None:
    """A row of small cover cards with the same fixed zones as the big cards."""
    with st.grid(6, min_column_width=130):
        for _, book in books.iterrows():
            with st.container(border=True, height="stretch"):
                cover_zone(book["image_url"], book["title"], MINI_COVER_WIDTH, MINI_COVER_ZONE)
                title_zone(book["title"], MINI_TITLE_ZONE, 26, small=True)
                st.caption(detail(book))


def category_chart(prices: pd.DataFrame) -> alt.Chart:
    """Horizontal bars, cheapest first; cheapest and priciest are accented, placeholders greyed."""
    colours = {"cheapest": "#2F5D50", "priciest": "#8C3B3B", "other": "#9DB8AA", "placeholder": "#C4BDB0"}
    labels = {"cheapest": "Cheapest", "priciest": "Priciest", "other": "Other genre", "placeholder": "Placeholder"}
    marked = queries.mark_category_prices(prices).assign(Kind=lambda f: f["kind"].map(labels))
    return (
        alt.Chart(marked)
        .mark_bar()
        .encode(
            x=alt.X("avg_price:Q", title="Average price (£)"),
            y=alt.Y("category:N", sort=list(marked["category"]), title=None),  # keep the cheapest-first order
            color=alt.Color(
                "Kind:N", title=None,
                scale=alt.Scale(domain=[labels[k] for k in colours], range=list(colours.values())),
                legend=alt.Legend(orient="bottom"),
            ),
            tooltip=["category", "books", alt.Tooltip("avg_price:Q", format=".2f", title="Average price (£)")],
        )
        .properties(height=max(200, 18 * len(marked)))
    )


def rating_card(books: pd.DataFrame, found: dict) -> None:
    top = found["top_rating"]
    with insight_card("Ratings", ":material/star:", f"**{top['stars']}★ is the most common rating** ({top['share']:.0f}% of books)."):
        ratings = queries.rating_distribution(books).rename_axis("Stars").reset_index(name="Books")
        st.bar_chart(ratings, x="Stars", y="Books", height=220, alt="Number of books per star rating")


def price_band_card(books: pd.DataFrame, found: dict) -> None:
    band = found["busiest_band"]
    text = f"**The busiest price band is £{band['band']}** with {band['books']} books."
    with insight_card("Prices", ":material/payments:", text):
        bands = queries.price_distribution(books, 5).rename_axis("Price band (£)").reset_index(name="Books")
        st.bar_chart(bands, x="Price band (£)", y="Books", sort=False, height=220, alt="Number of books per £5 price band")


def rating_vs_price_card(books: pd.DataFrame, found: dict) -> None:
    gap = found["rating_gap"]
    if not gap:
        return
    facts = (
        f"{gap['low_rating']}★ books cost £{gap['low_price']:.2f} on average, "
        f"{gap['high_rating']}★ books £{gap['high_price']:.2f}."
    )
    # Say "no link" only when the gap is small (under 10% of the low price); otherwise report the gap.
    if abs(gap["difference"]) < 0.10 * gap["low_price"]:
        text = f"**Rating doesn't drive price.** {facts}"
    else:
        text = f"**Better-rated books cost {'more' if gap['difference'] > 0 else 'less'}.** {facts}"
    with insight_card("Quality vs price", ":material/balance:", text):
        by_rating = queries.avg_price_by_rating(books).rename_axis("Stars").reset_index(name="Average price (£)")
        st.bar_chart(by_rating, x="Stars", y="Average price (£)", height=220, alt="Average price per star rating")


def category_card(books: pd.DataFrame, found: dict, min_books: int) -> None:
    cheapest, priciest = found["cheapest_category"], found["priciest_category"]
    if not (cheapest and priciest):
        return
    text = (
        f"**{cheapest['category']} is the cheapest category** (£{cheapest['avg_price']:.2f} on average) and "
        f"**{priciest['category']} the priciest** (£{priciest['avg_price']:.2f}). "
        f"Only categories with at least {min_books} books are shown."
    )
    with insight_card("Price by category", ":material/category:", text):
        st.altair_chart(
            category_chart(queries.category_prices(books, min_books)),
            alt=f"Average price per category: cheapest {cheapest['category']}, priciest {priciest['category']}",
        )
        if books["category"].isin(queries.PLACEHOLDER_CATEGORIES).any():
            st.caption(
                "\"Default\" and \"Add a comment\" (grey) are the source site's own placeholder categories, "
                "not real genres, so read them with care."
            )


def show_insights(books: pd.DataFrame) -> None:
    """Findings about the whole catalogue (deliberately ignores the sidebar filters)."""
    st.caption("These findings describe the whole catalogue, not the filtered selection in the sidebar.")
    # The sample has only 60 books, so no category reaches 10; use a lower bar there.
    min_books = 10 if len(books) >= 200 else 5
    found = queries.takeaways(books, min_books)

    # A grid (not columns) so the three small cards stack on a narrow window.
    with st.grid(3, min_column_width=240):
        rating_card(books, found)
        price_band_card(books, found)
        rating_vs_price_card(books, found)
    category_card(books, found, min_books)

    st.markdown("#### :material/savings: Best value: cheapest 5-star books")
    show_mini_shelf(queries.best_value(books), lambda b: f"£{b['price']:.2f} · 5★")
    st.markdown("#### :material/inventory_2: Fullest shelves: most copies in stock")
    show_mini_shelf(queries.most_stocked(books), lambda b: f"{int(b['stock_count'])} copies · £{b['price']:.2f}")


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


def show_navigation(results: pd.DataFrame) -> str:
    """Shelf / Insights switch plus the 'Surprise me' button. Returns the chosen view."""
    # A segmented control + if (not st.tabs) so only the visible view is computed and drawn.
    with st.container(horizontal=True, vertical_alignment="center"):
        view = st.segmented_control(
            "View", ["Shelf", "Insights"], default="Shelf", required=True, key="nav",
            format_func=lambda v: ":material/auto_stories: Shelf" if v == "Shelf" else ":material/insights: Insights",
            label_visibility="collapsed",
        )
        # Random pick from the current filter result, shown in the same dialog as the cards.
        if st.button("Surprise me", icon=":material/casino:", key="surprise", disabled=results.empty):
            show_book_dialog(results.sample(1).iloc[0])
    return view


view = show_navigation(results)
if view == "Shelf":
    show_shelf(results, len(books))
else:
    show_insights(books)

show_footer(source)
