# botapp/orders.py
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Tuple

from .ozon_client import (
    OzonClient,
    msk_today_range,
    msk_current_month_range,
    fmt_int,
    fmt_rub0,
    s_num,
)


def _parse_date(v: Any) -> datetime | None:
    if not v:
        return None
    if isinstance(v, datetime):
        return v
    s = str(v).replace(" ", "T")
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


def _get_acceptance_dt(p: Dict[str, Any]) -> datetime | None:
    for key in (
        "in_process_at",
        "in_process_date",
        "acceptance_dt",
        "processed_at",
        "processing_dt",
        "approved_at",
    ):
        d = _parse_date(p.get(key))
        if d:
            return d
    return None


def _is_cancelled(p: Dict[str, Any]) -> bool:
    st = str(p.get("status", "")).lower()
    return "cancel" in st or "canceled" in st or "cancellation" in st


def _posting_total_price(p: Dict[str, Any]) -> float:
    ad = p.get("analytics_data") or p.get("analyticsData") or {}
    ad_price = s_num(ad.get("total_price") or ad.get("price"))
    if ad_price > 0:
        return ad_price

    products = p.get("products") or []
    if not isinstance(products, list):
        return 0.0

    total = 0.0
    for t in products:
        q = s_num(
            t.get("quantity")
            or t.get("offer_quantity")
            or t.get("items_count")
        )
        u = s_num(
            t.get("price")
            or t.get("client_price")
            or t.get("original_price")
        )
        total += q * u
    return total


def _summarize_orders(postings: List[Dict[str, Any]]) -> Tuple[int, int, float, float]:
    """
    Вернёт: (all_orders, ok_orders, sum_all, sum_ok)
    """
    all_orders = 0
    ok_orders = 0
    sum_all = 0.0
    sum_ok = 0.0

    for p in postings:
        total = _posting_total_price(p)
        all_orders += 1
        sum_all += total
        if not _is_cancelled(p):
            ok_orders += 1
            sum_ok += total

    return all_orders, ok_orders, sum_all, sum_ok


async def get_orders_today_text(client: OzonClient) -> str:
    since, to, pretty = msk_today_range()
    postings = await client.get_fbo_postings(since, to)

    all_orders, ok_orders, sum_all, sum_ok = _summarize_orders(postings)
    cancelled = all_orders - ok_orders
    avg = sum_ok / ok_orders if ok_orders else 0.0

    return (
        "<b>📦 Заказы за сегодня (FBO)</b>\n"
        f"{pretty}\n\n"
        f"🧾 Заказано: {fmt_int(all_orders)} / {fmt_rub0(sum_all)}\n"
        f"✅ Без отмен: {fmt_int(ok_orders)} / {fmt_rub0(sum_ok)}\n"
        f"❌ Отмен:     {fmt_int(cancelled)}\n"
        f"🧮 Средний чек: {fmt_rub0(avg)}"
    )


async def get_orders_month_summary_text(client: OzonClient) -> str:
    since, to, pretty = msk_current_month_range()
    postings = await client.get_fbo_postings(since, to)

    all_orders, ok_orders, sum_all, sum_ok = _summarize_orders(postings)
    cancelled = all_orders - ok_orders
    avg = sum_ok / ok_orders if ok_orders else 0.0

    return (
        "<b>📦 FBO • текущий месяц</b>\n"
        f"{pretty}\n\n"
        f"🧾 Заказано: {fmt_int(all_orders)} / {fmt_rub0(sum_all)}\n"
        f"✅ Без отмен: {fmt_int(ok_orders)} / {fmt_rub0(sum_ok)}\n"
        f"❌ Отмен:     {fmt_int(cancelled)}\n"
        f"🧮 Средний чек: {fmt_rub0(avg)}"
    )
