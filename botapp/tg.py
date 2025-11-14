import json
import os

import httpx
from fastapi import APIRouter, Request

from .finance import build_fin_today_message
from .ozon_client import build_seller_info_message

router = APIRouter()

TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")

if not TG_BOT_TOKEN:
    print("⚠️ TG_BOT_TOKEN не задан. Бот не сможет отправлять сообщения в Telegram.")

TG_API_URL = (
    f"https://api.telegram.org/bot{TG_BOT_TOKEN}/" if TG_BOT_TOKEN else None
)

# Клавиатура главного меню
KB_ROOT = {
    "keyboard": [
        [{"text": "📊 Полная аналитика"}],
        [{"text": "📦 FBO"}],
        [{"text": "📊 Финансы"}],
        [{"text": "⭐ Отзывы"}],
        [{"text": "🧠 ИИ"}],
        [{"text": "🧾 Аккаунт Ozon"}],
    ],
    "resize_keyboard": True,
}


async def tg_call(method: str, payload: dict) -> dict:
    """
    Вызов метода Telegram Bot API.
    Ошибки логируем, но не роняем сервер (чтобы не было 500 из-за editMessageText).
    """
    if not TG_API_URL:
        raise RuntimeError("TG_BOT_TOKEN не задан.")

    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(TG_API_URL + method, json=payload)

    try:
        data = resp.json()
    except json.JSONDecodeError:
        print(f"Telegram {method} -> не JSON, статус {resp.status_code}")
        return {"ok": False, "status_code": resp.status_code}

    if not data.get("ok"):
        # Просто логируем, но не поднимаем исключение
        print(f"Telegram {method} error: {data}")

    return data


async def send_message(chat_id: int, text: str, reply_markup: dict | None = None) -> None:
    payload: dict = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
    }
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup

    await tg_call("sendMessage", payload)


@router.post("/tg")
async def telegram_webhook(request: Request):
    """
    Единственная точка входа для вебхука.
    Обрабатываем только обычные сообщения (message).
    """
    update = await request.json()
    print("Telegram update:", update)

    message = update.get("message") or update.get("edited_message")
    if not message:
        # Например, service message — просто подтверждаем
        return {"ok": True}

    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    if chat_id is None:
        return {"ok": True}

    text = message.get("text") or ""

    # --- /start + возврат в меню ---
    if text.startswith("/start") or text == "Меню":
        await send_message(
            chat_id,
            "Выберите раздел 👇",
            reply_markup=KB_ROOT,
        )
        return {"ok": True}

    # --- Финансы за сегодня ---
    if text in ("/fin_today", "📊 Финансы"):
        try:
            msg = await build_fin_today_message()
        except Exception as e:
            msg = f"⚠️ Не удалось получить финансы за сегодня.\nОшибка: {e!s}"

        await send_message(chat_id, msg, reply_markup=KB_ROOT)
        return {"ok": True}

    # --- Информация о продавце (SellerAPI Ульянова) ---
    if text in ("/seller_info", "🧾 Аккаунт Ozon"):
        msg = await build_seller_info_message()
        await send_message(chat_id, msg, reply_markup=KB_ROOT)
        return {"ok": True}

    # --- Заглушки для остальных разделов главного меню ---

    if text == "📊 Полная аналитика":
        await send_message(
            chat_id,
            "Раздел *«📊 Полная аналитика»* пока не реализован.\n"
            "Сейчас доступен блок *«📊 Финансы за сегодня»* и информация об аккаунте Ozon.",
            reply_markup=KB_ROOT,
        )
        return
