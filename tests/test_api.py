import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from app import app, get_store
from kvarta.storage import SqliteStore

VALID = {
    "name": "Ольга",
    "phone": "+375 29 123-45-67",
    "interest": "subscription",
    "comment": "Под турку, если можно",
    "attribution": {
        "utm_source": "instagram",
        "utm_medium": "cpc",
        "utm_campaign": "october_subscription",
        "utm_content": "stories_calendar",
        "landing_page": "https://kvarta.example/?utm_source=instagram",
        "page_url": "https://kvarta.example/#form",
        "referrer": "https://l.instagram.com/",
    },
}


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "leads.db")


@pytest.fixture
def client(db_path):
    store = SqliteStore(db_path)
    store._connect().close()  # создать таблицу заранее, чтобы rows() работал и без заявок
    app.dependency_overrides[get_store] = lambda: store
    yield TestClient(app)
    app.dependency_overrides.clear()


def rows(db_path):
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    return [dict(r) for r in db.execute("SELECT * FROM leads")]


def test_creates_lead_with_attribution(client, db_path):
    resp = client.post("/api/lead", json=VALID)
    assert resp.status_code == 201
    [lead] = rows(db_path)
    assert lead["phone"] == "+375291234567"
    assert lead["utm_source"] == "instagram"
    assert lead["utm_content"] == "stories_calendar"
    assert lead["page_url"].endswith("#form")


def test_bad_phone_gets_readable_hint(client, db_path):
    resp = client.post("/api/lead", json={**VALID, "phone": "+7 912 345-67-89"})
    assert resp.status_code == 422
    assert "белорусский номер" in resp.json()["errors"]["phone"]
    assert rows(db_path) == []


def test_missing_name_and_interest(client):
    resp = client.post("/api/lead", json={**VALID, "name": "   ", "interest": "coffee"})
    errors = resp.json()["errors"]
    assert set(errors) == {"name", "interest"}


def test_same_number_in_other_format_is_duplicate(client, db_path):
    assert client.post("/api/lead", json=VALID).status_code == 201
    resp = client.post("/api/lead", json={**VALID, "phone": "80291234567", "name": "Оля"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "duplicate"
    assert len(rows(db_path)) == 1


def test_double_click_creates_one_lead(client, db_path):
    with ThreadPoolExecutor(max_workers=8) as pool:
        codes = list(pool.map(lambda _: client.post("/api/lead", json=VALID).status_code, range(8)))
    assert codes.count(201) == 1
    assert len(rows(db_path)) == 1


def test_same_number_allowed_after_ten_minutes(client, db_path):
    client.post("/api/lead", json=VALID)
    db = sqlite3.connect(db_path)
    db.execute("UPDATE leads SET created_at = datetime('now', '-11 minutes')")
    db.commit()
    assert client.post("/api/lead", json=VALID).status_code == 201
    assert len(rows(db_path)) == 2


def test_other_number_is_not_blocked(client, db_path):
    client.post("/api/lead", json=VALID)
    assert client.post("/api/lead", json={**VALID, "phone": "+375 33 765-43-21"}).status_code == 201


def test_honeypot_pretends_success_but_saves_nothing(client, db_path):
    resp = client.post("/api/lead", json={**VALID, "website": "http://spam"})
    assert resp.status_code == 201
    assert rows(db_path) == []


def test_storage_failure_returns_clear_message(client):
    class Broken:
        def insert_if_new(self, lead):
            raise ConnectionError("db down")

    app.dependency_overrides[get_store] = lambda: Broken()
    resp = client.post("/api/lead", json=VALID)
    assert resp.status_code == 503
    assert "Попробуйте ещё раз" in resp.json()["message"]
