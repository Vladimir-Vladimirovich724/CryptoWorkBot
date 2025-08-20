import os
import json
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import WebAppInfo
from aiogram.enums import ParseMode
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

# ==============================
# КОНФИГУРАЦИЯ БОТА И ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ
# ==============================
# Получаем переменные окружения из Render
TOKEN = os.getenv("BOT_TOKEN")
BOT_USERNAME = os.getenv("BOT_USERNAME")
MY_ID = int(os.getenv("MY_ID"))
MINI_APP_URL = os.getenv("MINI_APP_URL")

# Проверяем, загружены ли все переменные
if not all([TOKEN, BOT_USERNAME, MY_ID, MINI_APP_URL]):
    print("❌ ОШИБКА: Не все переменные окружения загружены! Проверьте настройки Render.")
    exit(1) # Завершаем выполнение, если переменные не найдены

# Инициализируем бота с использованием старого синтаксиса для совместимости
bot = Bot(token=TOKEN, parse_mode=ParseMode.MARKDOWN_V2)
dp = Dispatcher()

# Цены товаров и процент для рефералов
PRODUCT_PRICES = {
    "vip": 20.0,
    "booster": 10.0,
}
REFERRAL_PERCENT = 0.05

# Имя файла для хранения данных
DB_FILE = "data.json"

# ==============================
# ФУНКЦИИ ДЛЯ РАБОТЫ С БАЗОЙ ДАННЫХ (JSON)
# ==============================
def load_data():
    """Загружает данные из JSON файла."""
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                print("❌ ОШИБКА: Файл data.json поврежден. Создание нового файла.")
                return {"balances": {}, "referrals": {}, "purchases": {}}
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
# ГЛАВНОЕ МЕНЮ
# ==============================
def main_menu():
    """Создает и возвращает разметку главного меню."""
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(text="💰 Баланс", callback_data="balance"),
            types.InlineKeyboardButton(text="📋 Задания", callback_data="tasks")
        ],
        [
            types.InlineKeyboardButton(text="👥 Приглашения", callback_data="invite"),
            types.InlineKeyboardButton(text="🛒 Магазин", web_app=WebAppInfo(url=MINI_APP_URL))
        ],
        [
            types.InlineKeyboardButton(text="💸 Вывод", callback_data="withdraw")
        ]
    ])

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

    if len(args) > 1:
        try:
            inviter_id = str(int(args[1]))
            if inviter_id != user_id and user_id not in data["referrals"].get(inviter_id, []):
                data["referrals"].setdefault(inviter_id, []).append(user_id)
        except (ValueError, TypeError):
            pass
    
    save_data(data)

    await message.answer(
        f"👋 Привет, {message.from_user.first_name}!\\n"
        f"Добро пожаловать в CryptoWorkBot 💼\\n\\n"
        f"Ваш баланс: **{data['balances'].get(user_id, 0)} Stars** ✨\\n\\n"
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
    await callback.answer(f"💰 Ваш баланс: {bal} TON", show_alert=True)

@dp.callback_query(F.data == "tasks")
async def tasks_callback(callback: types.CallbackQuery):
    """Сообщение о заданиях."""
    await callback.answer("📋 Задания пока отсутствуют", show_alert=True)

@dp.callback_query(F.data == "invite")
async def invite_callback(callback: types.CallbackQuery):
    """Отображает реферальную ссылку и количество приглашенных."""
    user_id = str(callback.from_user.id)
    referral_link = f"https://t.me/{BOT_USERNAME}?start={user_id}"
    data = load_data()
    count = len(data["referrals"].get(user_id, []))
    await callback.message.answer(
        f"👥 Приглашай друзей и получай {REFERRAL_PERCENT*100}% от их покупок!\\n\\n"
        f"🔗 Ваша ссылка:\\n{referral_link}\\n\\n"
        f"Вы пригласили: {count} чел."
    )
    await callback.answer()

@dp.callback_query(F.data == "withdraw")
async def withdraw_callback(callback: types.CallbackQuery):
    """Сообщение о выводе средств."""
    await callback.answer("💸 Вывод временно недоступен", show_alert=True)

# ==============================
# ПОЛУЧЕНИЕ ДАННЫХ ИЗ WEBAPP И ОБРАБОТКА ПОКУПКИ
# ==============================
@dp.message(F.web_app_data)
async def handle_web_app_data(message: types.Message):
    """Обрабатывает данные, полученные от веб-приложения."""
    user_id = str(message.from_user.id)
    db_data = load_data()
    
    print(f"Получены данные от веб-приложения: {message.web_app_data.data}")

    try:
        data_from_app = json.loads(message.web_app_data.data)
        
        if data_from_app["action"] == "buy":
            product = data_from_app["product"]
            price = PRODUCT_PRICES.get(product)
            
            if not price:
                await message.answer("❌ Неизвестный товар.")
                return

            user_balance = db_data["balances"].get(user_id, 0.0)

            if user_balance >= price:
                db_data["balances"][user_id] -= price
                db_data["purchases"].setdefault(user_id, []).append(product)
                
                for inviter_id, invited_users in db_data["referrals"].items():
                    if user_id in invited_users:
                        referral_bonus = price * REFERRAL_PERCENT
                        db_data["balances"].setdefault(inviter_id, 0.0)
                        db_data["balances"][inviter_id] += referral_bonus
                        try:
                            await bot.send_message(
                                int(inviter_id),
                                f"🎉 Ваш реферал купил {product}! Вы получили {referral_bonus} TON."
                            )
                        except Exception as e:
                            print(f"Не удалось отправить сообщение рефералу {inviter_id}: {e}")

                await message.answer(f"✅ Поздравляем! Вы купили {product} за {price} Stars.\\n"
                                     f"Ваш новый баланс: {db_data['balances'][user_id]} Stars ✨")
            else:
                await message.answer(f"❌ Недостаточно средств для покупки {product}.\\n"
                                     f"Ваш баланс: {user_balance} Stars. Требуется: {price} Stars.")
    except (json.JSONDecodeError, KeyError) as e:
        await message.answer(f"❌ Ошибка при обработке покупки: неверный формат данных.")
        print(f"ОШИБКА: Неверный JSON или ключ в web_app_data: {e}")
    except Exception as e:
        await message.answer(f"❌ Непредвиденная ошибка: {e}")
        print(f"ОШИБКА: Непредвиденное исключение в обработчике web_app_data: {e}")
    finally:
        save_data(db_data)

# ==============================
# АДМИН-КОМАНДА ДЛЯ ПОПОЛНЕНИЯ БАЛАНСА
# ==============================
@dp.message(Command("add_ton"))
async def add_ton_to_balance(message: types.Message):
    """Позволяет администратору пополнить баланс пользователя."""
    if message.from_user.id != MY_ID:
        await message.answer("❌ У вас нет прав для этой команды.")
        return
    try:
        args = message.text.split()
        if len(args) != 3:
            raise ValueError
        
        target_user_id = str(int(args[1]))
        amount = float(args[2])
        
        db_data = load_data()
        db_data["balances"].setdefault(target_user_id, 0.0)
        db_data["balances"][target_user_id] += amount
        save_data(db_data)
        
        await message.answer(f"✅ Баланс пользователя {target_user_id} пополнен на {amount} TON.")
        try:
            await bot.send_message(int(target_user_id), f"🎉 Ваш баланс пополнен на {amount} TON!")
        except Exception as e:
            print(f"Не удалось отправить сообщение пользователю {target_user_id}: {e}")
    except (ValueError, IndexError):
        await message.answer("❌ Неверный формат. Используйте: /add_ton <ID пользователя> <сумма>")


# ==============================
# ГЛАВНАЯ ФУНКЦИЯ ДЛЯ ЗАПУСКА
# ==============================
async def main():
    """
    Главная функция для запуска бота с использованием Webhook.
    """
    # Получаем URL и порт, предоставленные Render
    render_url = os.getenv("RENDER_EXTERNAL_URL")
    if not render_url:
        print("❌ ОШИБКА: Не удалось получить RENDER_EXTERNAL_URL. Запуск Webhook невозможен.")
        return
        
    port = int(os.environ.get("PORT", 8000))
    webhook_url = f"{render_url}webhook"

    print(f"Используемый Webhook URL: {webhook_url}")
    
    try:
        # Сначала пытаемся удалить старый вебхук, чтобы избежать конфликта
        print("Попытка удалить старый Webhook...")
        await bot.delete_webhook()
        print("✅ Старый Webhook успешно удален.")
    except Exception as e:
        print(f"ℹ️ Не удалось удалить старый Webhook: {e}")

    try:
        print(f"Установка нового Webhook...")
        await bot.set_webhook(webhook_url)
        print("✅ Новый Webhook успешно установлен.")
    except Exception as e:
        print(f"❌ ОШИБКА: Не удалось установить Webhook. {e}")
        return

    # Создаем веб-приложение aiohttp для обработки Webhook
    app = web.Application()
    webhook_requests_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot
    )
    webhook_requests_handler.register(app, "/webhook")
    
    # Запускаем веб-сервер
    setup_application(app, dp, bot=bot)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    print(f"Бот запущен на порту {port}")
    await site.start()

if __name__ == "__main__":
    asyncio.run(main())
