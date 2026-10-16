"""Дубль заявки в Telegram-чат менеджера.

Включается переменными TELEGRAM_BOT_TOKEN и TELEGRAM_CHAT_ID. Telegram — только
уведомление: заявка к этому моменту уже сохранена в базе, поэтому сбой
Telegram не ломает отправку формы, а лишь пишется в лог.
"""
import html
import logging
from datetime import datetime, timedelta, timezone

import httpx

from .schemas import INTERESTS

log = logging.getLogger("kvarta")
MINSK = timezone(timedelta(hours=3))


def format_lead(lead: dict, now: datetime | None = None) -> str:
    """Текст сообщения в HTML-разметке Telegram. Всё, что ввёл человек, экранируется."""
    e = lambda v: html.escape(str(v)) if v else ""  # noqa: E731
    now = (now or datetime.now(timezone.utc)).astimezone(MINSK)

    lines = [
        f"<b>Новая заявка: {e(INTERESTS.get(lead['interest'], lead['interest']))}</b>",
        f"{e(lead['name'])}, {e(lead['phone'])}",
    ]
    if lead.get("items"):
        lines.append("")
        lines.extend(f"☕ {e(item)}" for item in lead["items"].split("; "))
        if lead["interest"] != "subscription":
            lines.append(f"≈ {e(lead.get('items_total'))} BYN по прайсу")
    if lead.get("comment"):
        lines.append(f"💬 {e(lead['comment'])}")

    source = [lead.get(k) for k in ("utm_source", "utm_medium", "utm_campaign")]
    if any(source):
        lines.append("")
        lines.append("Источник: " + " / ".join(e(s) for s in source if s))
        if lead.get("utm_content"):
            lines.append(f"Объявление: {e(lead['utm_content'])}")
        if lead.get("utm_term"):
            lines.append(f"Ключевое слово: {e(lead['utm_term'])}")
    else:
        click = "Яндекс (yclid)" if lead.get("yclid") else "Google (gclid)" if lead.get("gclid") else \
            "Facebook/Instagram (fbclid)" if lead.get("fbclid") else None
        lines.append("")
        lines.append(f"Источник: {click or 'без UTM-меток'}")
    if lead.get("referrer"):
        lines.append(f"Пришёл с: {e(lead['referrer'])}")
    if lead.get("landing_page"):
        lines.append(f"Страница входа: {e(lead['landing_page'])}")

    lines.append("")
    lines.append(f"🕓 {now:%d.%m.%Y %H:%M} (Минск)")
    return "\n".join(lines)


class TelegramNotifier:
    def __init__(self, token: str, chat_id: str, client: httpx.Client | None = None):
        self.url = f"https://api.telegram.org/bot{token}/sendMessage"
        self.chat_id = chat_id
        self.client = client or httpx.Client(timeout=4)

    def send(self, lead: dict) -> bool:
        try:
            resp = self.client.post(self.url, json={
                "chat_id": self.chat_id,
                "text": format_lead(lead),
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            })
            resp.raise_for_status()
            return True
        except Exception as exc:  # уведомление вторично, заявка уже сохранена
            # str(exc) у httpx может содержать URL с токеном — его в лог не пишем.
            log.warning("Telegram: не удалось отправить уведомление (%s)", type(exc).__name__)
            return False
