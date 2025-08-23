import os
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher, Router, types
from aiogram.filters import CommandStart
from aiogram.types import BotCommand
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # пример: https://cryptoworkbot.onrender.com/webhook
WEBHOOK_PATH = "/webhook"
WEB_SERVER_HOST = "0.0.0.0"
WEB_SERVER_PORT = int(os.getenv("PORT", 8080))

if not BOT_TOKEN or not WEBHOOK_URL:
    raise RuntimeError("❌ Нет переменных окружения BOT_TOKEN или WEBHOOK_URL")

logging.basicConfig(level=logging.INFO)

router = Router()

@router.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer("✅ Бот работает! Render ↔ Telegram соединены.")

async def on_startup(dispatcher: Dispatcher, bot: Bot):
    await bot.set_webhook(f"{WEBHOOK_URL}{WEBHOOK_PATH}", drop_pending_updates=True)
    await bot.set_my_commands([
        BotCommand(command="start", description="Проверить бота"),
    ])
    logging.info("Webhook установлен ✅")

async def on_shutdown(dispatcher: Dispatcher, bot: Bot):
    await bot.delete_webhook()
    logging.info("Webhook удалён ❌")

def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)

    app = web.Application()
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)

    app.on_startup.append(lambda app, bot=bot: on_startup(dp, bot))
    app.on_shutdown.append(lambda app, bot=bot: on_shutdown(dp, bot))

    web.run_app(app, host=WEB_SERVER_HOST, port=WEB_SERVER_PORT)

if __name__ == "__main__":
    main()
