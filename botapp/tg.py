import os
from typing import Any, Dict, Optional

import httpx
from fastapi import APIRouter, Request

from .finance import build_fin_today_message
from .ozon_client import build_seller_info_message

BOT_TOKEN = os.getenv("TG_BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError("Не задан TG_BOT_TOKEN в переменных окружения")

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

router = APIRouter()


async def tg_call(method: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Универсальный вызов Telegram Bot API.
    Не кидает исключения при ошибке — только логирует.
    """
    url = f"{TELEGRAM_API}/{method}"
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(url, json=payload)
    data = resp.json()

    if not data.get("ok"):
        # Просто логируем, чтобы бот не падал с 500
        print(f"Telegram {method} ERROR: {data}")

    return data


async def send_message(
    chat_id: int,
    text: str,
    reply_markup: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
    }
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup
    return await tg_call("sendMessage", payload)


# ---------- Клавиатуры ----------

KB_ROOT: Dict[str, Any] = {
    "keyboard": [
        [{"text": "📊 Полная аналитика"}],
        [{"text": "📦 FBO"}],
        [{"text": "💰 Финансы"}],
        [{"text": "⭐️ Отзывы"}],
        [{"text": "🧠 ИИ"}],
        [{"text": "ℹ️ Аккаунт Ozon"}],  # новая кнопка
    ],
    "resize_keyboard": True,
}


WELCOME_TEXT = (
    "Привет! 😊 Я бот на FastAPI + Render.\n\n"
    "⚙️ Сейчас умею:\n"
    "/fin_today — сводка по финансам за сегодня (по API Ozon)\n"
    "/seller_info — информация о продавце (через ozonapi-async)\n\n"
    "Выберите раздел в меню ниже 👇"
)


# ---------- Webhook ----------


@router.post("/tg")
async def telegram_webhook(request: Request):
    update = await request.json()
    print("Telegram update:", update)

    message = update.get("message") or update.get("edited_message")
    if not message:
        # Игнорируем callback_query и прочее, пока они нам не нужны
        return {"ok": True}

    chat_id: int = message["chat"]["id"]
    text: str = message.get("text") or ""

    # --- команды ---

    if text.startswith("/start"):
        await send_message(chat_id, WELCOME_TEXT, reply_markup=KB_ROOT)
        return {"ok": True}

    if text == "/fin_today" or text == "💰 Финансы":
        try:
            msg = build_fin_today_message()  # синхронная функция, как и раньше
        except Exception as e:
            msg = f"⚠️ Не удалось получить финансы за сегодня.\n{e}"
        await send_message(chat_id, msg, reply_markup=KB_ROOT)
        return {"ok": True}

    if text in ("/seller_info", "ℹ️ Аккаунт Ozon"):
        try:
            msg = await build_seller_info_message()
        except Exception as e:
            msg = f"⚠️ Не удалось получить информацию о продавце.\n{e}"
        await send_message(chat_id, msg, reply_markup=KB_ROOT)
        return {"ok": True}

    if text == "Меню":
        await send_message(chat_id, "Выберите раздел 👇", reply_markup=KB_ROOT)
        return {"ok": True}

    # --- заглушки для остальных кнопок ---

    if text == "📊 Полная аналитика":
        await send_message(
            chat_id,
            "Раздел 📊 Полная аналитика пока в разработке.",
            reply_markup=KB_ROOT,
        )
        return {"ok": True}

    if text == "📦 FBO":
        await send_message(
            chat_id,
            "Раздел 📦 FBO пока в разработке.",
            reply_markup=KB_ROOT,
        )
        return {"ok": True}

    if text == "⭐️ Отзывы":
        await send_message(
            chat_id,
            "Раздел ⭐️ Отзывы пока в разработке.",
            reply_markup=KB_ROOT,
        )
        return {"ok": True}

    if text == "🧠 ИИ":
        await send_message(
            chat_id,
            "Раздел 🧠 ИИ пока в разработке.",
            reply_markup=KB_ROOT,
        )
        return {"ok": True}

    # --- ответ по умолчанию ---

    await send_message(
        chat_id,
        (
            "Я пока понимаю команды:\n"
            "/fin_today — финансы за сегодня\n"
            "/seller_info — информация о продавце\n\n"
            "И кнопки в меню 👇"
        ),
        reply_markup=KB_ROOT,
    )
    return {"ok": True}
