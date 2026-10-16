"""Ассортимент и цены. Источник правды для сервера: цены из браузера не принимаем.

Те же sku и цены стоят в public/index.html (data-sku, data-price) — их совпадение проверяет тест.
"""
CATALOG: dict[str, tuple[str, int]] = {
    "ethiopia": ("Эфиопия Иргачеффе", 32),
    "colombia": ("Колумбия Уила", 29),
    "brazil": ("Бразилия Серрадо", 26),
    "drip": ("Дрип-пакеты, ассорти", 18),
}
MAX_QTY = 20
FREE_DELIVERY_FROM = 50


def describe(items: dict[str, int]) -> tuple[str, int]:
    """«Эфиопия Иргачеффе × 2; Дрип-пакеты, ассорти × 1» и сумма в BYN."""
    parts, total = [], 0
    for sku, qty in items.items():
        name, price = CATALOG[sku]
        parts.append(f"{name} × {qty}")
        total += price * qty
    return "; ".join(parts), total
