"""Pure HTML -> data functions for books.toscrape.com (no network, so they are easy to test).

Always pass the response *bytes* (resp.content), not resp.text: requests guesses ISO-8859-1 for
this site and would turn "£" into "Â£". BeautifulSoup reads the page's own UTF-8 declaration.
"""

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

# The rating is only a CSS class on the page ("star-rating Three").
RATING_WORDS = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}


def parse_listing(html: bytes, page_url: str) -> tuple[list[str], str | None]:
    """Return (absolute product URLs on this listing page, absolute URL of the next page or None)."""
    soup = BeautifulSoup(html, "html.parser")
    book_urls = [
        urljoin(page_url, a["href"])  # links are relative, so join them with the page URL
        for a in soup.select("article.product_pod h3 a")
    ]
    next_link = soup.select_one("li.next a")
    next_url = urljoin(page_url, next_link["href"]) if next_link else None
    return book_urls, next_url


def _money(text: str) -> float:
    """'£51.77' -> 51.77"""
    return float(text.replace("£", "").strip())


def parse_book(html: bytes, url: str) -> dict:
    """Parse one product page into a dict with the books columns plus `category` (the name)."""
    soup = BeautifulSoup(html, "html.parser")

    # The info table is label/value pairs: {"UPC": "...", "Price (excl. tax)": "£51.77", ...}
    table = {
        row.th.get_text(strip=True): row.td.get_text(strip=True)
        for row in soup.select("table.table-striped tr")
    }

    # "In stock (22 available)" -> in_stock True, stock_count 22
    availability = table["Availability"]
    match = re.search(r"\((\d+) available\)", availability)
    stock_count = int(match.group(1)) if match else None

    # Look inside .product_main: the "related books" part of the page has star ratings too.
    rating_classes = soup.select_one(".product_main p.star-rating")["class"]
    rating = next(RATING_WORDS[c] for c in rating_classes if c in RATING_WORDS)

    # The description paragraph follows the #product_description header; some books have none.
    header = soup.select_one("#product_description")
    paragraph = header.find_next_sibling("p") if header else None
    description = paragraph.get_text(strip=True) if paragraph else None

    image = soup.select_one("#product_gallery img")
    # Breadcrumb is Home > Books > <category> > <title>, so the category is the 3rd item.
    category = soup.select(".breadcrumb li")[2].get_text(strip=True)

    return {
        "upc": table["UPC"],
        "title": soup.select_one("h1").get_text(strip=True),
        "category": category,
        "price": _money(table["Price (incl. tax)"]),
        "price_excl_tax": _money(table["Price (excl. tax)"]),
        "tax": _money(table["Tax"]),
        "in_stock": availability.startswith("In stock"),
        "stock_count": stock_count,
        "rating": rating,
        "description": description,
        "image_url": urljoin(url, image["src"]) if image else None,
        "product_url": url,
    }
