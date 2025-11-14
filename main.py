from fastapi import FastAPI

from botapp.tg import router as tg_router

app = FastAPI()


@app.get("/")
async def root():
    return {"status": "ok"}


# Вебхук Telegram на /tg
app.include_router(tg_router)
