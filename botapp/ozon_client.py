import json
import os
from datetime import datetime, timedelta, timezone
from functools import lru_cache

import httpx
from dotenv import load_dotenv

# Пытаемся подключить библиотеку Ульянова
try:
    from ozonapi import SellerAPI  # type: ignore
except ImportError:  # ozonapi-async не установлен
    SellerAPI = None  # type: ignore[assignment]

# Локальная разработка: подхватить .env
load_dotenv()

OZON_API_URL = os.getenv("OZON_API_URL", "https://api-seller.ozon.ru")

MSK_TZ = timezone(timedelta(hours=3))


@lru_cache()
def get_credentials() -> tuple[str, str]:
    """
    Берём Client-Id и Api-Key из переменных окружения.
    Используются и для прямых запросов, и для SellerAPI.
    """
    client_id = os.getenv("OZON_CLIENT_ID")
    api_key = os.getenv("OZON_API_KEY")

    if not client_id or not api_key:
        raise RuntimeError(
            "Не заданы переменные окружения OZON_CLIENT_ID и OZON_API_KEY."
        )

    return client_id, api_key


def _auth_headers() -> dict:
    client_id, api_key = get_credentials()
    return {
        "Client-Id": client_id,
        "Api-Key": api_key,
        "Content-Type": "application/json",
    }


async def ozon_post(path: str, payload: dict) -> dict:
    """
    Универсальный POST к Seller API.
    """
    url = OZON_API_URL.rstrip("/") + path

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(url, json=payload, headers=_auth_headers())

    resp.raise_for_status()
    return resp.json()


def today_msk_range_utc() -> tuple[str, str]:
    """
    Границы текущего дня по МСК, переведённые в UTC и отформатированные
    как 2025-11-13T00:00:00Z (без миллисекунд).
    """
    now_msk = datetime.now(MSK_TZ)
    start_msk = now_msk.replace(hour=0, minute=0, second=0, microsecond=0)
    end_msk = start_msk + timedelta(days=1)

    start_utc = start_msk.astimezone(timezone.utc)
    end_utc = end_msk.astimezone(timezone.utc)

    fmt = "%Y-%m-%dT%H:%M:%SZ"
    return start_utc.strftime(fmt), end_utc.strftime(fmt)


# --- Пример: прямой вызов /v3/finance/transaction/totals через HTTP ---

async def api_finance_totals_today() -> dict:
    """
    Прямой запрос к /v3/finance/transaction/totals на сегодня (по МСК).
    Сейчас не используется в боте, но может пригодиться дальше.
    """
    date_from, date_to = today_msk_range_utc()

    payload = {
        "date_time_from": date_from,
        "date_time_to": date_to,
        "transaction_type": "all",
    }

    return await ozon_post("/v3/finance/transaction/totals", payload)


# --- SellerAPI Ульянова: информация о продавце ---


@lru_cache()
def _seller_api_kwargs() -> dict:
    """
    Параметры для инициализации SellerAPI.
    Если потом перейдём на конфиг-класс — поменяется только здесь.
    """
    client_id, api_key = get_credentials()
    return {
        "client_id": client_id,
        "api_key": api_key,
    }


async def api_seller_info() -> object:
    """
    Получить seller_info через ozonapi-async.
    """
    if SellerAPI is None:
        raise RuntimeError(
            "Библиотека ozonapi-async не установлена. "
            "Добавь её в requirements.txt и сделай redeploy."
        )

    kwargs = _seller_api_kwargs()
    async with SellerAPI(**kwargs) as api:  # type: ignore[call-arg]
        return await api.seller_info()


async def build_seller_info_message() -> str:
    """
    Собираем красивое текстовое сообщение для Телеграма
    по результату seller_info().
    """
    try:
        info = await api_seller_info()
    except Exception as e:
        return f"⚠️ Не удалось получить информацию о продавце.\nОшибка: {e!s}"

    # Пытаемся аккуратно вытащить основные поля.
    try:
        lines: list[str] = ["🧾 Аккаунт Ozon", ""]

        company = getattr(info, "company", None)

        if company is not None:
            name = getattr(company, "name", None)
            inn = getattr(company, "inn", None)
            ogrn = getattr(company, "ogrn", None)
            address = getattr(company, "address", None)

            if name:
                lines.append(f"🏢 Компания: {name}")
            if inn:
                lines.append(f"ИНН: {inn}")
            if ogrn:
                lines.append(f"ОГРН: {ogrn}")
            if address:
                lines.append(f"📍 Юр. адрес: {address}")
        else:
            # Если структура вдруг другая — просто выводим JSON
            data = info
            if hasattr(info, "model_dump"):
                data = info.model_dump()  # type: ignore[attr-defined]
            elif hasattr(info, "dict"):
                data = info.dict()  # type: ignore[call-arg]

            lines.append("```json")
            lines.append(json.dumps(data, ensure_ascii=False, indent=2))
            lines.append("```")

        return "\n".join(lines)

    except Exception:
        # На всякий случай совсем универсальный fallback
        return f"🧾 Аккаунт Ozon:\n{info!r}"
