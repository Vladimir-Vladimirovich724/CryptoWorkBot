import logging
import json
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    WebAppInfo
)
import asyncio
import os

# Логирование
logging.basicConfig(level=logging.INFO)

# Токен из Render (Environment Variables)
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN не найден в переменных окружения Render!")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Простая "база"
users = {}
purchases = {}

# ---------- КНОПКИ ----------
main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="💰 Баланс"), KeyboardButton(text="👥 Рефералы")],
        [KeyboardButton(text="🛒 Магазин", web_app=WebAppInfo(url="https://cryptoworkbot-shop.onrender.com"))]
    ],
    resize_keyboard=True
)

# ---------- СТАРТ ----------
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    if user_id not in users:
        users[user_id] = {"balance": 0, "refs": []}
    await message.answer(
        "👋 Добро пожаловать в *CryptoWorkBot*!\n\n"
        "Зарабатывай и трать ⭐️ Stars.",
        reply_markup=main_kb,
        parse_mode="Markdown"
    )

# ---------- БАЛАНС ----------
@dp.message(F.text == "💰 Баланс")
async def check_balance(message: types.Message):
    user_id = message.from_user.id
    balance = users.get(user_id, {}).get("balance", 0)
    await message.answer(f"💰 Ваш баланс: {balance} Stars")

# ---------- РЕФЕРАЛЫ ----------
@dp.message(F.text == "👥 Рефералы")
async def check_refs(message: types.Message):
    user_id = message.from_user.id
    refs = users.get(user_id, {}).get("refs", [])
    await message.answer(
        f"👥 У вас {len(refs)} рефералов.\n"
        f"🔗 Ваша ссылка: https://t.me/{(await bot.get_me()).username}?start={user_id}"
    )

# ---------- МАГАЗИН ----------
@dp.message(F.text == "🛒 Магазин")
async def open_shop(message: types.Message):
    await message.answer(
        "🛒 Открывай магазин и покупай товары за ⭐ Stars!",
        reply_markup=main_kb
    )

# ---------- ОБРАБОТЧИК WebApp ----------
@dp.message(F.web_app_data)
async def handle_web_app_data(message: types.Message):
    try:
        data = json.loads(message.web_app_data.data)
        logging.info(f"📩 Получены данные из WebApp: {data}")

        if data.get("action") == "buy":
            product = data.get("product")
            user_id = message.from_user.id

            if product == "vip":
                purchases.setdefault(user_id, []).append("vip")
                await message.answer("✅ Поздравляем
