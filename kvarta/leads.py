"""Сохранение заявки с учётом повторов того же номера за 10 минут.

ТЗ: повтор не должен создавать вторую заявку. Но если человек за эти 10 минут
сначала задал вопрос, а потом выбрал кофе, новое не должно потеряться — тогда
мы дополняем уже существующую заявку. Повтор без новых данных (двойной клик,
повторная отправка той же формы) — обычный дубль.
"""
from typing import Literal

from .storage import LeadStore

Status = Literal["created", "updated", "duplicate"]
MERGED_FIELDS = ("interest", "items", "items_total", "comment")
COMMENT_LIMIT = 2000


def merge(old: dict, new: dict) -> dict | None:
    """Поля, которые нужно обновить в старой заявке, или None, если нового ничего нет."""
    # «Вопрос» не понижает уже оформленный заказ или подписку.
    interest = old["interest"] if new["interest"] == "question" else new["interest"]

    # Последний выбор кофе и есть актуальный; пустой выбор старый не стирает.
    if new.get("items"):
        items, items_total = new["items"], new.get("items_total")
    else:
        items, items_total = old.get("items"), old.get("items_total")

    old_comment, new_comment = old.get("comment") or "", (new.get("comment") or "").strip()
    comment = old_comment
    if new_comment and new_comment not in old_comment:
        comment = f"{old_comment}\n{new_comment}".strip()[:COMMENT_LIMIT]

    merged = {"interest": interest, "items": items, "items_total": items_total, "comment": comment}
    same = all(_norm(merged[k]) == _norm(old.get(k)) for k in MERGED_FIELDS)
    return None if same else merged


def save(store: LeadStore, record: dict) -> tuple[Status, dict | None]:
    """Сохранить заявку. Возвращает статус и итоговую заявку для уведомления менеджеру."""
    if store.insert_if_new(record):
        return "created", record
    old = store.recent(record["phone"])
    if old is None:  # окно в 10 минут успело закрыться между двумя запросами
        return "duplicate", None
    changes = merge(old, record)
    if changes is None:
        return "duplicate", None
    store.update(old["id"], changes)
    return "updated", {**record, **changes}


def _norm(value) -> str:
    return "" if value is None else str(value)
