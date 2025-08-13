import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder
import asyncio

TOKEN = os.getenv("BOT_TOKEN")  # токен берем из переменной среды
BOT_USERNAME = "CryptoWorkBot"  # твой username бота без @

bot = Bot(token=TOKEN)
dp = Dispatcher()


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
    user_id = message.from_user.id
    referral_link = f"https://t.me/{BOT_USERNAME}?start={user_id}"
    await message.answer(
        f"👋 Привет, {message.from_user.first_name}!\n\n"
        f"👥 Приглашай друзей и получай 0.1 TON за каждого!\n\n"
        f"🔗 Твоя ссылка:\n{referral_link}",
        reply_markup=main_menu()
    )


# Обработчики кнопок
@dp.callback_query(F.data == "balance")
async def balance_callback(callback: types.CallbackQuery):
    await callback.message.answer("💰 Ваш баланс: 0 TON")
    await callback.answer()

@dp.callback_query(F.data == "tasks")
async def tasks_callback(callback: types.CallbackQuery):
    await callback.message.answer("📋 Задания пока отсутствуют")
    await callback.answer()

@dp.callback_query(F.data == "invite")
async def invite_callback(callback: types.CallbackQuery):
    referral_link = f"https://t.me/{BOT_USERNAME}?start={callback.from_user.id}"
    await callback.message.answer(
        f"👥 Приглашай друзей и получай 0.1 TON за каждого!\n\n"
        f"🔗 Ваша ссылка:\n{referral_link}"
    )
    await callback.answer()

@dp.callback_query(F.data == "withdraw")
async def withdraw_callback(callback: types.CallbackQuery):
    await callback.message.answer("💸 Вывод временно недоступен")
    await callback.answer()


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
