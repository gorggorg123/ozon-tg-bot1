import asyncio
from contextlib import asynccontextmanager

from ozonapi import SellerAPI


@asynccontextmanager
async def get_api():
    """
    Универсальный асинхронный контекстный менеджер для SellerAPI.

    Конфигурация берётся из .env / переменных окружения:
    OZON_SELLER_CLIENT_ID, OZON_SELLER_API_KEY и т.д.
    """
    async with SellerAPI() as api:
        yield api


async def build_seller_info_message() -> str:
    """
    Строит текстовое сообщение с информацией об аккаунте Ozon.
    Используется в /seller_info и кнопке 'ℹ️ Аккаунт Ozon'.
    """
    async with SellerAPI() as api:
        info = await api.seller_info()

    company = info.company

    # Защита от None, если каких-то полей нет
    name = company.name or "—"
    inn = company.inn or "—"
    ogrn = getattr(company, "ogrn", None) or "—"

    msg = (
        "<b>ℹ️ Информация об аккаунте Ozon</b>\n\n"
        f"<b>Компания:</b> {name}\n"
        f"<b>ИНН:</b> <code>{inn}</code>\n"
        f"<b>ОГРН:</b> <code>{ogrn}</code>\n"
    )
    return msg


# Небольшой локальный тест, если захочешь проверить из консоли
if __name__ == "__main__":
    async def _test():
        text = await build_seller_info_message()
        print(text)

    asyncio.run(_test())
