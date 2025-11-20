"""Набор клавиатур и фабрик callback_data для навигации бота."""

from __future__ import annotations

from typing import Optional

from aiogram.filters.callback_data import CallbackData
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)


class MenuCallbackData(CallbackData, prefix="menu"):
    """Универсальный callback для внутренних меню.

    section: название раздела (reviews, fbo, account, home)
    action: действие внутри раздела (period/nav/summary/etc)
    extra: дополнительный параметр (период, индекс и т.д.)
    """

    section: str
    action: str
    extra: Optional[str] = None


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Reply-клавиатура главного меню."""

    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 Финансы за сегодня")],
            [KeyboardButton(text="📦 FBO")],
            [KeyboardButton(text="⭐ Отзывы")],
            [KeyboardButton(text="👤 Аккаунт Ozon")],
        ],
        resize_keyboard=True,
    )


def back_home_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура с одной кнопкой возврата в главное меню."""

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🏠 В меню",
                    callback_data=MenuCallbackData(section="home", action="open").pack(),
                )
            ]
        ]
    )


def fbo_menu_keyboard() -> InlineKeyboardMarkup:
    """Инлайн-меню раздела FBO."""

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📦 Сводка",
                    callback_data=MenuCallbackData(section="fbo", action="summary").pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="📅 Месяц",
                    callback_data=MenuCallbackData(section="fbo", action="month").pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔍 Фильтр",
                    callback_data=MenuCallbackData(section="fbo", action="filter").pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="🏠 В меню",
                    callback_data=MenuCallbackData(section="home", action="open").pack(),
                )
            ],
        ]
    )


def reviews_periods_keyboard() -> InlineKeyboardMarkup:
    """Инлайн-меню выбора периода отзывов."""

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Сегодня",
                    callback_data=MenuCallbackData(section="reviews", action="period", extra="today").pack(),
                ),
                InlineKeyboardButton(
                    text="7 дней",
                    callback_data=MenuCallbackData(section="reviews", action="period", extra="week").pack(),
                ),
                InlineKeyboardButton(
                    text="Месяц",
                    callback_data=MenuCallbackData(section="reviews", action="period", extra="month").pack(),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🏠 В меню",
                    callback_data=MenuCallbackData(section="home", action="open").pack(),
                )
            ],
        ]
    )


def reviews_navigation_keyboard(period: str, has_prev: bool, has_next: bool) -> InlineKeyboardMarkup:
    """Клавиатура для просмотра отдельного отзыва."""

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="◀ Предыдущий",
                    callback_data=MenuCallbackData(section="reviews", action="nav_prev", extra=period).pack(),
                ),
                InlineKeyboardButton(
                    text="Следующий ▶",
                    callback_data=MenuCallbackData(section="reviews", action="nav_next", extra=period).pack(),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="✍ Ответ ИИ",
                    callback_data=MenuCallbackData(section="reviews", action="ai", extra=period).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="📅 Сменить период",
                    callback_data=MenuCallbackData(section="reviews", action="back_periods").pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="🏠 В меню",
                    callback_data=MenuCallbackData(section="home", action="open").pack(),
                )
            ],
        ]
    )


def account_keyboard() -> InlineKeyboardMarkup:
    """Инлайн-меню для раздела аккаунта (пока только возврат в меню)."""

    return back_home_keyboard()


__all__ = [
    "MenuCallbackData",
    "main_menu_keyboard",
    "back_home_keyboard",
    "fbo_menu_keyboard",
    "reviews_periods_keyboard",
    "reviews_navigation_keyboard",
    "account_keyboard",
]
