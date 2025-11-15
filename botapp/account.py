# botapp/account.py

from __future__ import annotations

import json
import os
from typing import Any

import httpx

OZON_BASE_URL = "https://api-seller.ozon.ru"
OZON_CLIENT_ID = os.getenv("OZON_CLIENT_ID")
OZON_API_KEY = os.getenv("OZON_API_KEY")


async def _fetch_company_info() -> dict[str, Any]:
    if not OZON_CLIENT_ID or not OZON_API_KEY:
        raise RuntimeError("Не заданы OZON_CLIENT_ID / OZON_API_KEY")

    headers = {
        "Client-Id": OZON_CLIENT_ID,
        "Api-Key": OZON_API_KEY,
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{OZON_BASE_URL}/v1/company/info",
            json={},          # важно: POST с пустым JSON
            headers=headers,
        )
        resp.raise_for_status()
        data: Any = resp.json()

    # Ozon обычно возвращает {"result": {...}}
    if isinstance(data, dict) and isinstance(data.get("result"), dict):
        return data["result"]
    return data


async def get_account_info_text() -> str:
    try:
        info = await _fetch_company_info()
    except Exception as e:
        return (
            "⚠️ Не удалось получить данные аккаунта.\n"
            f"Ошибка: {e}"
        )

    company_name = info.get("name") or info.get("company_name")
    inn = info.get("inn")
    ogrn = info.get("ogrn")
    region = info.get("region")
    email = info.get("email")

    lines = ["👤 *Аккаунт Ozon*:", ""]

    if company_name:
        lines.append(f"🏢 Компания: *{company_name}*")
    if inn:
        lines.append(f"🧾 ИНН: `{inn}`")
    if ogrn:
        lines.append(f"📄 ОГРН: `{ogrn}`")
    if region:
        lines.append(f"📍 Регион: {region}")
    if email:
        lines.append(f"✉️ Email: {email}")

    # На всякий случай приложим сырой JSON снизу
    lines.append("")
    lines.append("`" + json.dumps(info, ensure_ascii=False) + "`")

    return "\n".join(lines)
