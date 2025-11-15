# main.py (фрагменты)

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery

from botapp.tg import main_menu_kb
from botapp.finance import get_finance_today_text
from botapp.orders import get_orders_today_text
from botapp.account import get_account_info_text
from botapp.reviews import get_reviews_menu_text  # как у тебя сейчас

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    text = (
        "Этот раздел ещё в разработке.\n\n"
        "Сейчас доступны:"
    )
    await message.answer(text, reply_markup=main_menu_kb())


# --- callbacks ---

@router.callback_query(F.data == "fin_today")
async def cb_fin_today(callback: CallbackQuery) -> None:
    await callback.answer()  # закрываем часы
    text = await get_finance_today_text()
    await callback.message.answer(text)


@router.callback_query(F.data == "orders_today")
async def cb_orders_today(callback: CallbackQuery) -> None:
    await callback.answer()
    text = await get_orders_today_text()
    await callback.message.answer(text)


@router.callback_query(F.data == "account_info")
async def cb_account_info(callback: CallbackQuery) -> None:
    await callback.answer()
    text = await get_account_info_text()
    await callback.message.answer(text)


@router.callback_query(F.data == "full_analytics")
async def cb_full_analytics(callback: CallbackQuery) -> None:
    await callback.answer()
    # пока заглушка, позже допилим по Ульянову
    await callback.message.answer("📊 Полная аналитика скоро будет доступна.")


@router.callback_query(F.data == "reviews")
async def cb_reviews(callback: CallbackQuery) -> None:
    await callback.answer()
    text = await get_reviews_menu_text()
    await callback.message.answer(text)
