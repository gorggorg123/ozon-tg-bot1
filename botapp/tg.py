# botapp/tg.py
import os
import json

import httpx
from fastapi import APIRouter, Request

from .finance import build_fin_today_message
from .orders import build_orders_today_message
from .ozon_client import build_seller_info_message

router = APIRouter()

TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")

if not TG_BOT_TOKEN:
    print("⚠️ TG_BOT_TOKEN не задан. Бот не сможет работать с Telegram.")

TG_API_URL = (
    f"https://api.telegram.org/bot{TG_BOT_TOKEN}/" if TG_BOT_TOKEN else None
)

# Главное меню — ИНЛАЙН-клавиатура
KB_ROOT = {
    "inline_keyboard": [
        [{"text": "📊 Финансы сегодня", "callback_data": "finance_today"}],
        [{"text": "📦 Заказы за сегодня", "callback_data": "orders_today"}],
        [{"text": "🧾 Аккаунт Ozon", "callback_data": "seller_info"}],
        [{"text": "📊 Полная аналитика", "callback_data": "analytics_full"}],
        [{"text": "📦 FBO", "callback_data": "fbo"}],
        [{"text": "⭐ Отзывы", "callback_data": "reviews"}],
        [{"text": "🧠 ИИ", "callback_data": "ai"}],
    ]
}


async def tg_call(method: str, payload: dict) -> dict:
    """
    Вызов метода Telegram Bot API.
    Ошибки логируем, но не роняем сервер.
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
        # Не поднимаем исключение, чтобы не было 500
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


async def edit_message_text(
    chat_id: int,
    message_id: int,
    text: str,
    reply_markup: dict | None = None,
) -> None:
    payload: dict = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": "Markdown",
    }
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup

    await tg_call("editMessageText", payload)


@router.post("/tg")
async def telegram_webhook(request: Request):
    """
    Единственная точка входа для вебхука Telegram.
    Обрабатываем и message, и callback_query.
    """
    update = await request.json()
    print("Telegram update:", update)

    # Обычное сообщение (/start и т.п.)
    message = update.get("message") or update.get("edited_message")
    if message:
        chat = message.get("chat") or {}
        chat_id = chat.get("id")
        if chat_id is None:
            return {"ok": True}

        text = message.get("text") or ""

        if text.startswith("/start"):
            await send_message(
                chat_id,
                "Выберите раздел 👇",
                reply_markup=KB_ROOT,
            )
            return {"ok": True}

        # На всё остальное — просто показываем меню
        await send_message(
            chat_id,
            "Выберите раздел 👇",
            reply_markup=KB_ROOT,
        )
        return {"ok": True}

    # Callback-запрос от инлайн-клавиатуры
    callback = update.get("callback_query")
    if callback:
        data = callback.get("data") or ""
        cb_message = callback.get("message") or {}
        chat = cb_message.get("chat") or {}
        chat_id = chat.get("id")
        message_id = cb_message.get("message_id")

        if chat_id is None or message_id is None:
            # Всё равно ответим на callback, чтобы Telegram не крутил «часики»
            await tg_call(
                "answerCallbackQuery",
                {"callback_query_id": callback.get("id")},
            )
            return {"ok": True}

        # По умолчанию
        text = "Этот раздел пока не реализован."

        if data == "finance_today":
            try:
                text = await build_fin_today_message()
            except Exception as e:
                text = (
                    "⚠️ Не удалось получить финансы за сегодня.\n"
                    f"Ошибка: `{e!s}`"
                )

        elif data == "orders_today":
            try:
                text = await build_orders_today_message()
            except Exception as e:
                text = (
                    "⚠️ Не удалось получить заказы за сегодня.\n"
                    f"Ошибка: `{e!s}`"
                )

        elif data == "seller_info":
            text = await build_seller_info_message()

        # Остальные callback_data пока заглушки,
        # но сообщение меню всё равно обновляем
        await edit_message_text(
            chat_id,
            message_id,
            text,
            reply_markup=KB_ROOT,
        )

        # Обязательно ответить на callback
        await tg_call(
            "answerCallbackQuery",
            {"callback_query_id": callback.get("id")},
        )

        return {"ok": True}

    # Если ничего не распознали — просто ок
    return {"ok": True}
