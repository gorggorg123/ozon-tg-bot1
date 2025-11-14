import inspect
import logging
import os

import httpx
from fastapi import APIRouter, Request

from .finance import build_fin_today_message
from .ozon_client import build_seller_info_message

logger = logging.getLogger("ozon_tg_bot")

router = APIRouter()

TG_BOT_TOKEN = os.environ["TG_BOT_TOKEN"]
TG_API_URL = f"https://api.telegram.org/bot{TG_BOT_TOKEN}"


def tg_call(method: str, payload: dict) -> dict:
    """Низкоуровневый вызов Telegram Bot API."""
    resp = httpx.post(f"{TG_API_URL}/{method}", json=payload, timeout=15)
    data = resp.json()

    if not data.get("ok"):
        desc = str(data.get("description", "")).lower()
        code = data.get("error_code")

        # ВАЖНО: игнорируем 'message is not modified'
        if code == 400 and "message is not modified" in desc:
            logger.info("Telegram %s: message is not modified, игнорируем", method)
            return data

        logger.error("Telegram %s ERROR: %s", method, data)
        raise RuntimeError(f"Telegram {method} -> {data}")

    return data


def send_message(chat_id: int, text: str, reply_markup: dict | None = None):
    payload: dict = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup

    return tg_call("sendMessage", payload)


def edit_message_text(
    chat_id: int,
    message_id: int,
    text: str,
    reply_markup: dict | None = None,
):
    payload: dict = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup

    return tg_call("editMessageText", payload)


# --- Клавиатуры -----------------------------------------------------------

# Главное меню
kb_root = {
    "inline_keyboard": [
        [
            {"text": "💰 Финансы за сегодня", "callback_data": "fin_today"},
        ],
        [
            {"text": "ℹ️ Аккаунт Ozon", "callback_data": "seller_info"},
        ],
    ]
}

# Клавиатура для экранов с отчётами / информацией
kb_back = {
    "inline_keyboard": [
        [
            {"text": "🔙 В меню", "callback_data": "back_to_menu"},
        ]
    ]
}


# --- Вспомогалки ---------------------------------------------------------

async def _get_fin_today_message() -> str:
    """
    Универсальный обёртка над build_fin_today_message.

    Работает и если build_fin_today_message является обычной функцией,
    и если она async (корутина).
    """
    result = build_fin_today_message()
    if inspect.iscoroutine(result):
        result = await result
    return result


async def _handle_command_start(chat_id: int):
    text = (
        "Привет! 😊 Я бот на FastAPI + Render.\n"
        "⚙️ Сейчас умею:\n"
        "• <b>/fin_today</b> — сводка по финансам за сегодня (API Ozon)\n"
        "• <b>/seller_info</b> — информация об аккаунте продавца Ozon\n\n"
        "Выбери действие ниже 👇"
    )
    send_message(chat_id, text, kb_root)


async def _handle_fin_today(chat_id: int, message_id: int | None = None):
    try:
        msg = await _get_fin_today_message()
    except Exception as e:
        logger.exception("Ошибка при получении финансов за сегодня")
        msg = f"⚠️ Не удалось получить финансы за сегодня.\n\n<code>{e}</code>"

    if message_id is None:
        send_message(chat_id, msg, kb_back)
    else:
        edit_message_text(chat_id, message_id, msg, kb_back)


async def _handle_seller_info(chat_id: int, message_id: int | None = None):
    try:
        msg = await build_seller_info_message()
    except Exception as e:
        logger.exception("Ошибка при получении seller_info")
        msg = f"⚠️ Не удалось получить информацию об аккаунте Ozon.\n\n<code>{e}</code>"

    if message_id is None:
        send_message(chat_id, msg, kb_back)
    else:
        edit_message_text(chat_id, message_id, msg, kb_back)


async def _handle_back_to_menu(chat_id: int, message_id: int):
    text = "Главное меню. Выбери действие 👇"
    edit_message_text(chat_id, message_id, text, kb_root)


# --- Основной webhook -----------------------------------------------------

@router.post("/tg")
async def telegram_webhook(request: Request):
    update = await request.json()
    logger.info("Telegram update: %s", update)

    # 1) Обычные сообщения
    message = update.get("message") or update.get("edited_message")
    if message:
        chat_id = message["chat"]["id"]
        text = (message.get("text") or "").strip()

        if text == "/start":
            await _handle_command_start(chat_id)
            return {"ok": True}

        if text == "/fin_today":
            await _handle_fin_today(chat_id, message_id=None)
            return {"ok": True}

        if text == "/seller_info":
            await _handle_seller_info(chat_id, message_id=None)
            return {"ok": True}

        # Любой другой текст — просто показываем меню
        await _handle_command_start(chat_id)
        return {"ok": True}

    # 2) Callback-кнопки
    callback = update.get("callback_query")
    if callback:
        data = callback.get("data") or ""
        message = callback["message"]
        chat_id = message["chat"]["id"]
        message_id = message["message_id"]

        if data == "fin_today":
            await _handle_fin_today(chat_id, message_id)
            return {"ok": True}

        if data == "seller_info":
            await _handle_seller_info(chat_id, message_id)
            return {"ok": True}

        if data == "back_to_menu":
            await _handle_back_to_menu(chat_id, message_id)
            return {"ok": True}

    # 3) Всё остальное (service messages и т.п.)
    return {"ok": True}
