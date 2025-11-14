import datetime as dt
import json
import os

import httpx

OZON_CLIENT_ID = os.getenv("OZON_CLIENT_ID")
OZON_API_KEY = os.getenv("OZON_API_KEY")

OZON_API_URL = "https://api-seller.ozon.ru"


def _msk_today_range() -> tuple[str, str]:
    """
    Возвращает интервал [сегодня 00:00:00, завтра 00:00:00) в МСК в ISO-формате.
    """
    now_utc = dt.datetime.utcnow()
    msk_now = now_utc + dt.timedelta(hours=3)  # UTC+3

    date_from = msk_now.replace(hour=0, minute=0, second=0, microsecond=0)
    date_to = date_from + dt.timedelta(days=1)

    iso_from = date_from.isoformat(timespec="seconds") + "Z"
    iso_to = date_to.isoformat(timespec="seconds") + "Z"
    return iso_from, iso_to


async def _ozon_call(path: str, payload: dict) -> dict:
    """
    Вспомогательная функция для вызова Ozon Seller API.
    """
    if not OZON_CLIENT_ID or not OZON_API_KEY:
        raise RuntimeError("OZON_CLIENT_ID / OZON_API_KEY не заданы в переменных окружения.")

    headers = {
        "Client-Id": OZON_CLIENT_ID,
        "Api-Key": OZON_API_KEY,
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(OZON_API_URL + path, headers=headers, json=payload)

    try:
        data = resp.json()
    except json.JSONDecodeError:
        raise RuntimeError(f"Ozon {path} -> не JSON, статус {resp.status_code}")

    if "result" not in data:
        # вернём всё, чтобы увидеть структуру и не падать по KeyError
        raise RuntimeError(f"Ozon {path} -> неожиданный ответ: {data}")

    return data["result"]


async def build_fin_today_message() -> str:
    """
    Строит текстовую сводку по финансам за сегодня (по МСК).

    Пока делаем максимально безопасно:
    - пробуем вытащить основные поля, если структура другая — показываем сырой JSON.
    """
    if not OZON_CLIENT_ID or not OZON_API_KEY:
        return (
            "⚠️ Для доступа к финансам нужно задать переменные окружения "
            "`OZON_CLIENT_ID` и `OZON_API_KEY`."
        )

    date_from, date_to = _msk_today_range()

    body = {
        # тело запроса может меняться, но базово нужен период
        "filter": {
            "date": {
                "from": date_from,
                "to": date_to,
            },
        }
    }

    try:
        result = await _ozon_call("/v3/finance/transaction/totals", body)
    except Exception as e:
        # прокидываем понятную ошибку в бот
        return f"⚠️ Не удалось получить финансы за сегодня.\nОшибка Ozon API: {e!s}"

    # Пытаемся красиво отформатировать, но если ключей нет — покажем сырой JSON.
    try:
        accruals = result.get("accruals_for_sale") or 0
        services = result.get("services") or 0
        refunds = result.get("returns") or 0
        penalties = result.get("penalties") or 0
        logistics = result.get("logistics") or 0
        compensation = result.get("compensation") or 0
        other = result.get("other") or 0
        total = result.get("total") or 0

        msg = (
            "📅 *Финансы за сегодня (МСК)*\n\n"
            f"Начислено всего: *{total:,.0f} ₽*\n"
            f"Продажи: *{accruals:,.0f} ₽*\n"
            f"Возвраты/отмены: *{refunds:,.0f} ₽*\n"
            f"Логистика: *{logistics:,.0f} ₽*\n"
            f"Услуги/реклама: *{services:,.0f} ₽*\n"
            f"Штрафы: *{penalties:,.0f} ₽*\n"
            f"Компенсации: *{compensation:,.0f} ₽*\n"
            f"Прочее: *{other:,.0f} ₽*"
        )
        return msg
    except Exception:
        # Если структура другая — просто отдаём JSON для дебага.
        pretty = json.dumps(result, ensure_ascii=False, indent=2)
        return (
            "⚠️ Не удалось разобрать ответ Ozon по структуре.\n"
            "Вот что вернул API:\n"
            f"```json\n{pretty}\n```"
        )
