"""Parser tests on saved HTML pages (tests/fixtures), so they run offline."""

from pathlib import Path

import pytest

import parse

FIXTURES = Path(__file__).parent / "fixtures"
BASE = "https://books.toscrape.com/catalogue/"


def read(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def test_listing_returns_20_absolute_urls_and_next_page():
    urls, next_url = parse.parse_listing(read("listing_page1.html"), BASE + "page-1.html")
    assert len(urls) == 20
    assert urls[0] == BASE + "a-light-in-the-attic_1000/index.html"
    assert next_url == BASE + "page-2.html"


def test_listing_without_next_link_returns_none():
    html = b'<article class="product_pod"><h3><a href="x_1/index.html">x</a></h3></article>'
    urls, next_url = parse.parse_listing(html, BASE + "page-50.html")
    assert urls == [BASE + "x_1/index.html"]
    assert next_url is None


def test_book_with_description():
    url = BASE + "a-light-in-the-attic_1000/index.html"
    book = parse.parse_book(read("book_with_description.html"), url)
    assert book["upc"] == "a897fe39b1053632"
    assert book["title"] == "A Light in the Attic"
    assert book["category"] == "Poetry"
    assert book["price"] == 51.77
    assert book["price_excl_tax"] == 51.77
    assert book["tax"] == 0.0
    assert book["in_stock"] is True
    assert book["stock_count"] == 22
    assert book["rating"] == 3
    assert book["description"].startswith("It's hard to imagine a world")
    assert book["image_url"] == "https://books.toscrape.com/media/cache/fe/72/fe72f0532301ec28892ae79a629a293c.jpg"
    assert book["product_url"] == url


def test_book_without_description_gives_none():
    url = BASE + "alice-in-wonderland-alices-adventures-in-wonderland-1_5/index.html"
    book = parse.parse_book(read("book_without_description.html"), url)
    assert book["description"] is None
    assert book["upc"] == "cd2a2a70dd5d176d"
    assert book["category"] == "Classics"
    assert book["rating"] == 1  # the page also shows other books' ratings; ours is the first one
    assert book["title"] == "Alice in Wonderland (Alice's Adventures in Wonderland #1)"


def test_pound_sign_is_not_garbled():
    # Pass bytes: the price must parse as a number, not fail on "Â£".
    book = parse.parse_book(read("book_with_description.html"), BASE + "x_1/index.html")
    assert isinstance(book["price"], float)


@pytest.mark.parametrize("word,number", [("One", 1), ("Five", 5)])
def test_rating_words(word, number):
    assert parse.RATING_WORDS[word] == number
