"""Бэкенд лендинга «Кварта»: один эндпоинт POST /api/lead.

На Vercel этот файл становится serverless-функцией, а папку public/ раздаёт CDN.
Локально: uvicorn app:app --reload — тогда статику раздаёт сам FastAPI.
"""
import json
import logging
import os
from functools import lru_cache
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from kvarta.schemas import LeadIn
from kvarta.storage import LeadStore, SqliteStore, TursoStore

log = logging.getLogger("kvarta")
logging.basicConfig(level=logging.INFO)

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

FIELD_ERRORS = {
    "name": "Напишите, как к вам обращаться.",
    "phone": "Нужен белорусский номер: +375 и 9 цифр, например +375 29 123-45-67.",
    "interest": "Выберите, что вас интересует.",
    "comment": "Комментарий получился слишком длинным — сократите до 1000 знаков.",
}
SAVE_FAILED = (
    "Не получилось отправить заявку — это проблема на нашей стороне. "
    "Попробуйте ещё раз через минуту или позвоните нам."
)


@lru_cache
def get_store() -> LeadStore:
    url, token = os.getenv("TURSO_DATABASE_URL"), os.getenv("TURSO_AUTH_TOKEN")
    if url and token:
        return TursoStore(url, token)
    if os.getenv("VERCEL"):
        # На Vercel файловая система временная: без Turso заявки бы терялись.
        raise RuntimeError("TURSO_DATABASE_URL / TURSO_AUTH_TOKEN не заданы")
    Path("data").mkdir(exist_ok=True)
    return SqliteStore("data/leads.db")


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    errors = {}
    for err in exc.errors():
        loc = [p for p in err["loc"] if p != "body"]
        field = str(loc[0]) if loc else "form"
        errors.setdefault(field, FIELD_ERRORS.get(field, "Проверьте это поле."))
    return JSONResponse(
        status_code=422,
        content={"status": "invalid", "message": "Проверьте поля формы.", "errors": errors},
    )


@app.post("/api/lead")
def create_lead(lead: LeadIn, request: Request, store: LeadStore = Depends(get_store)):
    if lead.website:
        log.info("honeypot: заявка от бота отброшена")
        return JSONResponse(status_code=201, content={"status": "created"})

    record = {
        "name": lead.name,
        "phone": lead.phone,
        "interest": lead.interest,
        "comment": lead.comment,
        **lead.attribution.model_dump(),
        "user_agent": (request.headers.get("user-agent") or "")[:300],
    }
    try:
        created = store.insert_if_new(record)
    except Exception:
        # Заявку не теряем совсем: она остаётся в логах Vercel.
        log.exception("не удалось сохранить заявку: %s", json.dumps(record, ensure_ascii=False))
        return JSONResponse(status_code=503, content={"status": "error", "message": SAVE_FAILED})

    if not created:
        return JSONResponse(
            status_code=200,
            content={
                "status": "duplicate",
                "message": "Мы уже получили заявку с этим номером — менеджер скоро перезвонит.",
            },
        )
    log.info("новая заявка: %s, %s", lead.interest, lead.attribution.utm_source or "без utm")
    return JSONResponse(status_code=201, content={"status": "created"})


@app.exception_handler(RuntimeError)
async def config_error(request: Request, exc: RuntimeError):
    log.error("ошибка конфигурации: %s", exc)
    return JSONResponse(status_code=503, content={"status": "error", "message": SAVE_FAILED})


if not os.getenv("VERCEL"):
    app.mount("/", StaticFiles(directory="public", html=True), name="static")
