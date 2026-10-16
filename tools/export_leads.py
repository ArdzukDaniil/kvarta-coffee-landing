"""Выгрузить заявки в CSV для менеджера (открывается в Excel).

    python tools/export_leads.py                 # -> leads.csv
    python tools/export_leads.py out/leads.csv

Берёт базу так же, как сайт: Turso, если заданы TURSO_DATABASE_URL и
TURSO_AUTH_TOKEN, иначе локальный data/leads.db.
"""
import csv
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import get_store  # noqa: E402
from kvarta.schemas import INTERESTS  # noqa: E402

MINSK = timezone(timedelta(hours=3))
COLUMNS = [
    ("created_at", "Когда (Минск)"), ("name", "Имя"), ("phone", "Телефон"), ("interest", "Интерес"),
    ("items", "Что заказал"), ("items_total", "Сумма по прайсу, BYN"), ("comment", "Комментарий"), ("utm_source", "Источник"), ("utm_medium", "Тип трафика"),
    ("utm_campaign", "Кампания"), ("utm_content", "Объявление"), ("utm_term", "Ключевое слово"),
    ("yclid", "yclid"), ("gclid", "gclid"), ("fbclid", "fbclid"), ("referrer", "Пришёл с"),
    ("landing_page", "Страница входа"), ("page_url", "Страница отправки"),
]
FORMULA_START = ("=", "+", "-", "@", "\t", "\r")


def to_minsk(utc_text: str) -> str:
    dt = datetime.strptime(utc_text, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    return dt.astimezone(MINSK).strftime("%d.%m.%Y %H:%M")


def safe_cell(value) -> str:
    """Защита от формул в Excel: имя и комментарий вводит посетитель,
    и «=HYPERLINK(...)» выполнилось бы у менеджера. Телефон уже нормализован (+375…), его не трогаем."""
    s = "" if value is None else str(value)
    if s.startswith(FORMULA_START) and not re.fullmatch(r"\+375\d{9}", s):
        s = "'" + s
    return s


def export(rows: list[dict], path: Path) -> None:
    # utf-8-sig и «;» — чтобы Excel с русской локалью сразу открыл кириллицу по колонкам
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow([title for _, title in COLUMNS])
        for r in rows:
            r = {**r, "created_at": to_minsk(r["created_at"]), "interest": INTERESTS.get(r["interest"], r["interest"])}
            w.writerow([safe_cell(r.get(key)) for key, _ in COLUMNS])


if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "leads.csv")
    rows = get_store().all_leads()
    export(rows, out)
    print(f"{len(rows)} заявок -> {out}")
