from __future__ import annotations

from typing import Dict, Any

from .ozon_client import ozon_raw_post, msk_day_range


def _s_num(x: Any) -> float:
    try:
        return float(str(x).replace(" ", "").replace("\u00a0", ""))
    except Exception:
        return 0.0


def _fmt_int(n: float | int) -> str:
    return f"{int(round(n)):,}".replace(",", " ")


def _rub0(n: float | int) -> str:
    return f"{_fmt_int(n)} ₽"


def _sales_from_totals(t: Dict[str, Any]) -> float:
    return _s_num(t.get("accruals_for_sale")) - _s_num(t.get("refunds_and_cancellations"))


def _build_expenses(t: Dict[str, Any]) -> float:
    sc = _s_num(t.get("sale_commission"))
    pad = _s_num(t.get("processing_and_delivery"))
    rfc = _s_num(t.get("refunds_and_cancellations"))
    sa = _s_num(t.get("services_amount"))
    oa = _s_num(t.get("others_amount"))

    commission = abs(sc)
    delivery = abs(pad)
    returns = -rfc if rfc < 0 else 0
    other = abs(sa) + abs(oa)
    return commission + delivery + returns + other


def _accrued_from_totals(t: Dict[str, Any]) -> float:
    return (
        _s_num(t.get("accruals_for_sale"))
        + _s_num(t.get("sale_commission"))
        + _s_num(t.get("processing_and_delivery"))
        + _s_num(t.get("refunds_and_cancellations"))
        + _s_num(t.get("services_amount"))
        + _s_num(t.get("others_amount"))
        + _s_num(t.get("compensation_amount"))
    )


async def get_finance_today_text() -> str:
    """
    Возвращает готовый текст для Telegram по финансам за текущий день (МСК).
    """
    rng = msk_day_range()

    payload = {
        "date": {
            "from": rng["since"],
            "to": rng["to"],
        },
        "transaction_type": "all",
    }

    data = await ozon_raw_post("/v3/finance/transaction/totals", payload)
    totals = data.get("result") or {}

    accrued = _accrued_from_totals(totals)
    sales = _sales_from_totals(totals)
    expenses = _build_expenses(totals)
    profit = accrued - expenses

    text = (
        f"🏦 Финансы за сегодня\n"
        f"{rng['pretty']}\n\n"
        f"Начислено: {_rub0(accrued)}\n"
        f"Продажи:  {_rub0(sales)}\n"
        f"Расходы:  {_rub0(expenses)}\n"
        f"Прибыль (грубо, до себестоимости): {_rub0(profit)}"
    )

    return text
