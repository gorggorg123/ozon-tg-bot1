# botapp/reviews.py
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from .ozon_client import (
    OzonClient,
    msk_current_month_range,
    fmt_int,
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


async def get_reviews_month_text(client: OzonClient) -> str:
    since, to, pretty = msk_current_month_range()
    reviews = await client.get_reviews(since, to, limit=100)

    dist = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    total = 0
    sum_rating = 0

    last_items: List[str] = []

    for r in reviews:
        rating = int(r.get("rating") or r.get("grade") or 0)
        if 1 <= rating <= 5:
            dist[rating] += 1
            total += 1
            sum_rating += rating

        dt = (
            _parse_date(r.get("date"))
            or _parse_date(r.get("created_at"))
            or _parse_date(r.get("createdAt"))
        )
        dt_str = dt.strftime("%d.%m %H:%M") if dt else ""

        text = r.get("text") or r.get("comment") or ""
        text = str(text)
        if len(text) > 70:
            text = text[:67] + "…"

        offer = r.get("offer_id") or r.get("sku") or ""
        prefix = f"{rating}★ "
        meta = []
        if dt_str:
            meta.append(dt_str)
        if offer:
            meta.append(str(offer))
        meta_str = " • ".join(meta)
        last_items.append(f"• {prefix}{meta_str} — {text}".strip())

    avg = (sum_rating / total) if total else 0

    dist_line = (
        f"1★ {fmt_int(dist[1])} • "
        f"2★ {fmt_int(dist[2])} • "
        f"3★ {fmt_int(dist[3])} • "
        f"4★ {fmt_int(dist[4])} • "
        f"5★ {fmt_int(dist[5])}"
    )

    header = (
        "<b>⭐ Отзывы • текущий месяц</b>\n"
        f"{pretty}\n\n"
        f"Всего отзывов: <b>{fmt_int(total)} шт</b>\n"
        f"Средний рейтинг: <b>{avg:.2f}</b>\n"
        f"Распределение: {dist_line}\n"
    )

    if last_items:
        header += "\n<b>Последние отзывы (до 10 шт)</b>\n" + "\n".join(
            last_items[:10]
        )
    else:
        header += "\nОтзывы за период не найдены."

    return header
