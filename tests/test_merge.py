"""Повтор того же номера за 10 минут: не вторая заявка, но и ничего не теряется."""
import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app import app, get_notifier, get_store
from kvarta.leads import merge
from kvarta.storage import SqliteStore, TursoStore
from kvarta.telegram import TelegramNotifier, format_lead

PHONE = "+375447778899"


@pytest.fixture
def env(tmp_path):
    store = SqliteStore(str(tmp_path / "leads.db"))
    sent = []

    def handler(request):
        sent.append(json.loads(request.content)["text"])
        return httpx.Response(200, json={"ok": True})

    notifier = TelegramNotifier("T", "1", client=httpx.Client(transport=httpx.MockTransport(handler)))
    app.dependency_overrides[get_store] = lambda: store
    app.dependency_overrides[get_notifier] = lambda: notifier
    yield TestClient(app), store, sent
    app.dependency_overrides.clear()


def post(http, **kw):
    return http.post("/api/lead", json={"name": "Ира", "phone": PHONE, "interest": "question", **kw})


def test_question_then_order_updates_same_lead(env):
    http, store, sent = env
    assert post(http, comment="Что взять для турки?").status_code == 201
    resp = post(http, interest="one_time", items={"ethiopia": 3})
    assert resp.status_code == 200
    assert resp.json()["status"] == "updated"

    [lead] = store.all_leads()  # вторая заявка не создана
    assert lead["interest"] == "one_time"
    assert lead["items"] == "Эфиопия Иргачеффе × 3"
    assert lead["comment"] == "Что взять для турки?"
    assert len(sent) == 2 and sent[1].startswith("<b>Дополнение к заявке: Разовый заказ")


def test_question_after_order_keeps_order_and_appends_comment(env):
    http, store, _ = env
    post(http, interest="one_time", items={"brazil": 2})
    assert post(http, comment="Можно смолоть?").json()["status"] == "updated"
    [lead] = store.all_leads()
    assert lead["interest"] == "one_time"  # вопрос не понижает заказ
    assert lead["items"] == "Бразилия Серрадо × 2"
    assert lead["comment"] == "Можно смолоть?"


def test_same_form_twice_is_plain_duplicate(env):
    http, store, sent = env
    post(http, interest="one_time", items={"brazil": 2}, comment="после 18:00")
    resp = post(http, interest="one_time", items={"brazil": 2}, comment="после 18:00")
    assert resp.json()["status"] == "duplicate"
    assert len(store.all_leads()) == 1
    assert len(sent) == 1  # менеджера не дёргаем повторно


def test_long_utm_is_cut_not_rejected(env):
    http, store, _ = env
    resp = post(http, attribution={"utm_content": "x" * 1000, "fbclid": "y" * 900, "utm_source": 12345})
    assert resp.status_code == 201
    [lead] = store.all_leads()
    assert len(lead["utm_content"]) == 200
    assert len(lead["fbclid"]) == 300
    assert lead["utm_source"] == "12345"


def test_too_long_name_gets_specific_hint(env):
    http, _, _ = env
    resp = http.post("/api/lead", json={"name": "x" * 200, "phone": PHONE, "interest": "question"})
    assert resp.json()["errors"]["name"] == "Имя получилось слишком длинным — до 80 символов."


def test_merge_rules():
    old = {"interest": "subscription", "items": "Колумбия Уила × 2", "items_total": "58", "comment": "утром"}
    assert merge(old, {"interest": "subscription", "items": None, "comment": ""}) is None
    assert merge(old, {"interest": "question", "items": None, "comment": "утром"}) is None
    changed = merge(old, {"interest": "one_time", "items": "Бразилия Серрадо × 1", "items_total": 26, "comment": "и дрипы"})
    assert changed == {"interest": "one_time", "items": "Бразилия Серрадо × 1", "items_total": 26, "comment": "утром\nи дрипы"}


def test_update_message_header():
    lead = {"name": "Ира", "phone": PHONE, "interest": "one_time"}
    assert format_lead(lead, update=True).startswith("<b>Дополнение к заявке: Разовый заказ</b>")


def test_turso_recent_and_update():
    calls = []

    def handler(request):
        body = json.loads(request.content)
        calls.append(body["requests"][0]["stmt"]["sql"].split()[0])
        result = {"cols": [{"name": "id"}, {"name": "interest"}], "rows": [[{"type": "integer", "value": "7"}, {"type": "text", "value": "question"}]], "affected_row_count": 1}
        return httpx.Response(200, json={"results": [{"type": "ok", "response": {"type": "execute", "result": result}}, {"type": "ok", "response": {"type": "close"}}]})

    store = TursoStore("libsql://x.turso.io", "t", client=httpx.Client(transport=httpx.MockTransport(handler)))
    assert store.recent(PHONE) == {"id": "7", "interest": "question"}
    store.update("7", {"interest": "one_time", "items": None, "items_total": None, "comment": ""})
    assert calls == ["SELECT", "UPDATE"]
