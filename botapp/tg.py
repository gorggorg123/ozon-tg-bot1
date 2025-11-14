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

TG_API_URL = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/" if TG_BOT_TOKEN else None

# Инлайн-клавиатура главного меню
KB_ROOT_INLINE: dict = {
    "inline_keyboard": [
        [
            {
                "text": "📊 Финансы за сегодня",
                "callback_data": "fin_today",
            }
        ],
        [
            {
                "text": "🧾 Аккаунт Ozon",
                "callback_data": "seller_info",
            }
        ],
        [
            {
                "text": "📊 Полная аналитика",
                "callback_data": "analytics",
            }
        ],
        [
            {
                "text": "📦 FBO",
                "callback_data": "fbo",
            }
        ],
        [
            {
                "text": "⭐ Отзывы",
                "callback_data": "reviews",
            }
        ],
        [
            {
                "text": "🧠 ИИ",
                "callback_data": "ai",
            }
        ],
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
        # Просто логируем ошибку, но не кидаем исключение
        print(f"Telegram {method} error: {data}")

    return data


async def send_message(
    chat_id: int,
    text: str,
    reply_markup: dict | None = None,
) -> None:
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
    Обрабатываем:
      * обычные сообщения (message, edited_message)
      * нажатия на инлайн-кнопки (callback_query)
    """
    update = await request.json()
    print("Telegram update:", update)

    # --- 1) Обработка инлайн-кнопок (callback_query) ---
    callback_query = update.get("callback_query")
    if callback_query:
        cq_id = callback_query.get("id")
        message = callback_query.get("message") or {}
        chat = message.get("chat") or {}
        chat_id = chat.get("id")
        data = callback_query.get("data") or ""

        if chat_id is None:
            return {"ok": True}

        # Ответ на конкретные callback_data
        if data == "fin_today":
            try:
                msg = await build_fin_today_message()
            except Exception as e:
                msg = f"⚠️ Не удалось получить финансы за сегодня.\nОшибка: {e!s}"

            await send_message(chat_id, msg, reply_markup=KB_ROOT_INLINE)

        elif data == "seller_info":
            try:
                msg = await build_seller_info_message()
            except Exception as e:
                msg = f"⚠️ Не удалось получить данные аккаунта Ozon.\nОшибка: {e!s}"

            await send_message(chat_id, msg, reply_markup=KB_ROOT_INLINE)

        elif data == "analytics":
            await send_message(
                chat_id,
                "Раздел *«📊 Полная аналитика»* пока в разработке.\n"
                "Данные будем тянуть через SellerAPI Ульянова (ozonapi-async).",
                reply_markup=KB_ROOT_INLINE,
            )

        elif data == "fbo":
            await send_message(
                chat_id,
                "Раздел *«📦 FBO»* пока в разработке.\n"
                "Позже сюда добавим отчёты по складам/остаткам через SellerAPI.",
                reply_markup=KB_ROOT_INLINE,
            )

        elif data == "reviews":
            await send_message(
                chat_id,
                "Раздел *«⭐ Отзывы»* пока в разработке.",
                reply_markup=KB_ROOT_INLINE,
            )

        elif data == "ai":
            await send_message(
                chat_id,
                "Раздел *«🧠 ИИ»* пока в разработке.\n"
                "План: брифинг, цели месяца, прогноз, план закупок и свободные вопросы.",
                reply_markup=KB_ROOT_INLINE,
            )

        # Ответ Telegram, чтобы убрать "часики" на кнопке
        if cq_id:
            await tg_call(
                "answerCallbackQuery",
                {"callback_query_id": cq_id},
            )

        return {"ok": True}

    # --- 2) Обычные сообщения (message / edited_message) ---
    message = update.get("message") or update.get("edited_message")
    if not message:
        # service message и т.п. – просто ОК
        return {"ok": True}

    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    if chat_id is None:
        return {"ok": True}

    text = message.get("text") or ""

    # --- /start и возврат в меню ---
    if text.startswith("/start") or text == "Меню":
        await send_message(
            chat_id,
            "Привет! 😊 Я бот на FastAPI + Render.\n"
            "Сейчас умею:\n"
            "• *📊 Финансы за сегодня* — сводка по API Ozon\n"
            "• *🧾 Аккаунт Ozon* — данные продавца через SellerAPI Ульянова\n\n"
            "Выберите раздел 👇",
            reply_markup=KB_ROOT_INLINE,
        )
        return {"ok": True}

    # --- Текстовая команда /fin_today (на всякий случай) ---
    if text.startswith("/fin_today"):
        try:
            msg = await build_fin_today_message()
        except Exception as e:
            msg = f"⚠️ Не удалось получить финансы за сегодня.\nОшибка: {e!s}"

        await send_message(chat_id, msg, reply_markup=KB_ROOT_INLINE)
        return {"ok": True}

    # --- Текстовая команда /seller_info ---
    if text.startswith("/seller_info"):
        try:
            msg = await build_seller_info_message()
        except Exception as e:
            msg = f"⚠️ Не удалось получить данные аккаунта Ozon.\nОшибка: {e!s}"

        await send_message(chat_id, msg, reply_markup=KB_ROOT_INLINE)
        return {"ok": True}

    # --- Всё остальное — предлагаем меню ---
    await send_message(
        chat_id,
        "Не понял команду 🤔\nИспользуй меню ниже:",
        reply_markup=KB_ROOT_INLINE,
    )
    return {"ok": True}
