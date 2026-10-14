"""Белорусские номера: нормализация к виду +375XXXXXXXXX и проверка кода.

Принимаем любой привычный ввод: +375 29 123-45-67, 375291234567,
8 029 123 45 67, 80291234567, 029 1234567, 291234567.
"""
import re

# Мобильные операторы: A1 (29, 44), МТС (29, 33), life:) (25).
MOBILE_CODES = {"25", "29", "33", "44"}
# Городские: 17 — Минск, 15х/16х/21х/22х/23х — области.
LANDLINE_PREFIXES = {"15", "16", "17", "21", "22", "23"}


def normalize_phone(raw: str) -> str | None:
    """Вернуть номер в формате +375XXXXXXXXX или None, если номер не белорусский."""
    digits = re.sub(r"\D", "", raw or "")

    if digits.startswith("375"):
        national = digits[3:]
    elif digits.startswith("80"):
        national = digits[2:]
    elif digits.startswith("0"):
        national = digits[1:]
    else:
        national = digits

    if len(national) != 9:
        return None

    prefix = national[:2]
    if prefix not in MOBILE_CODES and prefix not in LANDLINE_PREFIXES:
        return None
    # У мобильных номер абонента не начинается с нуля.
    if prefix in MOBILE_CODES and national[2] == "0":
        return None

    return "+375" + national
