import os

from dotenv import load_dotenv
from ozonapi import SellerAPI  # из пакета ozonapi-async


# Подгружаем .env (локально). На Render переменные берутся из настроек сервиса.
load_dotenv()


async def build_seller_info_message() -> str:
    """
    Получает информацию о продавце через SellerAPI Ульянова
    и возвращает готовый текст для Telegram.
    """
    # Если client_id / api_key не заданы — сразу понятная ошибка
    client_id = os.getenv("OZON_SELLER_CLIENT_ID")
    api_key = os.getenv("OZON_SELLER_API_KEY")

    if not client_id or not api_key:
        return (
            "⚠️ Не заданы ключи Ozon Seller API.\n\n"
            "Проверь переменные окружения:\n"
            "<code>OZON_SELLER_CLIENT_ID</code>\n"
            "<code>OZON_SELLER_API_KEY</code>"
        )

    async with SellerAPI() as api:
        # Конфиг возьмётся автоматически из .env / переменных окружения
        info = await api.seller_info()

    # Структура в библиотеке такая: info.company.name / info.company.inn
    company = getattr(info, "company", None)
    name = getattr(company, "name", None) if company else None
    inn = getattr(company, "inn", None) if company else None

    lines: list[str] = ["👤 <b>Информация о продавце Ozon</b>"]

    if name:
        lines.append(f"🏢 Компания: <b>{name}</b>")
    if inn:
        lines.append(f"📄 ИНН: <code>{inn}</code>")

    if not name and not inn:
        # На всякий случай, если структура вдруг другая
        lines.append("Не удалось красиво разобрать ответ от Ozon Seller API.")
        lines.append("Но соединение с SellerAPI работает ✅")

    lines.append("")
    lines.append("Данные получены через библиотеку <i>ozonapi-async</i>.")

    return "\n".join(lines)
