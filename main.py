import os
import asyncio
import json
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import WebAppInfo

# ==============================
# НАСТРОЙКИ
# ==============================
TOKEN = os.getenv("BOT_TOKEN")  # Токен из Render переменных окружения
BOT_USERNAME = "MenqenqmersareryBot"
MY_ID = 7352855554   # твой ID для админ-команд
REFERRAL_PERCENT = 0.05  

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Простая "база" в памяти (потом можно заменить на БД)
balances = {}
referrals = {}
purchases = {}

# URL твоего мини-приложения
MINI_APP_URL = "https://cryptoworkbot-shop.onrender.com"

# ==============================
# ВЕБ-СЕРВЕР ДЛЯ RENDER
# ==============================
async def handle(request):
    return web.Response(text="✅ Bot is running!")

async def start_webserver():
    app = web.Application()
    app.router.add_get("/", handle)
    port = int(os.getenv("PORT", 10000))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

# ==============================
# ГЛАВНОЕ МЕНЮ
# ==============================
def main_menu():
    kb = InlineKeyboardBuilder()
    kb.button(text="💰 Баланс", callback_data="balance")
    kb.button(text="📋 Задания", callback_data="tasks")
    kb.button(text="👥 Приглашения", callback_data="invite")
    kb.button(text="🛒 Магазин", web_app=WebAppInfo(url=MINI_APP_URL))
    kb.button(text="💸 Вывод", callback_data="withdraw")
    kb.adjust(2)
    return kb.as_markup()

# ==============================
# СТАРТ
# ==============================
@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    user_id = message.from_user.id
    args = message.text.split()

    if user_id not in balances:
        balances[user_id] = 0.0
        referrals[user_id] = []
        purchases[user_id] = []

    # обработка рефералов
    if len(args) > 1:
        try:
            inviter_id = int(args[1])
            if inviter_id != user_id and user_id not in referrals.get(inviter_id, []):
                referrals.setdefault(inviter_id, []).append(user_id)
        except Exception:
            pass

    await message.answer(
        f"👋 Привет, {message.from_user.first_name}!\n"
        f"Добро пожаловать в CryptoWorkBot 💼\n\n"
        f"Выполняй задания, приглашай друзей и зарабатывай TON!",
        reply_markup=main_menu()
    )

# ==============================
# КНОПКИ МЕНЮ
# ==============================
@dp.callback_query(F.data == "balance")
async def balance_callback(callback: types.CallbackQuery):
    bal = balances.get(callback.from_user.id, 0.0)
    await callback.message.answer(f"💰 Ваш баланс: {bal} TON")
    await callback.answer()

@dp.callback_query(F.data == "tasks")
async def tasks_callback(callback: types.CallbackQuery):
    await callback.message.answer("📋 Задания пока отсутствуют")
    await callback.answer()

@dp.callback_query(F.data == "invite")
async def invite_callback(callback: types.CallbackQuery):
    referral_link = f"https://t.me/{BOT_USERNAME}?start={callback.from_user.id}"
    count = len(referrals.get(callback.from_user.id, []))
    await callback.message.answer(
        f"👥 Приглашай друзей и получай 5% от их покупок!\n\n"
        f"🔗 Ваша ссылка:\n{referral_link}\n\n"
        f"Вы пригласили: {count} чел."
    )
    await callback.answer()

@dp.callback_query(F.data == "withdraw")
async def withdraw_callback(callback: types.CallbackQuery):
    await callback.message.answer("💸 Вывод временно недоступен")
    await callback.answer()

# ==============================
# ПОЛУЧЕНИЕ ДАННЫХ ИЗ WEBAPP
# ==============================
@dp.message(F.web_app_data)
async def handle_web_app_data(message: types.Message):
    try:
        data = json.loads(message.web_app_data.data)
        if data["action"] == "buy":
            product = data["product"]
            if product == "vip":
                purchases.setdefault(message.from_user.id, []).append("vip")
                await message.answer("✅ Поздравляем! 🌟 Вы купили VIP за 20 Stars.")
            elif product == "booster":
                purchases.setdefault(message.from_user.id, []).append("booster")
                await message.answer("✅ Отлично! 🚀 Вы купили Бустер за 10 Stars.")
            else:
                await message.answer("❌ Неизвестный товар.")
    except Exception as e:
        await message.answer(f"Ошибка при обработке покупки: {e}")

# ==============================
# АДМИН-КОМАНДА
# ==============================
@dp.message(F.text.startswith('/add_ton'))
async def add_ton_to_balance(message: types.Message):
    if message.from_user.id != MY_ID:
        await message.answer("❌ У вас нет прав для этой команды.")
        return
    try:
        args = message.text.split()
        amount = float(args[1])
        user_id = int(args[2])
        balances.setdefault(user_id, 0.0)
        balances[user_id] += amount
        await message.answer(f"✅ Баланс пользователя {user_id} пополнен на {amount} TON.")
        await bot.send_message(user_id, f"🎉 Ваш баланс пополнен на {amount} TON!")
    except Exception:
        await message.answer("❌ Неверный формат. Используйте: /add_ton <сумма> <ID>")

# ==============================
# MAIN
# ==============================
async def main():
    await start_webserver()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
