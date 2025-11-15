# main.py
import os
import asyncio
import logging

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from botapp.finance import get_finance_today_text
from botapp.orders import get_orders_today_text
from botapp.account import get_account_info_text

# ---------- Логирование ----------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("main")

# ---------- Telegram bot ----------
TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN", "").strip()
if not TG_BOT_TOKEN:
    logger.warning("TG_BOT_TOKEN не задан в переменных окружения!")

bot = Bot(
    token=TG_BOT_TOKEN,
    default=DefaultBotProperties(parse_mode="HTML"),
)
dp = Dispatcher()

# ---------- Инлайн-меню ----------
MENU_KB = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🏦 Финансы за сегодня", callback_data="fin_today")],
        [InlineKeyboardButton(text="📦 Заказы за сегодня", callback_data="orders_today")],
        [InlineKeyboardButton(text="🧾 Аккаунт Ozon", callback_data="account")],
        [InlineKeyboardButton(text="📊 Полная аналитика", callback_data="analytics_full")],
    ]
)


# ---------- Handlers ----------

@dp.message(F.text == "/start")
async def cmd_start(message: Message) -> None:
    text = (
        "Этот раздел ещё в разработке.\n\n"
        "Сейчас доступны:\n"
        "• 🏦 Финансы за сегодня\n"
        "• 📦 Заказы за сегодня\n"
        "• 🧾 Аккаунт Ozon\n"
        "• 📊 Полная аналитика (упрощённая)\n"
    )
    await message.answer(text, reply_markup=MENU_KB)


# дублируем на случай, если пользователь нажмёт старые кнопки/введёт текст
@dp.message(F.text.contains("Финансы за сегодня"))
async def cmd_fin_today_text(message: Message) -> None:
    await cmd_fin_today_cb(
        CallbackQuery(message=message, id="", data="fin_today")
    )


@dp.callback_query(F.data == "fin_today")
async def cmd_fin_today_cb(callback: CallbackQuery) -> None:
    await callback.answer()
    try:
        text = await get_finance_today_text()
    except Exception as e:
        logger.exception("Ошибка при получении финансов: %s", e)
        await callback.message.answer(
            f"⚠️ Не удалось получить финансы за сегодня.\nОшибка: {e}"
        )
        return

    await callback.message.answer(text, reply_markup=MENU_KB)


@dp.callback_query(F.data == "orders_today")
async def cmd_orders_today(callback: CallbackQuery) -> None:
    await callback.answer()
    try:
        text = await get_orders_today_text()
    except Exception as e:
        logger.exception("Ошибка при получении заказов: %s", e)
        await callback.message.answer(
            f"⚠️ Не удалось получить заказы за сегодня.\nОшибка: {e}"
        )
        return

    await callback.message.answer(text, reply_markup=MENU_KB)


@dp.callback_query(F.data == "account")
async def cmd_account(callback: CallbackQuery) -> None:
    await callback.answer()
    try:
        text = await get_account_info_text()
    except Exception as e:
        logger.exception("Ошибка при получении данных аккаунта: %s", e)
        await callback.message.answer(
            f"⚠️ Не удалось получить данные аккаунта.\nОшибка: {e}"
        )
        return

    await callback.message.answer(text, reply_markup=MENU_KB)


@dp.callback_query(F.data == "analytics_full")
async def cmd_analytics_full(callback: CallbackQuery) -> None:
    """
    Пока простая заглушка. Позже сюда завезём
    аналитику по Ulianov (finance + FBO + analytics/get-data).
    """
    await callback.answer()
    text = (
        "Этот раздел ещё в разработке.\n\n"
        "Уже можно пользоваться:\n"
        "• 🏦 Финансы за сегодня\n"
        "• 📦 Заказы за сегодня\n"
        "• 🧾 Аккаунт Ozon\n\n"
        "Позже здесь появится полная аналитика по данным OzonAPI."
    )
    await callback.message.answer(text, reply_markup=MENU_KB)


# ---------- FastAPI + запуск бота на Render ----------

app = FastAPI()


@app.on_event("startup")
async def on_startup() -> None:
    logger.info("Startup completed: bot task created.")
    asyncio.create_task(run_bot())


async def run_bot() -> None:
    logger.info("Запускаю Telegram-бота (long polling)…")
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.exception("Polling stopped with error: %s", e)


@app.get("/", response_class=PlainTextResponse)
async def root() -> str:
    return "ok"
