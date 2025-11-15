# botapp/orders.py

from __future__ import annotations

import datetime as dt
import os
from typing import Any, List

import httpx

MSK_TZ = dt.timezone(dt.timedelta(hours=3))
OZON_BASE_URL = "https://api-seller.ozon.ru"

OZON_CLIENT_ID = os.getenv("OZON_CLIENT_ID")
OZON_API_KEY = os.getenv("OZON_API_KEY")


def _to_ozon_ts(d: dt.datetime) -> str:
    """Переводим дату в формат RFC3339 Z (UTC), как любит Ozon."""
    return (
        d.astimezone(dt.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


async def _fetch_fbo_postings_today() -> List[dict]:
    """
    Возвращает список заказов FBO за текущие сутки по МСК.
    Делает прямой POST /v2/posting/fbo/list.
    """

    if not OZON_CLIENT_ID or not OZON_API_KEY:
        raise RuntimeError("Не заданы OZON_CLIENT_ID / OZON_API_KEY")

    now_msk = dt.datetime.now(tz=MSK_TZ)
    start = now_msk.replace(hour=0, minute=0, second=0, microsecond=0)
    end = now_msk.replace(hour=23, minute=59, second=59, microsecond=0)

    payload = {
        "dir": "asc",
        "filter": {
            "since": _to_ozon_ts(start),
            "to": _to_ozon_ts(end),
        },
        "limit": 1000,
        "offset": 0,
        "with": {
            "analytics_data": False,
            "financial_data": False,
        },
    }

    headers = {
        "Client-Id": OZON_CLIENT_ID,
        "Api-Key": OZON_API_KEY,
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{OZON_BASE_URL}/v2/posting/fbo/list",
            json=payload,
            headers=headers,
        )
        resp.raise_for_status()
        data: Any = resp.json()

    # Защита от разных форматов ответа
    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        # классический ответ Ozon: {"result": [ ... ]}
        if isinstance(data.get("result"), list):
            return data["result"]
        # на всякий случай
        if isinstance(data.get("postings"), list):
            return data["postings"]

    # pydantic-модель из библиотеки Ульянова (на будущее)
    if hasattr(data, "result") and isinstance(data.result, list):
        return data.result
    if hasattr(data, "postings") and isinstance(data.postings, list):
        return data.postings

    return []


async def get_orders_today_text() -> str:
    """
    Формирует текст для раздела «Заказы за сегодня».
    """

    try:
        postings = await _fetch_fbo_postings_today()
    except Exception as e:
        return (
            "⚠️ Не удалось получить заказы за сегодня.\n"
            f"Ошибка: {e}"
        )

    if not postings:
        return "📦 За сегодня заказов нет."

    total = len(postings)
    delivered = sum(1 for p in postings if p.get("status") == "delivered")
    cancelled = sum(1 for p in postings if p.get("status") == "cancelled")
    in_work = total - delivered - cancelled

    lines = [
        "📦 *Заказы за сегодня*",
        "",
        f"Всего заказов: *{total}*",
        f"✅ Доставлено: *{delivered}*",
        f"🚚 В обработке: *{in_work}*",
        f"❌ Отменено: *{cancelled}*",
    ]

    return "\n".join(lines)
