"""Tests for the db write helpers, using a tiny fake client instead of the real database."""

import db


class FakeResponse:
    def __init__(self, data):
        self.data = data


class FakeQuery:
    """Records the calls made on it; execute() returns the canned data."""

    def __init__(self, client, table):
        self.client, self.table = client, table
        self.calls = []

    def __getattr__(self, method):  # upsert / insert / update / select / eq / range
        def record(*args, **kwargs):
            self.calls.append((method, args, kwargs))
            return self
        return record

    def execute(self):
        self.client.log.append((self.table, self.calls))
        return FakeResponse(self.client.responses.pop(0) if self.client.responses else [])


class FakeClient:
    def __init__(self, responses=()):
        self.responses = list(responses)  # one canned `data` list per execute(), in order
        self.log = []  # (table, calls) per executed query

    def table(self, name):
        return FakeQuery(self, name)


def test_ensure_categories_returns_name_to_id():
    client = FakeClient([[{"id": 2, "name": "Travel"}, {"id": 1, "name": "Poetry"}]])
    assert db.ensure_categories(client, ["Travel", "Poetry", "Travel"]) == {"Travel": 2, "Poetry": 1}
    table, calls = client.log[0]
    assert table == "categories"
    assert calls[0][0] == "upsert"
    assert calls[0][1][0] == [{"name": "Poetry"}, {"name": "Travel"}]  # deduplicated, sorted
    assert calls[0][2] == {"on_conflict": "name"}


def test_ensure_categories_with_no_names_makes_no_request():
    client = FakeClient()
    assert db.ensure_categories(client, []) == {}
    assert client.log == []


def test_upsert_books_drops_first_seen_and_conflicts_on_upc():
    client = FakeClient()
    db.upsert_books(client, [{"upc": "a", "title": "T", "first_seen": "2020-01-01"}])
    table, calls = client.log[0]
    assert table == "books"
    assert calls[0][1][0] == [{"upc": "a", "title": "T"}]
    assert calls[0][2] == {"on_conflict": "upc"}


def test_upsert_books_with_no_rows_makes_no_request():
    client = FakeClient()
    db.upsert_books(client, [])
    assert client.log == []


def test_known_product_urls_pages_until_a_short_page():
    page1 = [{"product_url": f"u{i}"} for i in range(db.PAGE_SIZE)]
    page2 = [{"product_url": "last"}]
    client = FakeClient([page1, page2])
    urls = db.known_product_urls(client)
    assert len(urls) == db.PAGE_SIZE + 1 and "last" in urls
    ranges = [c[1] for _, calls in client.log for c in calls if c[0] == "range"]
    assert ranges == [(0, 999), (1000, 1999)]


def test_start_run_returns_id_and_finish_run_updates_it():
    client = FakeClient([[{"id": 7}]])
    assert db.start_run(client, "incremental") == 7
    db.finish_run(client, 7, {"status": "ok", "errors": 0})
    table, calls = client.log[1]
    assert table == "scrape_runs"
    assert calls[0][0] == "update"
    assert calls[0][1][0]["status"] == "ok" and "finished_at" in calls[0][1][0]
    assert calls[1] == ("eq", ("id", 7), {})
