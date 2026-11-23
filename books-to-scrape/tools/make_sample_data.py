"""Write tests/fixtures/sample_books.csv: 60 SYNTHETIC books (not scraped, not real).

Why: the app and its tests can run without a Supabase project or a finished scraper.
The columns are the same as what queries.load_books() returns for real data
(one row per book, category as a name instead of an id).

Run from anywhere: python books-to-scrape/tools/make_sample_data.py
A fixed random seed makes the output identical on every run.
"""

import csv
import random
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "sample_books.csv"

COLUMNS = [
    "upc", "title", "category", "price", "price_excl_tax", "tax", "in_stock", "stock_count",
    "rating", "description", "image_url", "product_url", "first_seen", "last_scraped",
]
CATEGORIES = ["Travel", "Mystery", "Historical Fiction", "Poetry", "Science", "Romance", "Fantasy", "Nonfiction"]
WORDS = ["Silent", "River", "Garden", "Last", "Winter", "Paper", "Glass", "Northern", "Hidden", "Letters",
         "Atlas", "Lantern", "Orchard", "Harbor", "Echo", "Summer", "Stone", "Map", "Island", "Clock"]


def make_rows(n: int = 60, seed: int = 42) -> list[dict]:
    rng = random.Random(seed)
    rows = []
    for i in range(1, n + 1):
        price = round(rng.uniform(10, 60), 2)
        in_stock = rng.random() > 0.15  # some out of stock, so the "in stock only" filter has something to do
        has_description = rng.random() > 0.1  # some missing, like on the real site
        title = f"Sample {i:02d}: The {rng.choice(WORDS)} {rng.choice(WORDS)}"
        rows.append({
            "upc": f"sample{i:04d}",
            "title": title,
            "category": CATEGORIES[(i - 1) % len(CATEGORIES)] if i <= 40 else rng.choice(CATEGORIES),
            "price": price,
            "price_excl_tax": price,
            "tax": 0.0,
            "in_stock": in_stock,
            "stock_count": rng.randint(1, 22) if in_stock else 0,
            "rating": rng.randint(1, 5),
            "description": f"Synthetic description for {title}." if has_description else "",
            "image_url": "",  # no real cover images for synthetic books
            "product_url": f"https://example.invalid/sample-books/{i:02d}",
            "first_seen": "2026-11-23T10:00:00+00:00",
            "last_scraped": "2026-11-23T10:00:00+00:00",
        })
    return rows


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    rows = make_rows()
    with OUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} synthetic books to {OUT}")


if __name__ == "__main__":
    main()
