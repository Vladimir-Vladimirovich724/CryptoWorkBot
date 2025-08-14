import os
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiohttp import web

TOKEN = os.getenv("BOT_TOKEN")  # токен из переменных среды Render
BOT_USERNAME = "MenqenqmersareryBot"  # username бота без @

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Простая "база данных" в памяти
balances = {}
referrals = {}

# Главное меню
def main_menu():
    kb = InlineKeyboardBuilder()
    kb.button(text="💰 Баланс", callback_data="balance")
    kb.button(text="📋 Задания", callback_data="tasks")
    kb.button(text="👥 Приглашения", callback_data="invite")
    kb.button(text="💸 Вывод", callback_data="withdraw")
    kb.adjust(2)
    return kb.as_markup()


@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    args = message.text.split()
    user_id = message.from_user.id

    if user_id not in balances:
        balances[user_id] = 0.0
        referrals[user_id] = []

    # Обработка рефералки
    if len(args) > 1:
        inviter_id = int(args[1])
        if inviter_id != user_id and user_id not in referrals.get(inviter_id, []):
            referrals[inviter_id].append(user_id)
            balances[inviter_id] += 0.1

    await message.answer(
        f"👋 Привет, {message.from_user.first_name}!\n"
        f"Добро пожаловать в CryptoWorkBot 💼\n\n"
        f"Выполняй задания и зарабатывай TON!",
        reply_markup=main_menu()
    )


# Обработчики кнопок
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


# ====== AIOHTTP СЕРВЕР ДЛЯ РЕНДЕР ======
async def handle(request):
    return web.Response(text="Bot is running!")

async def start_web_app():
    app = web.Application()
    app.router.add_get("/", handle)
    port = int(os.environ.get("PORT", 10000))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"Web server started on port {port}")


async def main():
    await start_web_app()  # запуск HTTP сервера
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
