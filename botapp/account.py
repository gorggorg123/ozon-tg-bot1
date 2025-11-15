# botapp/account.py
from __future__ import annotations

from typing import Dict, Any

from .ozon_client import OzonClient, fmt_int


async def get_account_info_text(client: OzonClient) -> str:
    info: Dict[str, Any] = await client.get_company_info()

    name = info.get("name") or info.get("legal_name") or "Без названия"
    region = info.get("region") or info.get("region_name") or ""
    city = info.get("city") or ""
    warehouses = info.get("warehouses") or info.get("warehouse_list") or []

    wh_lines = []
    if isinstance(warehouses, list) and warehouses:
        for w in warehouses[:5]:
            w_name = w.get("name") or w.get("warehouse_name") or "Склад"
            w_city = w.get("city") or w.get("address", {}).get("city") or ""
            wh_lines.append(f"• {w_name}" + (f" ({w_city})" if w_city else ""))
    else:
        wh_lines.append("• нет данных по складам в API-ответе")

    balance = info.get("balance") or info.get("current_balance")

    text = (
        "<b>📄 Аккаунт Ozon</b>\n\n"
        f"Название: <b>{name}</b>\n"
    )
    if city or region:
        text += f"Регион: {city or ''}{', ' if city and region else ''}{region or ''}\n"

    if balance is not None:
        text += f"Баланс (по данным API, если есть): {fmt_int(balance)} ₽\n"

    text += "\n<b>Склады</b>\n" + "\n".join(wh_lines)
    return text
