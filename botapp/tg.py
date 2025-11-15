# botapp/tg.py
from __future__ import annotations

import logging

from aiogram import Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

from .ozon_client import OzonClient
from .finance import get_finance_today_text, get_finance_month_summary_text
from .orders import get_orders_today_text, get_orders_month_summary_text
from .account import get_account_info_text
from .reviews import get_reviews_month_text

logger = logging.getLogger(__name__)

BTN_FIN_TODAY = "🏦 Финансы за сегодня"
BTN_ORDERS_TODAY = "📦 Заказы за сегодня"
BTN_ACCOUNT = "🧾 Аккаунт Ozon"
BTN_FULL = "📊 Полная аналитика"
BTN_REVIEWS = "⭐ Отзывы"


def make_main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_FIN_TODAY)],
            [KeyboardButton(text=BTN_ORDERS_TODAY)],
            [KeyboardButton(text=BTN_ACCOUNT)],
            [KeyboardButton(text=BTN_FULL)],
            [KeyboardButton(text=BTN_REVIEWS)],
        ],
        resize_keyboard=True,
    )


def register_handlers(dp: Dispatcher, ozon: OzonClient) -> None:
    kb = make_main_keyboard()

    @dp.message(CommandStart())
    async def cmd_start(message: Message) -> None:
        text = (
            "Привет! 😊 Я бот для аналитики Ozon Seller.\n\n"
            "Сейчас умею:\n"
            f"• {BTN_FIN_TODAY}\n"
            f"• {BTN_ORDERS_TODAY}\n"
            f"• {BTN_ACCOUNT}\n"
            f"• {BTN_FULL}\n"
            f"• {BTN_REVIEWS}"
        )
        await message.answer(text, reply_markup=kb)

    @dp.message(F.text == BTN_FIN_TODAY)
    async def handle_fin_today(message: Message) -> None:
        try:
            text = await get_finance_today_text(ozon)
        except Exception as e:  # noqa: BLE001
            logger.exception("Ошибка при получении финансов за сегодня")
            text = (
                "⚠️ Не удалось получить финансы за сегодня.\n"
                f"Ошибка: {e}"
            )
        await message.answer(text, reply_markup=kb)

    @dp.message(F.text == BTN_ORDERS_TODAY)
    async def handle_orders_today(message: Message) -> None:
        try:
            text = await get_orders_today_text(ozon)
        except Exception as e:  # noqa: BLE001
            logger.exception("Ошибка при получении заказов")
            text = (
                "⚠️ Не удалось получить заказы за сегодня.\n"
                f"Ошибка: {e}"
            )
        await message.answer(text, reply_markup=kb)

    @dp.message(F.text == BTN_ACCOUNT)
    async def handle_account(message: Message) -> None:
        try:
            text = await get_account_info_text(ozon)
        except Exception as e:  # noqa: BLE001
            logger.exception("Ошибка при получении информации об аккаунте")
            text = (
                "⚠️ Не удалось получить данные аккаунта.\n"
                f"Ошибка: {e}"
            )
        await message.answer(text, reply_markup=kb)

    @dp.message(F.text == BTN_FULL)
    async def handle_full(message: Message) -> None:
        """
        Упрощённая «Полная аналитика» по Ульянову:
        финансы + FBO за текущий месяц в одном сообщении.
        """
        try:
            fin = await get_finance_month_summary_text(ozon)
            fbo = await get_orders_month_summary_text(ozon)
            text = f"<b>📊 Полная аналитика (текущий месяц)</b>\n\n{fin}\n\n{fbo}"
        except Exception as e:  # noqa: BLE001
            logger.exception("Ошибка полной аналитики")
            text = (
                "⚠️ Не удалось рассчитать полную аналитику.\n"
                f"Ошибка: {e}"
            )
        await message.answer(text, reply_markup=kb)

    @dp.message(F.text == BTN_REVIEWS)
    async def handle_reviews(message: Message) -> None:
        try:
            text = await get_reviews_month_text(ozon)
        except Exception as e:  # noqa: BLE001
            logger.exception("Ошибка при получении отзывов")
            text = (
                "⚠️ Не удалось получить отзывы.\n"
                f"Ошибка: {e}"
            )
        await message.answer(text, reply_markup=kb)
