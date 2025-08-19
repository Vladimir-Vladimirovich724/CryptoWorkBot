import asyncio
import logging
import json
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo

# Включаем логирование
logging.basicConfig(level=logging.INFO)

# Токен берём из переменной окружения (Render → Environment → BOT_TOKEN)
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("❌ Ошибка: BOT_TOKEN не найден. Добавьте его в Render → Environment.")

# Создаём объекты бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Хранилище покупок (для примера)
purchases = {}

# Главное меню с кнопкой магазина
main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🛒 Магазин", web_app=WebAppInfo(url="https://cryptoworkbot-shop.onrender.com"))]
    ],
    resize_keyboard=True
)

# Команда /start
@dp.message(F.text == "/start")
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Привет! Добро пожаловать в CryptoWorkBot.\n\n"
        "Здесь можно покупать VIP и Бустеры за Telegram Stars ⭐",
        reply_markup=main_kb
    )

# Обработка данных из WebApp
@dp.message(F.web_app_data)
async def handle_web_app_data(message: types.Message):
    try:
        data = json.loads(message.web_app_data.data)
        logging.info(f"📩 Получены данные из WebApp: {data}")  # пишем в логи Render

        if data.get("action") == "buy":
            product = data.get("product")

            if product == "vip":
                purchases.setdefault(message.from_user.id, []).append("vip")
                await message.answer("✅ Поздравляем! 🌟 Вы купили VIP за 20 Stars.")
            elif product == "booster":
                purchases.setdefault(message.from_user.id, []).append("booster")
                await message.answer("✅ Отлично! 🚀 Вы купили Бустер за 10 Stars.")
            else:
                await message.answer("❌ Неизвестный товар.")

        else:
            await message.answer("⚠️ Данные получены, но действие не распознано.")

    except Exception as e:
        logging.error(f"❌ Ошибка при обработке web_app_data: {e}")
        await message.answer(f"Ошибка при обработке покупки: {e}")

# Основной запуск
async def main():
    logging.info("✅ Bot is running!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
