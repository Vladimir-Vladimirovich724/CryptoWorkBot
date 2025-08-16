import os
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import WebAppInfo

# ==============================
# НАСТРОЙКИ
# ==============================
TOKEN = os.getenv("BOT_TOKEN")  # токен из Render
BOT_USERNAME = "MenqenqmersareryBot"

bot = Bot(token=TOKEN)
dp = Dispatcher()

balances = {}
referrals = {}
purchases = {}

# URL вашего мини-приложения
MINI_APP_URL = "https://cryptoworkbot-shop.onrender.com"

# ==============================
# ВЕБ-СЕРВЕР ДЛЯ RENDER
# ==============================
async def handle(request):
    return web.Response(text="✅ Bot is running!")

async def start_webserver():
    app = web.Application()
    app.router.add_get("/", handle)
    port = int(os.getenv("PORT", 10000))  # Render требует PORT
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
    
    # Новая кнопка, которая будет открывать мини-приложение
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
        inviter_id = int(args[1])
        if inviter_id != user_id and user_id not in referrals.get(inviter_id, []):
            referrals[inviter_id].append(user_id)
            balances[inviter_id] += 0.1

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
        f"👥 Приглашай друзей и получай 0.1 TON за каждого!\n\n"
        f"🔗 Ваша ссылка:\n{referral_link}\n\n"
        f"Вы пригласили: {count} чел."
    )
    await callback.answer()


@dp.callback_query(F.data == "withdraw")
async def withdraw_callback(callback: types.CallbackQuery):
    await callback.message.answer("💸 Вывод временно недоступен")
    await callback.answer()


# ==============================
# ОБРАБОТКА ПЛАТЕЖЕЙ
# ==============================
@dp.message(F.content_type == "successful_payment")
async def successful_payment(message: types.Message):
    payment = message.successful_payment
    user_id = message.from_user.id

    if payment.invoice_payload == "booster_1":
        purchases[user_id].append("booster")
        await message.answer("✅ Покупка успешна! 🚀 Доход увеличен x1.5")

    elif payment.invoice_payload == "vip_1":
        purchases[user_id].append("vip")
        await message.answer("✅ Поздравляем! 🌟 Вы получили VIP-доступ")


# ==============================
# MAIN
# ==============================
async def main():
    await start_webserver()   # фиктивный сервер для Render
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
