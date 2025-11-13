from fastapi import FastAPI
from app.tg import router as tg_router

app = FastAPI()


@app.get("/")
async def root():
    return {"status": "ok", "message": "Ozon bot is alive"}


# Подключаем Telegram-вебхук
app.include_router(tg_router)
