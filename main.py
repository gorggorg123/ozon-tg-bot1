import asyncio
import contextlib
import logging
import os

from fastapi import FastAPI

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from botapp.finance import get_finance_today_text
from botapp.orders import get_orders_today_text

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("main")

TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
if not TG_BOT_TOKEN:
    raise RuntimeError("TG_BOT_TOKEN is not set")

bot = Bot(
    token=TG_BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)
dp = Dispatcher()
app = FastAPI()


# ========= КЛАВИАТУРА =========
def main_menu_inline_kb() -> InlineKeyboardMarkup:
    """
    Главное меню — ИНЛАЙН-клавиатура (кнопки под сообщением).
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🏦 Финансы за сегодня", callback_data="fin_today")],
            [InlineKeyboardButton(text="📦 Заказы за сегодня", callback_data="orders_today")],
            [InlineKeyboardButton(text="📂 Аккаунт Ozon", callback_data="account_info")],
            [InlineKeyboardButton(text="📊 Полная аналитика", callback_data="full_analytics")],
        ]
    )


# ========= ХЕНДЛЕРЫ /start и команды =========
@dp.message(CommandStart())
async def cmd_start(message: Message) -> None:
    text = (
        "Этот раздел ещё в разработке.\n\n"
        "Сейчас доступны:\n"
        "• 🏦 Финансы за сегодня\n"
        "• 📦 Заказы за сегодня"
    )
    await message.answer(text, reply_markup=main_menu_inline_kb())


@dp.message(Command("fin_today"))
async def cmd_fin_today(message: Message) -> None:
    try:
        text = await get_finance_today_text()
    except Exception as e:
        logger.exception("Ошибка при получении финансов за сегодня: %s", e)
        text = f"⚠️ Не удалось получить финансы за сегодня.\nОшибка: {e}"
    await message.answer(text)


@dp.message(Command("orders_today"))
async def cmd_orders_today(message: Message) -> None:
    try:
        text = await get_orders_today_text()
    except Exception as e:
        logger.exception("Ошибка при получении заказов: %s", e)
        text = f"⚠️ Не удалось получить заказы за сегодня.\nОшибка: {e}"
    await message.answer(text)


# ========= CALLBACK-и от инлайн-кнопок =========
@dp.callback_query(F.data == "fin_today")
async def cb_fin_today(callback: CallbackQuery) -> None:
    await callback.answer()
    try:
        text = await get_finance_today_text()
    except Exception as e:
        logger.exception("Ошибка при получении финансов за сегодня: %s", e)
        text = f"⚠️ Не удалось получить финансы за сегодня.\nОшибка: {e}"
    await callback.message.answer(text)


@dp.callback_query(F.data == "orders_today")
async def cb_orders_today(callback: CallbackQuery) -> None:
    await callback.answer()
    try:
        text = await get_orders_today_text()
    except Exception as e:
        logger.exception("Ошибка при получении заказов: %s", e)
        text = f"⚠️ Не удалось получить заказы за сегодня.\nОшибка: {e}"
    await callback.message.answer(text)


@dp.callback_query(F.data == "account_info")
async def cb_account_info(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer("🗂 Раздел «Аккаунт Ozon» ещё в разработке.")


@dp.callback_query(F.data == "full_analytics")
async def cb_full_analytics(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer("📊 Раздел «Полная аналитика» ещё в разработке.")


# ========= FASTAPI + запуск бота на Render =========
@app.get("/")
async def root():
    return {"status": "ok", "message": "Ozon TG bot is running"}


_bot_task: asyncio.Task | None = None


async def _run_bot() -> None:
    logger.info("Запускаю Telegram-бота (long polling)…")
    await dp.start_polling(bot)


@app.on_event("startup")
async def on_startup() -> None:
    global _bot_task
    loop = asyncio.get_event_loop()
    _bot_task = loop.create_task(_run_bot())
    logger.info("Startup completed: bot task created.")


@app.on_event("shutdown")
async def on_shutdown() -> None:
    global _bot_task
    if _bot_task:
        _bot_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await _bot_task
    logger.info("Shutdown completed.")
