import re
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import app, get_notifier, get_store
from kvarta.catalog import CATALOG
from kvarta.storage import SqliteStore
from kvarta.telegram import format_lead

BASE = {"name": "Ольга", "phone": "+375291234567", "interest": "one_time"}


@pytest.fixture
def client(tmp_path):
    store = SqliteStore(str(tmp_path / "leads.db"))
    app.dependency_overrides[get_store] = lambda: store
    app.dependency_overrides[get_notifier] = lambda: None
    yield TestClient(app), store
    app.dependency_overrides.clear()


def test_items_saved_as_readable_list_with_server_prices(client):
    http, store = client
    resp = http.post("/api/lead", json={**BASE, "items": {"ethiopia": 2, "drip": 1, "brazil": 0}})
    assert resp.status_code == 201
    [lead] = store.all_leads()
    assert lead["items"] == "Эфиопия Иргачеффе × 2; Дрип-пакеты, ассорти × 1"  # нули отброшены
    assert lead["items_total"] == "82"


def test_lead_without_items_is_fine(client):
    http, store = client
    assert http.post("/api/lead", json=BASE).status_code == 201
    assert store.all_leads()[0]["items"] is None


@pytest.mark.parametrize("items", [{"latte": 1}, {"ethiopia": -1}, {"ethiopia": 21}, {"ethiopia": "много"}])
def test_bad_items_rejected_with_hint(client, items):
    http, _ = client
    resp = http.post("/api/lead", json={**BASE, "items": items})
    assert resp.status_code == 422
    assert "обновите страницу" in resp.json()["errors"]["items"]


def test_telegram_lists_items_and_total():
    lead = {**BASE, "items": "Эфиопия Иргачеффе × 2; Дрип-пакеты, ассорти × 1", "items_total": 82}
    text = format_lead(lead)
    assert "☕ Эфиопия Иргачеффе × 2" in text
    assert "☕ Дрип-пакеты, ассорти × 1" in text
    assert "≈ 82 BYN по прайсу" in text


def test_subscription_items_are_wishes_without_total():
    lead = {**BASE, "interest": "subscription", "items": "Колумбия Уила × 2", "items_total": 58}
    assert "BYN по прайсу" not in format_lead(lead)


def test_page_prices_match_server_catalog():
    html = (Path(__file__).parent.parent / "public" / "index.html").read_text(encoding="utf-8")
    on_page = {sku: int(price) for sku, price in re.findall(r'data-sku="(\w+)"[^>]*data-price="(\d+)"', html)}
    assert on_page == {sku: price for sku, (_, price) in CATALOG.items()}
