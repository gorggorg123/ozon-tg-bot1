# botapp/account.py
import os
import html
from typing import Any

from ozonapi import SellerAPI


def _esc(s: Any) -> str:
    return html.escape(str(s if s is not None else ""))


async def get_account_info_text() -> str:
    """
    Информация по аккаунту Ozon через библиотеку a-ulianov/OzonAPI.
    Показываем компанию и список складов.
    """

    client_id = os.getenv("OZON_CLIENT_ID")
    api_key = os.getenv("OZON_API_KEY")

    if not client_id or not api_key:
        return (
            "⚠️ Не заданы переменные окружения OZON_CLIENT_ID / OZON_API_KEY.\n"
            "Проверь настройки в Render / .env."
        )

    async with SellerAPI(client_id=client_id, api_key=api_key) as api:
        # seller_info
        seller_info = await api.seller_info()
        warehouses = await api.warehouse_list()

    # Аккуратно превращаем pydantic-модели в dict, чтобы не зависеть от схем
    if hasattr(seller_info, "model_dump"):
        seller_dict = seller_info.model_dump()
    else:
        seller_dict = seller_info  # на всякий

    if hasattr(warehouses, "model_dump"):
        warehouses_dict = warehouses.model_dump()
    else:
        warehouses_dict = warehouses

    company = {}
    if isinstance(seller_dict, dict):
        company = seller_dict.get("company") or {}

    company_name = company.get("name") or "—"
    inn = company.get("inn") or "—"
    ogrn = (
        company.get("ogrn")
        or company.get("ogrn_ip")
        or company.get("ogrn_ogrnip")
        or "—"
    )

    # склады
    wh_list = []
    if isinstance(warehouses_dict, dict):
        wh_list = (
            warehouses_dict.get("result")
            or warehouses_dict.get("warehouses")
            or []
        )
    elif isinstance(warehouses_dict, list):
        wh_list = warehouses_dict

    lines = []
    for w in wh_list[:10]:  # покажем максимум 10
        if hasattr(w, "model_dump"):
            w = w.model_dump()
        if not isinstance(w, dict):
            continue

        name = w.get("name") or w.get("warehouse_name") or "Склад"
        city = w.get("city") or w.get("region") or ""
        w_id = w.get("warehouse_id") or w.get("id")

        parts = [f"• {_esc(name)}"]
        if city:
            parts.append(f"({_esc(city)})")
        if w_id is not None:
            parts.append(f"— ID {_esc(w_id)}")
        lines.append(" ".join(parts))

    wh_count = len(wh_list)

    text = (
        "<b>🧾 Аккаунт Ozon</b>\n"
        f"Компания: <b>{_esc(company_name)}</b>\n"
        f"ИНН: <code>{_esc(inn)}</code>\n"
        f"ОГРН/ОГРНИП: <code>{_esc(ogrn)}</code>\n\n"
        f"<b>🏬 Склады: {wh_count}</b>\n"
    )

    if lines:
        text += "\n".join(lines)
    else:
        text += "Список складов не получен из API."

    return text
