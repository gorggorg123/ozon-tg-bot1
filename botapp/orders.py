from __future__ import annotations

from typing import Iterable

from ozonapi.seller.common.enumerations.postings import PostingStatus
from ozonapi.seller.common.enumerations.requests import SortingDirection
from ozonapi.seller.schemas.entities.postings import PostingFilter, PostingFilterWith
from ozonapi.seller.schemas.fbo import PostingFBOListRequest

from .ozon_client import create_seller_api, msk_day_range


def _s_num(x) -> float:
    try:
        return float(str(x).replace(" ", "").replace("\u00a0", ""))
    except Exception:
        return 0.0


def _fmt_int(n: float | int) -> str:
    return f"{int(round(n)):,}".replace(",", " ")


def _rub0(n: float | int) -> str:
    return f"{_fmt_int(n)} ₽"


def _posting_total_price(posting) -> float:
    total = 0.0
    products: Iterable = posting.products or []
    for p in products:
        qty = _s_num(getattr(p, "quantity", 0))
        price = _s_num(getattr(p, "price", 0))
        total += qty * price
    return total


async def _load_today_fbo_postings():
    """
    Загружает отправления FBO за текущий день (МСК).
    """
    rng = msk_day_range()
    since = rng["from_dt"]
    to = rng["to_dt"]

    # noinspection PyArgumentList
    filter_ = PostingFilter(
        since=since,
        to_=to,
        # статус не указываем — хотим видеть и отмены тоже
        status=None,
    )

    # noinspection PyArgumentList
    with_ = PostingFilterWith(
        analytics_data=True,
        financial_data=False,
        legal_info=False,
    )

    # noinspection PyArgumentList
    request = PostingFBOListRequest(
        dir=SortingDirection.DESC,
        filter=filter_,
        limit=1000,
        with_=with_,
    )

    api = create_seller_api()
    async with api:
        response = await api.posting_fbo_list(request)

    # response.result — список PostingFBOPosting
    return rng, response.result or []


async def get_orders_today_text() -> str:
    """
    Возвращает готовый текст с FBO-сводкой за сегодня.
    """
    rng, postings = await _load_today_fbo_postings()

    total_orders = len(postings)

    cancel_statuses = {PostingStatus.CANCELLED, PostingStatus.CANCELLED_FROM_SPLIT_PENDING}
    cancelled_orders = sum(1 for p in postings if p.status in cancel_statuses)
    ok_orders = total_orders - cancelled_orders

    total_sum_all = sum(_posting_total_price(p) for p in postings)
    total_sum_ok = sum(_posting_total_price(p) for p in postings if p.status not in cancel_statuses)

    avg_check = total_sum_ok / ok_orders if ok_orders > 0 else 0.0

    text = (
        f"📦 FBO — заказы за сегодня\n"
        f"{rng['pretty']}\n\n"
        f"Сегодня:\n"
        f"• 🧾 Заказано: {_fmt_int(total_orders)} / {_rub0(total_sum_all)}\n"
        f"• ✅ Без отмен: {_fmt_int(ok_orders)} / {_rub0(total_sum_ok)}\n"
        f"• ❌ Отмен: {_fmt_int(cancelled_orders)}\n"
        f"• 🧮 Средний чек (по успешным): {_rub0(avg_check)}"
    )

    return text
