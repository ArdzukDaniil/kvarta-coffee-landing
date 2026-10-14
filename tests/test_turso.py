import json

import httpx
import pytest

from kvarta.storage import TursoStore

LEAD = {"name": "Ольга", "phone": "+375291234567", "interest": "subscription", "utm_source": "instagram"}


def store_with(responder):
    seen = []

    def handler(request: httpx.Request):
        body = json.loads(request.content)
        seen.append((str(request.url), body))
        return responder(body)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    return TursoStore("libsql://kvarta-test.turso.io", "token", client=client), seen


def ok(affected):
    def responder(body):
        results = [
            {"type": "ok", "response": {"type": "execute", "result": {"affected_row_count": affected}}}
            for r in body["requests"] if r["type"] == "execute"
        ]
        results.append({"type": "ok", "response": {"type": "close"}})
        return httpx.Response(200, json={"results": results})
    return responder


def test_sends_pipeline_with_schema_once_and_typed_args():
    store, seen = store_with(ok(1))
    assert store.insert_if_new(LEAD) is True
    assert store.insert_if_new(LEAD) is True

    url, first = seen[0]
    assert url == "https://kvarta-test.turso.io/v2/pipeline"
    assert [r["type"] for r in first["requests"]] == ["execute", "execute", "execute", "close"]  # 2 схемы + insert
    insert_args = first["requests"][2]["stmt"]["args"]
    assert {"type": "text", "value": "+375291234567"} in insert_args
    assert {"type": "null"} in insert_args  # пустые utm уходят как NULL

    _, second = seen[1]
    assert [r["type"] for r in second["requests"]] == ["execute", "close"]  # схема уже создана


def test_duplicate_when_no_rows_inserted():
    store, _ = store_with(ok(0))
    assert store.insert_if_new(LEAD) is False


def test_turso_error_raises():
    def responder(body):
        return httpx.Response(200, json={"results": [{"type": "error", "error": {"message": "no such table"}}, {"type": "ok"}]})

    store, _ = store_with(responder)
    with pytest.raises(RuntimeError, match="no such table"):
        store.insert_if_new(LEAD)


def test_http_error_raises():
    store, _ = store_with(lambda body: httpx.Response(401, json={}))
    with pytest.raises(httpx.HTTPStatusError):
        store.insert_if_new(LEAD)
