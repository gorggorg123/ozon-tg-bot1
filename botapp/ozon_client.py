import os
import datetime as dt
from typing import Dict, Any

import httpx
from ozonapi import SellerAPI

OZON_API_URL = "https://api-seller.ozon.ru"

MSK_SHIFT_HOURS = 3
ONE_DAY = dt.timedelta(days=1)


# ============ ENV / креды ============

def get_ozon_credentials() -> tuple[str, str]:
    client_id = os.getenv("OZON_CLIENT_ID")
    api_key = os.getenv("OZON_API_KEY")

    if not client_id or not api_key:
        raise RuntimeError("Не заданы переменные окружения OZON_CLIENT_ID / OZON_API_KEY")

    return client_id.strip(), api_key.strip()


def build_ozon_headers() -> Dict[str, str]:
    client_id, api_key = get_ozon_credentials()
    return {
        "Client-Id": client_id,
        "Api-Key": api_key,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


# ============ Вспомогательные даты (день по МСК) ============

def _to_iso_no_ms(d: dt.datetime) -> str:
    d = d.astimezone(dt.timezone.utc)
    return d.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def msk_day_range(date_utc: dt.datetime | None = None) -> dict:
    """
    Возвращает диапазон текущего дня по МСК,
    но в формате UTC (как в твоём JS-боте).
    """
    if date_utc is None:
        date_utc = dt.datetime.now(dt.timezone.utc)

    # Полночь по UTC текущего дня
    midnight_utc = dt.datetime(
        year=date_utc.year,
        month=date_utc.month,
        day=date_utc.day,
        tzinfo=dt.timezone.utc,
    )

    # Сдвигаем на -3 часа, чтобы получить 00:00 МСК
    start_utc = midnight_utc - dt.timedelta(hours=MSK_SHIFT_HOURS)
    end_utc = start_utc + ONE_DAY - dt.timedelta(microseconds=1)

    # Красивый текст "дд.мм.гггг 00:00 — 23:59 (МСК)"
    msk_start = start_utc + dt.timedelta(hours=MSK_SHIFT_HOURS)
    dd = f"{msk_start.day:02d}.{msk_start.month:02d}.{msk_start.year}"
    pretty = f"{dd} 00:00 — {dd} 23:59 (МСК)"

    return {
        "since": _to_iso_no_ms(start_utc),
        "to": _to_iso_no_ms(end_utc),
        "from_dt": start_utc,
        "to_dt": end_utc,
        "pretty": pretty,
    }


# ============ Сырой HTTP к Ozon ============

async def ozon_raw_post(path: str, payload: Dict[str, Any], timeout: float = 15.0) -> Dict[str, Any]:
    """
    Универсальный POST на https://api-seller.ozon.ru
    Используем для методов, которых нет в ozonapi-async
    (например, /v3/finance/transaction/totals).
    """
    url = OZON_API_URL + path
    headers = build_ozon_headers()

    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(url, json=payload, headers=headers)

    try:
        data = resp.json()
    except ValueError:
        data = {"raw": resp.text}

    if resp.status_code >= 400:
        raise RuntimeError(f"Ozon {path}: HTTP {resp.status_code}: {data}")

    if isinstance(data, dict):
        return data
    # На всякий случай
    return {"result": data}


# ============ Класс SellerAPI ============

def create_seller_api() -> SellerAPI:
    """
    Создаёт экземпляр SellerAPI из ozonapi-async.
    Используем для FBO-методов и прочих, которые уже реализованы в библиотеке.
    """
    client_id, api_key = get_ozon_credentials()
    # noinspection PyArgumentList
    return SellerAPI(client_id=client_id, api_key=api_key)
