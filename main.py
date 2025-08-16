import os
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder

TOKEN = os.getenv("BOT_TOKEN")  # токен из Render
BOT_USERNAME = "MenqenqmersareryBot"

bot = Bot(token=TOKEN)
dp = Dispatcher()

balances = {}
referrals = {}
purchases = {}

# Главное меню
def main_menu():
    kb = InlineKeyboardBuilder()
    kb.button(text="💰 Баланс", callback_data="balance")
    kb.button(text="📋 Задания", callback_data="tasks")
    kb.button(text="👥 Приглашения", callback_data="invite")
    kb.button(text="🛒 Магазин", callback_data="shop")
    kb.button(text="💸 Вывод", callback_data="withdraw")
    kb.adjust(2)
    return kb.as_markup()


@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    user_id = message.from_user.id
    args = message.text.split()

    if user_id not in balances:
        balances[user_id] = 0.0
        referrals[user_id] = []
        purchases[user_id] = []

    # обработка рефералки
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


# Баланс
@dp.callback_query(F.data == "balance")
async def balance_callback(callback: types.CallbackQuery):
    bal = balances.get(callback.from_user.id, 0.0)
    await callback.message.answer(f"💰 Ваш баланс: {bal} TON")
    await callback.answer()


# Задания
@dp.callback_query(F.data == "tasks")
async def tasks_callback(callback: types.CallbackQuery):
    await callback.message.answer("📋 Задания пока отсутствуют")
    await callback.answer()


# Рефералы
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


# ------------------ МАГАЗИН ------------------
@dp.callback_query(F.data == "shop")
async def shop_callback(callback: types.CallbackQuery):
    kb = InlineKeyboardBuilder()
    kb.button(text="⚡ Бустер дохода (10⭐)", callback_data="buy_boost")
    kb.button(text="🌟 VIP-доступ (20⭐)", callback_data="buy_vip")
    kb.adjust(1)
    await callback.message.answer("🛒 Магазин\nВыберите товар:", reply_markup=kb.as_markup())
    await callback.answer()


# Покупка бустера
@dp.callback_query(F.data == "buy_boost")
async def buy_boost(callback: types.CallbackQuery):
    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title="⚡ Бустер дохода",
        description="Увеличивает доход на 50%",
        payload="booster_1",
        provider_token="",  # <-- здесь укажем provider_token из @BotFather
        currency="XTR",  # Telegram Stars валюта
        prices=[types.LabeledPrice(label="Бустер", amount=10 * 100)],  # 10⭐
    )
    await callback.answer()


# Покупка VIP
@dp.callback_query(F.data == "buy_vip")
async def buy_vip(callback: types.CallbackQuery):
    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title="🌟 VIP-доступ",
        description="Открывает VIP-функции в боте",
        payload="vip_1",
        provider_token="",  # <-- сюда provider_token
        currency="XTR",
        prices=[types.LabeledPrice(label="VIP-доступ", amount=20 * 100)],  # 20⭐
    )
    await callback.answer()


# Подтверждение платежа
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


# ---------------------------------------------

async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
