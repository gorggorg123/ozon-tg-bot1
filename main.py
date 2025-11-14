from fastapi import FastAPI
from botapp.tg import router as tg_router

app = FastAPI(title="Ozon Seller Telegram Bot")

# Роут вебхука Телеграма
app.include_router(tg_router)


@app.get("/")
async def root():
    return {
        "ok": True,
        "message": "Ozon Seller × Telegram — бот запущен",
    }
