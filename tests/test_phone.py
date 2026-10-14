import pytest

from kvarta.phone import normalize_phone


@pytest.mark.parametrize(
    "raw",
    [
        "+375 29 123-45-67",
        "+375 (29) 123-45-67",
        "375291234567",
        "8 029 123 45 67",
        "80291234567",
        "029 1234567",
        "291234567",
    ],
)
def test_same_mobile_number_in_any_format(raw):
    assert normalize_phone(raw) == "+375291234567"


@pytest.mark.parametrize("code", ["25", "29", "33", "44"])
def test_all_mobile_operators(code):
    assert normalize_phone(f"+375{code}7654321") == f"+375{code}7654321"


@pytest.mark.parametrize("raw", ["+375 17 222-33-44", "8 017 2223344", "+375 162 12-34-56"])
def test_landline_numbers(raw):
    assert normalize_phone(raw) is not None


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "abc",
        "+7 912 345-67-89",  # российский
        "+375 29 123-45-6",  # не хватает цифры
        "+375 29 123-45-678",  # лишняя цифра
        "+375 99 123-45-67",  # нет такого кода
        "+375 29 012-34-56",  # мобильный абонент с нуля
        "+48 512 345 678",  # польский
    ],
)
def test_rejects_non_belarusian_and_malformed(raw):
    assert normalize_phone(raw) is None
