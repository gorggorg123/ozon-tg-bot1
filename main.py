from fastapi import FastAPI, Request

app = FastAPI()


@app.get("/")
async def root():
    return {"status": "ok", "message": "Ozon bot is alive"}


@app.post("/tg")
async def telegram_webhook(request: Request):
    data = await request.json()
    # Пока просто печатаем апдейт в консоль
    print("Telegram update:", data)
    return {"ok": True}
