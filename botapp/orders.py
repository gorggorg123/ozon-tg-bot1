# botapp/orders.py
from collections import Counter

from .ozon_client import ozon_call, today_msk_range_utc


def _summarize_postings(postings: list[dict]) -> tuple[int, Counter]:
    total = len(postings)
    by_status: Counter = Counter()
    for p in postings:
        status = p.get("status", "unknown")
        by_status[status] += 1
    return total, by_status


async def build_orders_today_message() -> str:
    """
    Статистика заказов за сегодня по FBO + FBS.
    """
    date_from, date_to = today_msk_range_utc()

    # FBO
    payload_fbo = {
        "dir": "asc",
        "filter": {
            "since": date_from,
            "to": date_to,
            "status": "",  # все статусы
        },
        "limit": 1000,
        "offset": 0,
        "with": {
            "analytics_data": False,
            "financial_data": False,
        },
    }

    # FBS
    payload_fbs = {
        "dir": "asc",
        "filter": {
            "since": date_from,
            "to": date_to,
            "status": "",  # все статусы
        },
        "limit": 1000,
        "offset": 0,
        "with": {
            "analytics_data": False,
            "financial_data": False,
        },
    }

    fbo = await ozon_call("/v2/posting/fbo/list", payload_fbo)
    fbs = await ozon_call("/v3/posting/fbs/list", payload_fbs)

    fbo_postings = fbo.get("postings", []) or []
    fbs_postings = fbs.get("postings", []) or []

    total_fbo, statuses_fbo = _summarize_postings(fbo_postings)
    total_fbs, statuses_fbs = _summarize_postings(fbs_postings)
    total_all = total_fbo + total_fbs

    lines: list[str] = [
        "*📦 Заказы за сегодня*",
        "",
        "Период (МСК):",
        f"`{date_from}` — `{date_to}`",
        "",
        f"Всего заказов: *{total_all}*",
        "",
        f"*FBO*: {total_fbo} шт.",
    ]

    if statuses_fbo:
        lines.append("Статусы FBO:")
        for status, cnt in sorted(statuses_fbo.items()):
            # статус в `...`, чтобы не ломать Markdown из-за `_`
            lines.append(f"- `{status}`: {cnt}")
    else:
        lines.append("Статусы FBO: нет заказов")

    lines.append("")
    lines.append(f"*FBS*: {total_fbs} шт.")

    if statuses_fbs:
        lines.append("Статусы FBS:")
        for status, cnt in sorted(statuses_fbs.items()):
            lines.append(f"- `{status}`: {cnt}")
    else:
        lines.append("Статусы FBS: нет заказов")

    return "\n".join(lines)
