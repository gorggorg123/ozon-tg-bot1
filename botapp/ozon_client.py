# botapp/ozon_client.py
import os
import json
from datetime import datetime, timedelta, timezone

import httpx

OZON_CLIENT_ID = os.getenv("OZON_CLIENT_ID")
OZON_API_KEY = os.getenv("OZON_API_KEY")

OZON_BASE_URL = "https://api-seller.ozon.ru"

if not OZON_CLIENT_ID or not OZON_API_KEY:
    print(
        "⚠️ OZON_CLIENT_ID или OZON_API_KEY не заданы. "
        "Запросы к Ozon API будут падать."
    )

HEADERS = {
    "Client-Id": OZON_CLIENT_ID or "",
    "Api-Key": OZON_API_KEY or "",
    "Content-Type": "application/json",
}

# Вся логика дат делаем в одном месте
MSK = timezone(timedelta(hours=3))


def dt_to_ozon_ts(dt: datetime) -> str:
    """
    Приводим к UTC и формату RFC3339 без микросекунд:
    2025-11-15T00:00:00Z (без двойного 'Z').
    """
    dt_utc = dt.astimezone(timezone.utc).replace(microsecond=0)
    iso = dt_utc.isoformat()  # 2025-11-14T21:00:00+00:00
    return iso.replace("+00:00", "Z")


def today_msk_range_utc() -> tuple[str, str]:
    """
    Отрезок «сегодня по МСК» [00:00; 24:00) и сразу в UTC-строки для Ozon.
    """
    now_msk = datetime.now(MSK)
    start_msk = now_msk.replace(hour=0, minute=0, second=0, microsecond=0)
    end_msk = start_msk + timedelta(days=1)
    return dt_to_ozon_ts(start_msk), dt_to_ozon_ts(end_msk)


async def ozon_call(path: str, payload: dict) -> dict:
    """
    Универсальный POST к Ozon Seller API.
    Возвращает result или полный JSON.
    При ошибке — поднимает RuntimeError с подробностями.
    """
    if not OZON_CLIENT_ID or not OZON_API_KEY:
        raise RuntimeError(
            "OZON_CLIENT_ID / OZON_API_KEY не заданы в переменных окружения."
        )

    url = OZON_BASE_URL + path
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(url, headers=HEADERS, json=payload)

    try:
        data = resp.json()
    except json.JSONDecodeError:
        raise RuntimeError(f"Ozon {path}: не JSON, статус {resp.status_code}")

    if resp.status_code != 200:
        raise RuntimeError(f"Ozon {path}: HTTP {resp.status_code}: {data}")

    # Во многих методах результат лежит в data["result"]
    return data.get("result", data)


async def get_seller_info() -> dict:
    """
    /v1/seller/info — базовая инфа по аккаунту.
    """
    return await ozon_call("/v1/seller/info", {})


async def build_seller_info_message() -> str:
    """
    Готовим текст для кнопки «🧾 Аккаунт Ozon».
    """
    try:
        info = await get_seller_info()
    except Exception as e:
        return (
            "⚠️ Не удалось получить информацию об аккаунте Ozon.\n"
            f"Ошибка: `{e!s}`"
        )

    # Аккуратно вытаскиваем поля (часть может отсутствовать)
    name = info.get("name") or "—"
    warehouse_name = info.get("warehouse_name") or "—"
    region = info.get("region") or "—"
    is_enabled = info.get("is_enabled")
    marketplace_type = info.get("marketing_seller_type") or "—"

    status_txt = "активен ✅" if is_enabled else "отключен ⛔️"

    lines: list[str] = [
        "🧾 *Аккаунт Ozon*",
        "",
        f"*Название продавца:* `{name}`",
        f"*Регион:* `{region}`",
        f"*Тип продавца:* `{marketplace_type}`",
        f"*Склад Ozon:* `{warehouse_name}`",
        f"*Статус аккаунта:* {status_txt}",
    ]

    return "\n".join(lines)
