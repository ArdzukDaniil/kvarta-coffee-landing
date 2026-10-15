import csv
import json

import httpx

from kvarta.storage import SqliteStore, TursoStore
from tools.export_leads import export, safe_cell

LEAD = {"name": "Ольга", "phone": "+375291234567", "interest": "subscription", "utm_source": "instagram", "utm_content": "stories"}


def test_csv_for_excel_with_minsk_time(tmp_path):
    store = SqliteStore(str(tmp_path / "leads.db"))
    store.insert_if_new(LEAD)
    rows = store.all_leads()
    rows[0]["created_at"] = "2026-10-15 09:30:00"  # UTC
    out = tmp_path / "leads.csv"
    export(rows, out)

    raw = out.read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf")  # BOM для Excel
    [header, row] = list(csv.reader(out.open(encoding="utf-8-sig"), delimiter=";"))
    data = dict(zip(header, row))
    assert data["Когда (Минск)"] == "15.10.2026 12:30"
    assert data["Интерес"] == "Подписка"
    assert data["Источник"] == "instagram"
    assert data["Объявление"] == "stories"


def test_turso_all_leads_maps_columns():
    def handler(request):
        return httpx.Response(200, json={"results": [
            {"type": "ok", "response": {"type": "execute", "result": {
                "cols": [{"name": "id"}, {"name": "phone"}],
                "rows": [[{"type": "integer", "value": "1"}, {"type": "text", "value": "+375291234567"}]],
            }}},
            {"type": "ok", "response": {"type": "close"}},
        ]})

    store = TursoStore("libsql://x.turso.io", "t", client=httpx.Client(transport=httpx.MockTransport(handler)))
    assert store.all_leads() == [{"id": "1", "phone": "+375291234567"}]


def test_formulas_from_visitors_are_neutralized():
    assert safe_cell('=HYPERLINK("http://evil","x")').startswith("'=")
    assert safe_cell("@SUM(1)") == "'@SUM(1)"
    assert safe_cell("+375291234567") == "+375291234567"  # нормальный телефон остаётся как есть
    assert safe_cell("Ольга") == "Ольга"
