import os
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiohttp import web  # HTTP-сервер для Render

TOKEN = os.getenv("BOT_TOKEN")
BOT_USERNAME = "MenqenqmersareryBot"

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Данные в памяти
balances = {}
referrals = {}
tasks = [
    {"id": 1, "title": "Подпишись на канал 📢", "link": "https://t.me/example_channel", "reward": 0.2},
    {"id": 2, "title": "Посмотри пост 📰", "link": "https://t.me/example_channel/1", "reward": 0.1}
]

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

    # Рефералка
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

# Баланс
@dp.callback_query(F.data == "balance")
async def balance_callback(callback: types.CallbackQuery):
    bal = balances.get(callback.from_user.id, 0.0)
    await callback.message.answer(f"💰 Ваш баланс: {bal:.2f} TON")
    await callback.answer()

# Задания
@dp.callback_query(F.data == "tasks")
async def tasks_callback(callback: types.CallbackQuery):
    kb = InlineKeyboardBuilder()
    for task in tasks:
        kb.button(text=f"{task['title']} (+{task['reward']} TON)", callback_data=f"task_{task['id']}")
    kb.adjust(1)
    await callback.message.answer("📋 Доступные задания:", reply_markup=kb.as_markup())
    await callback.answer()

# Выполнение задания
@dp.callback_query(F.data.startswith("task_"))
async def do_task_callback(callback: types.CallbackQuery):
    task_id = int(callback.data.split("_")[1])
    task = next((t for t in tasks if t["id"] == task_id), None)
    if not task:
        await callback.answer("Задание не найдено", show_alert=True)
        return

    balances[callback.from_user.id] = balances.get(callback.from_user.id, 0.0) + task["reward"]
    await callback.message.answer(f"✅ Задание выполнено! Вы получили {task['reward']} TON\n"
                                  f"🔗 {task['link']}")
    await callback.answer()

# Приглашения
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

# Вывод
@dp.callback_query(F.data == "withdraw")
async def withdraw_callback(callback: types.CallbackQuery):
    await callback.message.answer("💸 Вывод временно недоступен")
    await callback.answer()

# HTTP-сервер для Render
async def handle(request):
    return web.Response(text="Bot is running!")

async def start_webserver():
    app = web.Application()
    app.router.add_get("/", handle)
    port = int(os.getenv("PORT", 10000))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

async def main():
    await start_webserver()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
