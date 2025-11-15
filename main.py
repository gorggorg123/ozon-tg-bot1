import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from dotenv import load_dotenv

from botapp import finance, orders
from botapp.tg import main_menu_keyboard, NOT_IMPLEMENTED_TEXT


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def cmd_start(message: Message) -> None:
    text = (
        "Привет! 😊 Я бот для аналитики Ozon Seller (Python + aiogram).\n\n"
        "Сейчас умею:\n"
        "• /fin_today — финансы за сегодня (по API Ozon)\n"
        "• /orders_today — FBO-заказы за сегодня\n\n"
        "Также можно просто нажимать кнопки в меню."
    )
    await message.answer(text, reply_markup=main_menu_keyboard)


async def cmd_fin_today(message: Message) -> None:
    try:
        text = await finance.get_finance_today_text()
        await message.answer(text)
    except Exception as e:
        logger.exception("Ошибка при получении финансов: %s", e)
        await message.answer(
            "⚠️ Не удалось получить финансы за сегодня.\n"
            f"Ошибка: {e}"
        )


async def cmd_orders_today(message: Message) -> None:
    try:
        text = await orders.get_orders_today_text()
        await message.answer(text)
    except Exception as e:
        logger.exception("Ошибка при получении заказов: %s", e)
        await message.answer(
            "⚠️ Не удалось получить заказы за сегодня.\n"
            f"Ошибка: {e}"
        )


async def cmd_not_implemented(message: Message) -> None:
    await message.answer(NOT_IMPLEMENTED_TEXT)


def setup_routes(dp: Dispatcher) -> None:
    # /start
    dp.message.register(cmd_start, CommandStart())

    # Финансы
    dp.message.register(cmd_fin_today, Command("fin_today"))
    dp.message.register(cmd_fin_today, F.text == "🏦 Финансы за сегодня")

    # Заказы
    dp.message.register(cmd_orders_today, Command("orders_today"))
    dp.message.register(cmd_orders_today, F.text == "📦 Заказы за сегодня")

    # Остальные разделы пока-заглушки
    dp.message.register(
        cmd_not_implemented,
        F.text.in_(
            [
                "📂 Аккаунт Ozon",
                "📊 Полная аналитика",
                "📦 FBO",
                "⭐ Отзывы",
                "🧠 ИИ",
            ]
        ),
    )


async def main() -> None:
    load_dotenv()

    token = os.getenv("TG_BOT_TOKEN")
    if not token:
        raise RuntimeError("Не задан TG_BOT_TOKEN в .env")

    bot = Bot(token=token, parse_mode="HTML")
    dp = Dispatcher()

    setup_routes(dp)

    logger.info("Запускаю бота…")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
