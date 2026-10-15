import json
from datetime import datetime, timezone

import httpx
from fastapi.testclient import TestClient

from app import app, get_notifier, get_store
from kvarta.storage import SqliteStore
from kvarta.telegram import TelegramNotifier, format_lead

LEAD = {
    "name": "Ольга <script>",
    "phone": "+375291234567",
    "interest": "subscription",
    "comment": "Под турку & помол",
    "utm_source": "instagram",
    "utm_medium": "cpc",
    "utm_campaign": "october",
    "utm_content": "stories_calendar",
    "landing_page": "https://kvarta.example/?utm_source=instagram",
}


def test_message_has_source_and_minsk_time_and_escapes_input():
    text = format_lead(LEAD, now=datetime(2026, 10, 15, 9, 30, tzinfo=timezone.utc))
    assert "Новая заявка: Подписка" in text
    assert "Ольга &lt;script&gt;" in text  # ввод человека не ломает HTML-разметку Telegram
    assert "Под турку &amp; помол" in text
    assert "Источник: instagram / cpc / october" in text
    assert "Объявление: stories_calendar" in text
    assert "15.10.2026 12:30 (Минск)" in text


def test_click_id_without_utm_is_named():
    text = format_lead({"name": "А", "phone": "+375291234567", "interest": "question", "yclid": "123"})
    assert "Источник: Яндекс (yclid)" in text


def notifier_with(status, calls):
    def handler(request):
        calls.append(json.loads(request.content))
        return httpx.Response(status, json={"ok": status == 200})
    return TelegramNotifier("TOKEN", "-100500", client=httpx.Client(transport=httpx.MockTransport(handler)))


def test_send_posts_html_message_to_chat():
    calls = []
    assert notifier_with(200, calls).send(LEAD) is True
    assert calls[0]["chat_id"] == "-100500"
    assert calls[0]["parse_mode"] == "HTML"


def test_telegram_failure_does_not_break_lead(tmp_path):
    calls = []
    store = SqliteStore(str(tmp_path / "leads.db"))
    app.dependency_overrides[get_store] = lambda: store
    app.dependency_overrides[get_notifier] = lambda: notifier_with(500, calls)
    try:
        resp = TestClient(app).post("/api/lead", json={"name": "Ольга", "phone": "+375291234567", "interest": "question"})
    finally:
        app.dependency_overrides.clear()
    assert resp.status_code == 201  # заявка сохранена, хоть Telegram и упал
    assert len(calls) == 1


def test_duplicate_is_not_sent_twice(tmp_path):
    calls = []
    store = SqliteStore(str(tmp_path / "leads.db"))
    app.dependency_overrides[get_store] = lambda: store
    app.dependency_overrides[get_notifier] = lambda: notifier_with(200, calls)
    try:
        client = TestClient(app)
        body = {"name": "Ольга", "phone": "+375291234567", "interest": "question"}
        client.post("/api/lead", json=body)
        client.post("/api/lead", json=body)
    finally:
        app.dependency_overrides.clear()
    assert len(calls) == 1
