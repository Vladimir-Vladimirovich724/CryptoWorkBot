import os
import asyncio
import json
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import WebAppInfo

# ==============================
# НАСТРОЙКИ. ИСПОЛЬЗУЙТЕ ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ
# ==============================
# Получаем токен бота из переменных окружения Render
TOKEN = os.getenv("BOT_TOKEN")  

# Установите эти переменные окружения на вашей платформе (например, в Render)
BOT_USERNAME = os.getenv("BOT_USERNAME", "MenqenqmersareryBot")
MY_ID = int(os.getenv("MY_ID", "7352855554")) 
MINI_APP_URL = os.getenv("MINI_APP_URL", "https://cryptoworkbot-shop.onrender.com")

# Цены товаров и процент для рефералов
PRODUCT_PRICES = {
    "vip": 20.0,
    "booster": 10.0,
}
REFERRAL_PERCENT = 0.05

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Имя файла для хранения данных
DB_FILE = "data.json"

# ==============================
# ФУНКЦИИ ДЛЯ РАБОТЫ С БАЗОЙ ДАННЫХ (JSON)
# ==============================
def load_data():
    """Загружает данные из JSON файла."""
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return json.load(f)
    return {
        "balances": {},
        "referrals": {},
        "purchases": {},
    }

def save_data(data):
    """Сохраняет данные в JSON файл."""
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

# ==============================
# ВЕБ-СЕРВЕР ДЛЯ RENDER
# ==============================
async def handle(request):
    """Обработчик для корневого URL, чтобы Render знал, что бот работает."""
    return web.Response(text="✅ Bot is running!")

async def start_webserver():
    """Запускает простой веб-сервер."""
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
    """Создает и возвращает разметку главного меню."""
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
    """
    Обрабатывает команду /start.
    Регистрирует нового пользователя и обрабатывает реферальные ссылки.
    """
    user_id = str(message.from_user.id)
    args = message.text.split()
    
    data = load_data()

    if user_id not in data["balances"]:
        data["balances"][user_id] = 0.0
        data["referrals"][user_id] = []
        data["purchases"][user_id] = []

    # Обработка реферальной ссылки
    if len(args) > 1:
        try:
            inviter_id = str(int(args[1]))
            # Проверяем, что пригласитель существует и пользователь не пригласил сам себя
            if inviter_id != user_id and user_id not in data["referrals"].get(inviter_id, []):
                data["referrals"].setdefault(inviter_id, []).append(user_id)
        except (ValueError, TypeError):
            # Игнорируем некорректные ID в ссылке
            pass
    
    save_data(data)

    await message.answer(
        f"👋 Привет, {message.from_user.first_name}!\n"
        f"Добро пожаловать в CryptoWorkBot 💼\n\n"
        f"Выполняй задания, приглашай друзей и зарабатывай TON!",
        reply_markup=main_menu()
    )

# ==============================
# ОБРАБОТЧИКИ КНОПОК МЕНЮ
# ==============================
@dp.callback_query(F.data == "balance")
async def balance_callback(callback: types.CallbackQuery):
    """Отображает текущий баланс пользователя."""
    data = load_data()
    user_id = str(callback.from_user.id)
    bal = data["balances"].get(user_id, 0.0)
    await callback.message.answer(f"💰 Ваш баланс: {bal} TON")
    await callback.answer()

@dp.callback_query(F.data == "tasks")
async def tasks_callback(callback: types.CallbackQuery):
    """Сообщение о заданиях."""
    await callback.message.answer("📋 Задания пока отсутствуют")
    await callback.answer()

@dp.callback_query(F.data == "invite")
async def invite_callback(callback: types.CallbackQuery):
    """Отображает реферальную ссылку и количество приглашенных."""
    user_id = str(callback.from_user.id)
    referral_link = f"https://t.me/{BOT_USERNAME}?start={user_id}"
    data = load_data()
    count = len(data["referrals"].get(user_id, []))
    await callback.message.answer(
        f"👥 Приглашай друзей и получай {REFERRAL_PERCENT*100}% от их покупок!\n\n"
        f"🔗 Ваша ссылка:\n{referral_link}\n\n"
        f"Вы пригласили: {count} чел."
    )
    await callback.answer()

@dp.callback_query(F.data == "withdraw")
async def withdraw_callback(callback: types.CallbackQuery):
    """Сообщение о выводе средств."""
    await callback.message.answer("💸 Вывод временно недоступен")
    await callback.answer()

# ==============================
# ПОЛУЧЕНИЕ ДАННЫХ ИЗ WEBAPP И ОБРАБОТКА ПОКУПКИ
# ==============================
@dp.message(F.web_app_data)
async def handle_web_app_data(message: types.Message):
    """Обрабатывает данные, полученные от веб-приложения."""
    user_id = str(message.from_user.id)
    try:
        data = json.loads(message.web_app_data.data)
        if data["action"] == "buy":
            product = data["product"]
            price = PRODUCT_PRICES.get(product)
            
            if not price:
                await message.answer("❌ Неизвестный товар.")
                return

            db_data = load_data()
            user_balance = db_data["balances"].get(user_id, 0.0)

            # Проверяем, достаточно ли средств
            if user_balance >= price:
                db_data["balances"][user_id] -= price
                db_data["purchases"].setdefault(user_id, []).append(product)
                
                # Начисление реферальных бонусов
                for inviter_id, invited_users in db_data["referrals"].items():
                    if user_id in invited_users:
                        referral_bonus = price * REFERRAL_PERCENT
                        db_data["balances"].setdefault(inviter_id, 0.0)
                        db_data["balances"][inviter_id] += referral_bonus
                        await bot.send_message(
                            int(inviter_id),
                            f"🎉 Ваш реферал купил {product}! Вы получили {referral_bonus} TON."
                        )
                
                save_data(db_data)
                await message.answer(f"✅ Поздравляем! Вы купили {product} за {price} Stars.")
            else:
                await message.answer("❌ Недостаточно средств.")
                
    except (json.JSONDecodeError, KeyError) as e:
        await message.answer(f"❌ Ошибка при обработке покупки: неверный формат данных.")
    except Exception as e:
        await message.answer(f"❌ Непредвиденная ошибка: {e}")

# ==============================
# АДМИН-КОМАНДА ДЛЯ ПОПОЛНЕНИЯ БАЛАНСА
# ==============================
@dp.message(F.text.startswith('/add_ton'))
async def add_ton_to_balance(message: types.Message):
    """Позволяет администратору пополнить баланс пользователя."""
    if message.from_user.id != MY_ID:
        await message.answer("❌ У вас нет прав для этой команды.")
        return
    try:
        args = message.text.split()
        amount = float(args[1])
        user_id = str(int(args[2]))
        
        db_data = load_data()
        db_data["balances"].setdefault(user_id, 0.0)
        db_data["balances"][user_id] += amount
        save_data(db_data)
        
        await message.answer(f"✅ Баланс пользователя {user_id} пополнен на {amount} TON.")
        await bot.send_message(int(user_id), f"🎉 Ваш баланс пополнен на {amount} TON!")
    except (ValueError, IndexError):
        await message.answer("❌ Неверный формат. Используйте: /add_ton <сумма> <ID>")

# ==============================
# MAIN
# ==============================
async def main():
    """Главная функция для запуска бота и веб-сервера."""
    await start_webserver()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
