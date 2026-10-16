"""Хранилище заявок: SQLite локально и в тестах, Turso (libSQL) на Vercel.

SQL одинаковый в обоих случаях — Turso это SQLite в облаке. Защита от дублей
сделана одним INSERT ... WHERE NOT EXISTS: SQLite выполняет запись атомарно,
поэтому даже два одновременных запроса (двойной клик) не создадут две заявки.
"""
import sqlite3
from typing import Protocol

import httpx

DEDUP_WINDOW_MINUTES = 10

LEAD_COLUMNS = (
    "name", "phone", "interest", "comment", "items", "items_total",
    "utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term",
    "yclid", "gclid", "fbclid",
    "referrer", "landing_page", "page_url", "user_agent",
)

SCHEMA = [
    f"""CREATE TABLE IF NOT EXISTS leads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        {", ".join(f"{c} TEXT" for c in LEAD_COLUMNS)}
    )""",
    "CREATE INDEX IF NOT EXISTS leads_phone_created ON leads (phone, created_at)",
]

_placeholders = ", ".join("?" for _ in LEAD_COLUMNS)
INSERT_IF_NEW = f"""
    INSERT INTO leads ({", ".join(LEAD_COLUMNS)})
    SELECT {_placeholders}
    WHERE NOT EXISTS (
        SELECT 1 FROM leads
        WHERE phone = ? AND created_at > datetime('now', '-{DEDUP_WINDOW_MINUTES} minutes')
    )
"""


SELECT_ALL = f"SELECT id, created_at, {', '.join(LEAD_COLUMNS)} FROM leads ORDER BY id DESC"
SELECT_RECENT = f"""
    SELECT id, interest, items, items_total, comment FROM leads
    WHERE phone = ? AND created_at > datetime('now', '-{DEDUP_WINDOW_MINUTES} minutes')
    ORDER BY id DESC LIMIT 1
"""
UPDATE_LEAD = "UPDATE leads SET interest = ?, items = ?, items_total = ?, comment = ? WHERE id = ?"


class LeadStore(Protocol):
    def insert_if_new(self, lead: dict) -> bool:
        """Сохранить заявку. False — такой номер уже был за последние 10 минут."""

    def all_leads(self) -> list[dict]:
        """Все заявки, новые сверху."""

    def recent(self, phone: str) -> dict | None:
        """Последняя заявка с этим номером за 10 минут (для дополнения)."""

    def update(self, lead_id, fields: dict) -> None:
        """Обновить интерес, кофе и комментарий заявки."""


def _args(lead: dict) -> list:
    return [lead.get(c) for c in LEAD_COLUMNS] + [lead["phone"]]


class SqliteStore:
    def __init__(self, path: str):
        self.path = path

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path, timeout=5)
        for sql in SCHEMA:  # IF NOT EXISTS — дёшево, и база переживёт удаление файла
            db.execute(sql)
        return db

    def insert_if_new(self, lead: dict) -> bool:
        with self._connect() as db:
            cur = db.execute(INSERT_IF_NEW, _args(lead))
            return cur.rowcount == 1

    def all_leads(self) -> list[dict]:
        with self._connect() as db:
            db.row_factory = sqlite3.Row
            return [dict(r) for r in db.execute(SELECT_ALL)]

    def recent(self, phone: str) -> dict | None:
        with self._connect() as db:
            db.row_factory = sqlite3.Row
            row = db.execute(SELECT_RECENT, [phone]).fetchone()
            return dict(row) if row else None

    def update(self, lead_id, fields: dict) -> None:
        with self._connect() as db:
            db.execute(UPDATE_LEAD, _update_args(lead_id, fields))


class TursoStore:
    """Turso через HTTP API (/v2/pipeline): без нативных зависимостей, работает в serverless."""

    def __init__(self, url: str, token: str, client: httpx.Client | None = None):
        self.endpoint = url.replace("libsql://", "https://", 1).rstrip("/") + "/v2/pipeline"
        self.client = client or httpx.Client(headers={"Authorization": f"Bearer {token}"}, timeout=8)
        self._schema_ready = False

    def _execute(self, statements: list[tuple[str, list]]) -> list[dict]:
        requests = [
            {"type": "execute", "stmt": {"sql": sql, "args": [_to_value(a) for a in args]}}
            for sql, args in statements
        ]
        requests.append({"type": "close"})
        resp = self.client.post(self.endpoint, json={"requests": requests})
        resp.raise_for_status()
        results = resp.json()["results"]
        for r in results:
            if r["type"] == "error":
                raise RuntimeError(f"Turso: {r['error'].get('message')}")
        return [r["response"]["result"] for r in results[:-1]]

    def insert_if_new(self, lead: dict) -> bool:
        statements = [] if self._schema_ready else [(sql, []) for sql in SCHEMA]
        statements.append((INSERT_IF_NEW, _args(lead)))
        results = self._execute(statements)
        self._schema_ready = True
        return results[-1]["affected_row_count"] == 1

    def all_leads(self) -> list[dict]:
        [result] = self._execute([(SELECT_ALL, [])])
        return _rows(result)

    def recent(self, phone: str) -> dict | None:
        [result] = self._execute([(SELECT_RECENT, [phone])])
        rows = _rows(result)
        return rows[0] if rows else None

    def update(self, lead_id, fields: dict) -> None:
        self._execute([(UPDATE_LEAD, _update_args(lead_id, fields))])


def _rows(result: dict) -> list[dict]:
    names = [c["name"] for c in result["cols"]]
    return [{n: cell.get("value") for n, cell in zip(names, row)} for row in result["rows"]]


def _update_args(lead_id, fields: dict) -> list:
    return [fields["interest"], fields["items"], fields["items_total"], fields["comment"], lead_id]


def _to_value(value) -> dict:
    if value is None:
        return {"type": "null"}
    return {"type": "text", "value": str(value)}
