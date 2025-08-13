import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart

TOKEN = os.getenv("BOT_TOKEN")  # Токен берём из переменных окружения Render
INVITE_LINK = "https://t.me/CryptoWorkBot?start="  # Твоя ссылка

bot = Bot(token=TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def start(message: types.Message):
    user_id = message.from_user.id
    invite_link = f"{INVITE_LINK}{user_id}"
    await message.answer(
        f"👋 Привет, {message.from_user.first_name}!\n\n"
        f"👥 Приглашай друзей и получай 0.1 TON за каждого!\n\n"
        f"🔗 Твоя ссылка:\n{invite_link}"
    )

async def run_bot():
    while True:  # бесконечный цикл перезапуска
        try:
            print("🚀 Бот запущен и ждёт команды...")
            await dp.start_polling(bot)
        except Exception as e:
            print(f"⚠️ Ошибка: {e}. Перезапуск через 5 секунд...")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(run_bot())
