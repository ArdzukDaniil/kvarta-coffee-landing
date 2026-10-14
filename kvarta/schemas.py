from typing import Literal

from pydantic import BaseModel, Field, field_validator

from .phone import normalize_phone

INTERESTS = {
    "subscription": "Подписка",
    "one_time": "Разовый заказ",
    "question": "Вопрос",
}


class Attribution(BaseModel):
    """Откуда пришёл человек. Собирается на странице при первом заходе."""

    utm_source: str | None = Field(None, max_length=200)
    utm_medium: str | None = Field(None, max_length=200)
    utm_campaign: str | None = Field(None, max_length=200)
    utm_content: str | None = Field(None, max_length=200)
    utm_term: str | None = Field(None, max_length=200)
    yclid: str | None = Field(None, max_length=200)
    gclid: str | None = Field(None, max_length=200)
    fbclid: str | None = Field(None, max_length=300)
    referrer: str | None = Field(None, max_length=500)
    landing_page: str | None = Field(None, max_length=500)
    page_url: str | None = Field(None, max_length=500)


class LeadIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    phone: str
    interest: Literal["subscription", "one_time", "question"]
    comment: str = Field("", max_length=1000)
    attribution: Attribution = Attribution()
    # Ловушка для ботов: поле скрыто от людей, заполняют его только скрипты.
    website: str = ""

    @field_validator("name", "comment", mode="before")
    @classmethod
    def strip(cls, v):
        return v.strip() if isinstance(v, str) else v

    @field_validator("phone")
    @classmethod
    def belarusian_phone(cls, v: str) -> str:
        phone = normalize_phone(v)
        if phone is None:
            raise ValueError("bad_phone")
        return phone
