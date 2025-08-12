import asyncio
import sqlite3
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.client.default import DefaultBotProperties

# --- Конфигурация ---
BOT_TOKEN = os.getenv("BOT_TOKEN")  # токен берём из переменной окружения
ADMIN_USERNAME = "@Ferdinantik_ot777"
TON_WALLET = "UQAndbKgGhUtqSlXCA8pL_aCq0xwxtf4HVyREfwUkgCs047M"
DB_PATH = "crypto_users.db"

# --- Инициализация бота ---
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# --- Инициализация базы данных ---
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            referrer INTEGER,
            balance REAL DEFAULT 0.0,
            ton_wallet TEXT
        )''')
        conn.commit()

# --- Команда /start ---
@dp.message(F.text.startswith("/start"))
async def start_handler(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or "Без ника"
    args = message.text.split()
    referrer = int(args[1]) if len(args) > 1 and args[1].isdigit() else None

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE id = ?", (user_id,))
        if not cursor.fetchone():
            cursor.execute("INSERT INTO users (id, username, referrer) VALUES (?, ?, ?)", (user_id, username, referrer))
            if referrer:
                cursor.execute("UPDATE users SET balance = balance + 0.1 WHERE id = ?", (referrer,))
            conn.commit()

    kb = InlineKeyboardBuilder()
    kb.button(text="💰 Баланс", callback_data="balance")
    kb.button(text="📝 Задания", callback_data="tasks")
    kb.button(text="👥 Пригласить", callback_data="ref")
    kb.button(text="💸 Вывод", callback_data="withdraw")

    await message.answer(
        f"Привет, <b>{username}</b>! Добро пожаловать в <b>CryptoWorkBot</b> 💼\n\n"
        "Выполняй задания и зарабатывай <b>TON</b>!\n",
        reply_markup=kb.as_markup()
    )

# --- Показ баланса ---
@dp.callback_query(F.data == "balance")
async def balance_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT balance FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        balance = result[0] if result else 0.0
    await callback.message.edit_text(f"💰 Ваш баланс: <b>{balance:.2f} TON</b>")

# --- Показ реферальной ссылки ---
@dp.callback_query(F.data == "ref")
async def ref_callback(callback: types.CallbackQuery):
    uid = callback.from_user.id
    link = f"https://t.me/CryptoWorkBot?start={uid}"
    await callback.message.edit_text(f"👥 Приглашай друзей и получай <b>0.1 TON</b> за каждого!\n\n🔗 Твоя ссылка:\n<code>{link}</code>")

# --- Вывод средств ---
@dp.callback_query(F.data == "withdraw")
async def withdraw_callback(callback: types.CallbackQuery):
    await callback.message.edit_text(f"🚫 Вывод пока доступен только через администратора.\nСвяжитесь с ним: {ADMIN_USERNAME}")

# --- Показ заданий ---
@dp.callback_query(F.data == "tasks")
async def tasks_callback(callback: types.CallbackQuery):
    await callback.message.edit_text("📋 Сейчас нет доступных заданий.\nСледите за обновлениями!")

# --- Запуск бота ---
async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
