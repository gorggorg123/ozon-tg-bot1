# botapp/finance.py
import json

from .ozon_client import ozon_call, today_msk_range_utc


async def get_today_finance_totals() -> dict:
    """
    /v3/finance/transaction/totals
    Требует либо posting_number, либо диапазон date.
    Мы передаём date (сегодня по МСК).
    """
    date_from, date_to = today_msk_range_utc()

    payload = {
        "filter": {
            "transaction_type": "all",  # безопасно: все операции
            "posting_number": [],
            "date": {
                "from": date_from,
                "to": date_to,
            },
        }
    }

    return await ozon_call("/v3/finance/transaction/totals", payload)


async def build_fin_today_message() -> str:
    """
    Строим сообщение для кнопки «📊 Финансы сегодня».
    Пока показываем сырые данные totals в виде JSON, но аккуратно,
    чтобы не ломать Markdown.
    """
    date_from, date_to = today_msk_range_utc()

    totals = await get_today_finance_totals()

    snippet = json.dumps(totals, ensure_ascii=False, indent=2)
    # Ограничим размер, чтобы влезло в Telegram
    if len(snippet) > 3500:
        snippet = snippet[:3500] + "\n..."

    msg = (
        "*📊 Финансы за сегодня*\n\n"
        "Период (МСК):\n"
        f"`{date_from}` — `{date_to}`\n\n"
        "Сводка Ozon (transaction/totals):\n"
        "```json\n"
        f"{snippet}\n"
        "```"
    )

    return msg
