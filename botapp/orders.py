import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

import httpx

logger = logging.getLogger(__name__)

MSK_SHIFT_HOURS = 3
ONE_DAY = timedelta(days=1)


def _to_ozon_iso(dt: datetime) -> str:
    """Формат в стиле 2025-11-15T00:00:00Z без миллисекунд."""
    return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _today_range_msk() -> Dict[str, Any]:
    """
    Диапазон "сегодня" в МСК:
    00:00–23:59 (по МСК) → переводим в UTC и в ISO для Ozon.
    """
    now_utc = datetime.now(timezone.utc)

    # Текущее "МСК-время"
    now_msk = now_utc + timedelta(hours=MSK_SHIFT_HOURS)

    # Полночь МСК
    start_msk = datetime(
        year=now_msk.year,
        month=now_msk.month,
        day=now_msk.day,
        tzinfo=timezone.utc,
    ) - timedelta(hours=MSK_SHIFT_HOURS)

    end_msk = start_msk + ONE_DAY - timedelta(seconds=1)

    pretty_date = (start_msk + timedelta(hours=MSK_SHIFT_HOURS)).strftime(
        "%d.%m.%Y"
    )

    return {
        "from_utc": start_msk,
        "to_utc": end_msk,
        "since": _to_ozon_iso(start_msk),
        "to": _to_ozon_iso(end_msk),
        "pretty": f"{pretty_date} 00:00 — {pretty_date} 23:59 (МСК)",
    }


def _format_rub(value: float) -> str:
    return f"{round(value):,} ₽".replace(",", " ")


def _posting_total_price(posting: Dict[str, Any]) -> float:
    """
    Считаем сумму заказа.
    Сначала пробуем analytics_data.total_price, иначе суммируем по товарам.
    """
    analytics = posting.get("analytics_data") or posting.get("analyticsData") or {}
    price = analytics.get("total_price") or analytics.get("price")
    if price is not None:
        try:
            return float(price)
        except (TypeError, ValueError):
            pass

    total = 0.0
    products = posting.get("products") or []
    for item in products:
        try:
            qty = float(
                item.get("quantity")
                or item.get("offer_quantity")
                or item.get("items_count")
                or 0
            )
            unit = float(
                item.get("price")
                or item.get("client_price")
                or item.get("original_price")
                or 0
            )
            total += qty * unit
        except (TypeError, ValueError):
            continue
    return total


def _is_cancelled(posting: Dict[str, Any]) -> bool:
    status = str(posting.get("status") or "").lower()
    return "cancel" in status


async def _fetch_fbo_postings(since: str, to: str) -> List[Dict[str, Any]]:
    """
    Делает запрос к /v2/posting/fbo/list и приводит ответ к списку постингов.
    Всю магию с result / result.postings нормализуем здесь.
    """
    client_id = os.getenv("OZON_CLIENT_ID", "")
    api_key = os.getenv("OZON_API_KEY", "")

    if not client_id or not api_key:
        raise RuntimeError("OZON_CLIENT_ID / OZON_API_KEY are not set")

    headers = {
        "Client-Id": client_id,
        "Api-Key": api_key,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    body = {
        "dir": "DESC",
        "filter": {
            "since": since,
            "to": to,
        },
        "limit": 1000,
        "offset": 0,
        "with": {
            "products": True,
            "financial_data": False,
            "analytics_data": True,
        },
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            "https://api-seller.ozon.ru/v2/posting/fbo/list",
            json=body,
            headers=headers,
        )
        resp.raise_for_status()
        data = resp.json()

    # Нормализация разных вариантов ответа
    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        res = data.get("result")
        if isinstance(res, list):
            return res
        if isinstance(res, dict):
            posts = res.get("postings") or res.get("items")
            if isinstance(posts, list):
                return posts

    logger.warning("Неизвестный формат ответа /v2/posting/fbo/list: %r", data)
    return []


async def get_orders_today_text() -> str:
    """
    Формирует текст «Заказы за сегодня» для Telegram.
    """
    rng = _today_range_msk()
    postings = await _fetch_fbo_postings(rng["since"], rng["to"])

    # Убираем дубли по номеру постинга
    seen = set()
    unique_postings: List[Dict[str, Any]] = []
    for p in postings:
        num = str(p.get("posting_number") or p.get("postingNumber") or "")
        if num and num not in seen:
            seen.add(num)
            unique_postings.append(p)

    total_orders = len(unique_postings)
    ok_postings = [p for p in unique_postings if not _is_cancelled(p)]
    cancelled = total_orders - len(ok_postings)

    sum_all = sum(_posting_total_price(p) for p in unique_postings)
    sum_ok = sum(_posting_total_price(p) for p in ok_postings)
    avg_check = sum_ok / len(ok_postings) if ok_postings else 0.0

    text = (
        "📦 <b>Заказы за сегодня</b>\n"
        f"{rng['pretty']}\n\n"
        f"🧾 Заказано: {total_orders} / {_format_rub(sum_all)}\n"
        f"✅ Без отмен: {len(ok_postings)} / {_format_rub(sum_ok)}\n"
        f"❌ Отмен: {cancelled}\n"
        f"🧮 Ср. чек: {_format_rub(avg_check)}"
    )

    return text
