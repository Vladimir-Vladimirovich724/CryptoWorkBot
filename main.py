import os
import json
import asyncio
from aiogram import Bot, Dispatcher, types, F # Я добавил F сюда!
from aiogram.filters import CommandStart, Command
from aiogram.types import WebAppInfo

# ==============================
# КОНФИГУРАЦИЯ БОТА И ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ
# ==============================
# Получаем переменные окружения, которые вы настроили на Render
BOT_TOKEN = os.getenv("BOT_TOKEN")
BOT_USERNAME = os.getenv("BOT_USERNAME")
MY_ID = int(os.getenv("MY_ID"))
MINI_APP_URL = os.getenv("MINI_APP_URL")

# Проверяем, что все переменные загружены
if not all([BOT_TOKEN, BOT_USERNAME, MY_ID, MINI_APP_URL]):
    print("❌ ERROR: Не все переменные окружения загружены!")
    # Можно добавить sys.exit(1), чтобы остановить приложение, если переменные не найдены
    # import sys; sys.exit(1)

# Инициализируем бота и диспетчер
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Словарь цен на товары (в Stars)
PRODUCT_PRICES = {
    "vip": 20,
    "booster": 10,
}

# Словарь для хранения баланса пользователей (пример, для базы данных нужен другой подход)
user_balances = {
    MY_ID: 1000  # Ваш ID для тестирования
}

# ==============================
# ОБРАБОТЧИКИ КОМАНД
# ==============================
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    """
    Обработчик команды /start.
    Приветствует пользователя и предлагает перейти в магазин.
    """
    user_id = message.from_user.id
    if user_id not in user_balances:
        user_balances[user_id] = 0 # Инициализируем баланс нового пользователя
    
    markup = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="🛍️ Магазин", web_app=WebAppInfo(url=MINI_APP_URL))]
    ])
    await message.answer(
        f"Привет! 👋 Я бот CryptoWorkBot.\n\n"
        f"Твой баланс: **{user_balances.get(user_id, 0)} Stars** ✨\n\n"
        f"Чтобы купить VIP-статус или Бустер, перейди в магазин по кнопке ниже.",
        reply_markup=markup,
        parse_mode="Markdown"
    )

@dp.message(Command("shop"))
async def cmd_shop(message: types.Message):
    """
    Обработчик команды /shop.
    Также открывает магазин.
    """
    markup = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="🛍️ Открыть магазин", web_app=WebAppInfo(url=MINI_APP_URL))]
    ])
    await message.answer(
        "Нажмите кнопку ниже, чтобы открыть магазин:",
        reply_markup=markup
    )

@dp.message(Command("add_ton"))
async def cmd_add_ton(message: types.Message):
    """
    Админ-команда для добавления Stars на баланс.
    Используется только для вас (админа).
    """
    if message.from_user.id != MY_ID:
        await message.answer("❌ У вас нет прав для использования этой команды.")
        return

    try:
        args = message.text.split()
        if len(args) != 3:
            raise ValueError
        
        target_user_id = int(args[1])
        amount = int(args[2])
        
        if target_user_id not in user_balances:
            user_balances[target_user_id] = 0
            
        user_balances[target_user_id] += amount
        await message.answer(
            f"✅ Успешно! Добавлено {amount} Stars на баланс пользователя с ID {target_user_id}."
        )
    except (ValueError, IndexError):
        await message.answer(
            "❌ Ошибка в команде. Используйте формат: /add_ton <ID пользователя> <сумма>"
        )

# ==============================
# ПОЛУЧЕНИЕ ДАННЫХ ИЗ WEBAPP И ОБРАБОТКА ПОКУПКИ
# ==============================
@dp.message(F.web_app_data)
async def handle_web_app_data(message: types.Message):
    """Обрабатывает данные, полученные от веб-приложения."""
    user_id = str(message.from_user.id)
    
    # Отладочное сообщение для проверки, что данные дошли до бота
    print(f"Получены данные от webapp: {message.web_app_data.data}")

    try:
        data = json.loads(message.web_app_data.data)
        
        if data["action"] == "buy":
            product = data["product"]
            
            # Проверяем, существует ли такой товар
            price = PRODUCT_PRICES.get(product)
            if price is None:
                await message.answer(f"❌ Неизвестный товар: {product}")
                return

            # Проверяем баланс пользователя
            current_balance = user_balances.get(message.from_user.id, 0)
            if current_balance >= price:
                user_balances[message.from_user.id] -= price
                await message.answer(f"🎉 Вы успешно купили **{product.upper()}** за {price} Stars!\n"
                                     f"Ваш новый баланс: {user_balances[message.from_user.id]} Stars ✨")
            else:
                await message.answer(f"❌ Недостаточно средств для покупки **{product.upper()}**.\n"
                                     f"Ваш баланс: {current_balance} Stars. Требуется: {price} Stars.")
    except (json.JSONDecodeError, KeyError) as e:
        await message.answer(f"❌ Ошибка при обработке данных из веб-приложения: неверный формат.")
        print(f"ERROR: Invalid JSON or key in web_app_data: {e}")
    except Exception as e:
        await message.answer(f"❌ Непредвиденная ошибка: {e}")
        print(f"ERROR: Unhandled exception in web_app_data handler: {e}")

# ==============================
# ГЛАВНАЯ ФУНКЦИЯ ДЛЯ ЗАПУСКА БОТА
# ==============================
async def main():
    """
    Основная функция для запуска бота.
    """
    print("Бот запускается...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
