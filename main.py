# main.py
import asyncio
import logging
import os

from fastapi import FastAPI
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from botapp.ozon_client import OzonClient
from botapp.tg import register_handlers

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("main")

TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN", "")
OZON_CLIENT_ID = os.getenv("OZON_CLIENT_ID", "")
OZON_API_KEY = os.getenv("OZON_API_KEY", "")

if not TG_BOT_TOKEN:
    raise RuntimeError("TG_BOT_TOKEN is not set")
if not OZON_CLIENT_ID or not OZON_API_KEY:
    raise RuntimeError("OZON_CLIENT_ID / OZON_API_KEY are not set")

bot = Bot(
    token=TG_BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)
dp = Dispatcher()

ozon_client = OzonClient(OZON_CLIENT_ID, OZON_API_KEY)
register_handlers(dp, ozon_client)

app = FastAPI()


@app.on_event("startup")
async def on_startup() -> None:
    logger.info("Startup: creating polling task")
    asyncio.create_task(start_bot())


@app.on_event("shutdown")
async def on_shutdown() -> None:
    logger.info("Shutdown: closing Ozon client and bot")
    await ozon_client.aclose()
    await bot.session.close()


async def start_bot() -> None:
    logger.info("Запускаю Telegram-бота (long polling)…")
    await dp.start_polling(
        bot,
        allowed_updates=dp.resolve_used_update_types(),
    )


@app.get("/")
async def root() -> dict:
    return {"status": "ok", "detail": "Ozon bot is running"}
