import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, Message
from fastapi import FastAPI
from dotenv import load_dotenv

from botapp.account import get_account_info_text
from botapp.finance import get_finance_today_text
from botapp.keyboards import (
    MenuCallbackData,
    account_keyboard,
    fbo_menu_keyboard,
    main_menu_keyboard,
    reviews_navigation_keyboard,
    reviews_periods_keyboard,
)
from botapp.orders import get_orders_today_text
from botapp.ozon_client import get_client
from botapp.reviews import (
    get_latest_review,
    get_reviews_menu_text,
    get_reviews_period_view,
    shift_reviews_view,
)
from botapp.reviews_ai import draft_reply

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("main")

TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN", "").strip()
OZON_CLIENT_ID = os.getenv("OZON_CLIENT_ID", "").strip()
OZON_API_KEY = os.getenv("OZON_API_KEY", "").strip()

if not TG_BOT_TOKEN:
    raise RuntimeError("TG_BOT_TOKEN is not set")
if not OZON_CLIENT_ID or not OZON_API_KEY:
    raise RuntimeError("OZON_CLIENT_ID / OZON_API_KEY are not set")

router = Router()
_last_reviews_period = "today"


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    text = "Добро пожаловать! Выберите раздел в меню."
    await message.answer(text, reply_markup=main_menu_keyboard())


@router.message(Command("fin_today"))
@router.message(F.text == "📊 Финансы за сегодня")
async def cmd_fin_today(message: Message) -> None:
    text = await get_finance_today_text()
    await message.answer(text, reply_markup=main_menu_keyboard())


@router.message(Command("account"))
@router.message(F.text == "👤 Аккаунт Ozon")
async def cmd_account(message: Message) -> None:
    text = await get_account_info_text()
    await message.answer(text, reply_markup=account_keyboard())


@router.message(Command("fbo"))
@router.message(F.text == "📦 FBO")
async def cmd_fbo(message: Message) -> None:
    text = await get_orders_today_text()
    await message.answer(text, reply_markup=fbo_menu_keyboard())


@router.message(Command("reviews"))
@router.message(F.text == "⭐ Отзывы")
async def cmd_reviews(message: Message) -> None:
    text = await get_reviews_menu_text()
    await message.answer(text, reply_markup=reviews_periods_keyboard())


async def _send_reviews_period(callback: CallbackQuery, period_key: str) -> None:
    """Общий помощник для смены периода отзывов."""

    global _last_reviews_period
    _last_reviews_period = period_key
    view = await get_reviews_period_view(callback.from_user.id, period_key)
    markup = reviews_navigation_keyboard(period_key, view.has_prev, view.has_next)

    try:
        if callback.message.text == view.text:
            await callback.answer("Этот период уже выбран")
            return
        await callback.message.edit_text(view.text, reply_markup=markup)
    except TelegramBadRequest as exc:
        if "message is not modified" in str(exc):
            await callback.answer("Этот период уже выбран")
        else:
            await callback.message.answer(view.text, reply_markup=markup)


@router.callback_query(MenuCallbackData.filter(F.section == "home"))
async def cb_home(callback: CallbackQuery, callback_data: MenuCallbackData) -> None:
    await callback.answer()
    await callback.message.answer("Главное меню", reply_markup=main_menu_keyboard())


@router.callback_query(MenuCallbackData.filter(F.section == "fbo"))
async def cb_fbo(callback: CallbackQuery, callback_data: MenuCallbackData) -> None:
    await callback.answer()
    action = callback_data.action
    if action == "summary":
        text = await get_orders_today_text()
        try:
            await callback.message.edit_text(text, reply_markup=fbo_menu_keyboard())
        except TelegramBadRequest:
            await callback.message.answer(text, reply_markup=fbo_menu_keyboard())
    elif action == "month":
        await callback.message.answer(
            "Месячная сводка пока в разработке, покажем как только будет готово.",
            reply_markup=fbo_menu_keyboard(),
        )
    elif action == "filter":
        await callback.message.answer("Фильтр скоро", reply_markup=fbo_menu_keyboard())


@router.callback_query(MenuCallbackData.filter(F.section == "account"))
async def cb_account(callback: CallbackQuery, callback_data: MenuCallbackData) -> None:
    await callback.answer()
    text = await get_account_info_text()
    await callback.message.answer(text, reply_markup=account_keyboard())


@router.callback_query(MenuCallbackData.filter(F.section == "reviews"))
async def cb_reviews(callback: CallbackQuery, callback_data: MenuCallbackData) -> None:
    action = callback_data.action
    if action == "period":
        await callback.answer()
        period_key = callback_data.extra or "today"
        await _send_reviews_period(callback, period_key)
        return

    if action in {"nav_prev", "nav_next"}:
        await callback.answer()
        step = -1 if action == "nav_prev" else 1
        view = await shift_reviews_view(callback.from_user.id, step)
        if not view:
            await callback.message.answer(
                "Выберите период отзывов", reply_markup=reviews_periods_keyboard()
            )
            return
        markup = reviews_navigation_keyboard(view.period, view.has_prev, view.has_next)
        try:
            if callback.message.text == view.text:
                await callback.answer("Этот отзыв уже показан")
                return
            await callback.message.edit_text(view.text, reply_markup=markup)
        except TelegramBadRequest as exc:
            if "message is not modified" in str(exc):
                await callback.answer("Этот отзыв уже показан")
            else:
                await callback.message.answer(view.text, reply_markup=markup)
        return

    if action == "ai":
        await callback.answer()
        review = await get_latest_review(_last_reviews_period, callback.from_user.id)
        if not review:
            await callback.message.answer("Свежих отзывов в выбранном периоде нет.")
            return
        reply = await draft_reply(review)
        await callback.message.answer(f"💡 Черновик ответа:\n{reply}")
        return

    if action == "back_periods":
        await callback.answer()
        text = await get_reviews_menu_text()
        try:
            await callback.message.edit_text(text, reply_markup=reviews_periods_keyboard())
        except TelegramBadRequest:
            await callback.message.answer(text, reply_markup=reviews_periods_keyboard())
        return


def build_dispatcher() -> Dispatcher:
    dp = Dispatcher()
    dp.include_router(router)
    return dp


bot = Bot(
    token=TG_BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)
dp = build_dispatcher()
app = FastAPI()


async def start_bot() -> None:
    logger.info("Запускаю Telegram-бота (long polling)…")
    await dp.start_polling(
        bot,
        allowed_updates=dp.resolve_used_update_types(),
    )


@app.on_event("startup")
async def on_startup() -> None:
    logger.info("Startup: validating Ozon credentials and creating polling task")
    # убедимся, что креды присутствуют, инициализируя клиент
    get_client()
    asyncio.create_task(start_bot())


@app.on_event("shutdown")
async def on_shutdown() -> None:
    logger.info("Shutdown: closing Ozon client and bot")
    try:
        client = get_client()
    except Exception:
        client = None
    if client:
        await client.aclose()
    await bot.session.close()


@app.get("/")
async def root() -> dict:
    return {"status": "ok", "detail": "Ozon bot is running"}


__all__ = ["app", "bot", "dp", "router"]
