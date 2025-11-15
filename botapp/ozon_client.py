# botapp/ozon_client.py
import os
import logging
from datetime import datetime, timedelta, date
from typing import Any, Dict, List, Tuple

import httpx

logger = logging.getLogger(__name__)

BASE_URL = "https://api-seller.ozon.ru"
MSK_SHIFT = timedelta(hours=3)


def _iso_z(dt: datetime) -> str:
    """Вернуть ISO-строку в UTC с Z без миллисекунд."""
    return dt.replace(microsecond=0).isoformat() + "Z"


def msk_today_range() -> Tuple[str, str, str]:
    """
    Диапазон на сегодня в МСК, но границы в UTC.
    Возвращает (from_iso, to_iso, pretty_text).
    """
    now_utc = datetime.utcnow()
    now_msk = now_utc + MSK_SHIFT
    d = now_msk.date()

    start_utc = datetime(d.year, d.month, d.day) - MSK_SHIFT
    end_utc = start_utc + timedelta(days=1) - timedelta(seconds=1)

    pretty = (
        f"{d.strftime('%d.%m.%Y')} 00:00 — "
        f"{d.strftime('%d.%m.%Y')} 23:59 (МСК)"
    )
    return _iso_z(start_utc), _iso_z(end_utc), pretty


def msk_current_month_range() -> Tuple[str, str, str]:
    """
    Диапазон с 1-го числа текущего месяца по сегодня (МСК).
    Границы возвращаются в UTC, плюс красивый текст.
    """
    now_utc = datetime.utcnow()
    now_msk = now_utc + MSK_SHIFT
    today = now_msk.date()

    first = date(today.year, today.month, 1)
    if today.month == 12:
        last_calendar = date(today.year, 12, 31)
    else:
        next_first = date(today.year, today.month + 1, 1)
        last_calendar = next_first - timedelta(days=1)

    end_date = today if today <= last_calendar else last_calendar

    start_utc = datetime(first.year, first.month, first.day) - MSK_SHIFT
    end_utc = datetime(
        end_date.year, end_date.month, end_date.day, 23, 59, 59
    ) - MSK_SHIFT

    pretty = (
        f"{first.strftime('%d.%m.%Y')} — "
        f"{end_date.strftime('%d.%m.%Y')} (МСК)"
    )
    return _iso_z(start_utc), _iso_z(end_utc), pretty


def fmt_int(n: float | int) -> str:
    return f"{int(round(n)):,.0f}".replace(",", " ")


def fmt_rub0(n: float | int) -> str:
    return f"{int(round(n)):,.0f} ₽".replace(",", " ")


def s_num(x: Any) -> float:
    try:
        return float(str(x).replace(" ", "").replace(",", ".")) if x is not None else 0.0
    except Exception:
        return 0.0


class OzonClient:
    def __init__(self, client_id: str, api_key: str) -> None:
        self.client_id = client_id.strip()
        self.api_key = api_key.strip()
        self._client = httpx.AsyncClient(
            base_url=BASE_URL,
            timeout=30.0,
            headers={
                "Client-Id": self.client_id,
                "Api-Key": self.api_key,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def post(self, path: str, json: Dict[str, Any]) -> Dict[str, Any]:
        url = path if path.startswith("/") else f"/{path}"
        r = await self._client.post(url, json=json)
        try:
            data = r.json()
        except Exception:
            text = await r.aread()
            logger.error("Ozon %s -> HTTP %s: %r", url, r.status_code, text[:500])
            r.raise_for_status()
            return {}
        if r.status_code >= 400:
            logger.error("Ozon %s -> HTTP %s: %r", url, r.status_code, data)
            r.raise_for_status()
        return data

    # ---------- Финансы ----------

    async def get_finance_totals(
        self, date_from_iso: str, date_to_iso: str
    ) -> Dict[str, Any]:
        body = {
            "date": {"from": date_from_iso, "to": date_to_iso},
            "transaction_type": "all",
        }
        data = await self.post("/v3/finance/transaction/totals", body)
        return data.get("result") or {}

    # ---------- FBO заказы ----------

    async def get_fbo_postings(
        self, date_from_iso: str, date_to_iso: str
    ) -> List[Dict[str, Any]]:
        """
        Полная выборка FBO-заказов за период (как в Ульянове: /v2/posting/fbo/list с пагинацией).
        """
        postings: List[Dict[str, Any]] = []
        limit = 1000
        offset = 0

        for _ in range(60):
            body = {
                "dir": "DESC",
                "filter": {"since": date_from_iso, "to": date_to_iso},
                "limit": limit,
                "offset": offset,
                "with": {
                    "products": True,
                    "financial_data": False,
                    "analytics_data": True,
                },
            }
            data = await self.post("/v2/posting/fbo/list", body)
            page = (
                data.get("result", {}).get("postings")
                or data.get("postings")
                or data.get("result")
                or []
            )
            if not isinstance(page, list) or not page:
                break
            postings.extend(page)
            if len(page) < limit:
                break
            offset += limit

        return postings

    # ---------- Аккаунт ----------

    async def get_company_info(self) -> Dict[str, Any]:
        data = await self.post("/v1/company/info", {})
        return data.get("result") or data

    # ---------- Отзывы ----------

    async def get_reviews(
        self, date_from_iso: str, date_to_iso: str, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        /v1/review/list — как в JS-коде.
        Берём одну страницу (до 100 отзывов) за период.
        """
        body = {
            "page": 1,
            "limit": limit,
            "filter": {
                "date": {
                    "from": date_from_iso[:10],
                    "to": date_to_iso[:10],
                }
            },
        }
        data = await self.post("/v1/review/list", body)
        res = data.get("result") or data
        arr = (
            res.get("reviews")
            or res.get("feedbacks")
            or res.get("items")
            or []
        )
        return arr if isinstance(arr, list) else []
