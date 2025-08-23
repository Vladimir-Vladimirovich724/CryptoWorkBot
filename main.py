import asyncio
import logging
import os
import json
import io
import wave
import base64
import aiohttp
from aiohttp import web

from aiogram import Bot, Dispatcher, Router, types
from aiogram.enums import ParseMode
from aiogram.types import BotCommand, BufferedInputFile
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.client.bot import DefaultBotProperties
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

# =========================
# Конфигурация и переменные окружения
# =========================
# Мы будем брать переменные из окружения, которые нужно будет настроить на хостинге.
# Сделаем проверку более надежной, чтобы избежать ошибок.
BOT_TOKEN = os.getenv("BOT_TOKEN")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
WEB_SERVER_HOST = os.getenv("WEB_SERVER_HOST", "0.0.0.0")
WEB_SERVER_PORT = int(os.getenv("PORT", 8080))
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "/webhook")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# Проверяем, что все переменные окружения установлены.
if not all([BOT_TOKEN, GOOGLE_API_KEY, WEBHOOK_URL]):
    logging.error("Не удалось найти переменные окружения BOT_TOKEN, GOOGLE_API_KEY и WEBHOOK_URL.")
    raise RuntimeError("Не удалось найти все необходимые переменные окружения.")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

router = Router()

# =========================
# Состояния FSM для TTS
# =========================
class TTSStates(StatesGroup):
    waiting_for_text = State()

# =========================
# Хендлеры
# =========================
@router.message(CommandStart())
async def cmd_start(message: types.Message):
    """
    Handles the /start command.
    Обрабатывает команду /start.
    """
    await message.answer("👋 Привет! Я готов к работе. Используйте /help для списка команд.")

@router.message(Command("help"))
async def cmd_help(message: types.Message):
    """
    Handles the /help command.
    Обрабатывает команду /help.
    """
    commands_list = (
        "Список доступных команд:\n"
        "/speak - Превратить текст в голос\n"
    )
    await message.answer(commands_list)

@router.message(Command("speak"))
async def cmd_speak(message: types.Message, state: FSMContext):
    """
    Starts the text-to-speech process.
    Начинает процесс преобразования текста в голос.
    """
    await message.answer("Пожалуйста, отправьте текст, который нужно озвучить.")
    await state.set_state(TTSStates.waiting_for_text)

@router.message(TTSStates.waiting_for_text)
async def process_tts_text(message: types.Message, state: FSMContext):
    """
    Receives text from the user and sends a request to the Gemini API for TTS.
    Получает текст от пользователя и отправляет запрос к Gemini API для TTS.
    """
    await state.clear()
    
    processing_msg = await message.answer("⏳ Генерирую аудио...")
    
    text_to_speak = message.text
    
    payload = {
        "contents": [
            { "parts": [ { "text": text_to_speak } ] }
        ],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": { "prebuiltVoiceConfig": { "voiceName": "Kore" } }
            }
        },
        "model": "gemini-2.5-flash-preview-tts"
    }
    
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-tts:generateContent?key={GOOGLE_API_KEY}"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(api_url, json=payload) as response:
                response.raise_for_status()
                data = await response.json()
                
                audio_data = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("inlineData", {}).get("data")
                mime_type = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("inlineData", {}).get("mimeType")
                
                if audio_data and mime_type.startswith("audio/"):
                    pcm_data = base64.b64decode(audio_data)
                    
                    sample_rate_match = mime_type.split(';')[0].split('rate=')[1]
                    sample_rate = int(sample_rate_match)
                    
                    output = io.BytesIO()
                    with wave.open(output, 'wb') as wav_file:
                        wav_file.setnchannels(1)
                        wav_file.setsampwidth(2)
                        wav_file.setframerate(sample_rate)
                        wav_file.writeframes(pcm_data)
                    
                    output.seek(0)
                    
                    await message.answer_voice(
                        voice=BufferedInputFile(output.getvalue(), filename="audio.wav"),
                        caption=f"Ваше аудио готово! ✨"
                    )
                else:
                    await message.answer("❌ Произошла ошибка: Не удалось сгенерировать аудио.")
                    
    except aiohttp.ClientError as e:
        logging.error(f"Ошибка HTTP-запроса: {e}")
        await message.answer("❌ Произошла ошибка при обращении к API. Попробуйте снова позже.")
    except Exception as e:
        logging.error(f"Непредвиденная ошибка: {e}")
        await message.answer("❌ Произошла непредвиденная ошибка.")
    finally:
        await processing_msg.delete()

@router.message()
async def fallback(message: types.Message):
    """
    Handles any unknown messages.
    Обрабатывает любые неизвестные сообщения.
    """
    await message.answer("Неизвестная команда. Напишите /help, чтобы увидеть список доступных команд.")

# =========================
# Главная функция запуска с вебхуками
# =========================
async def on_startup(dispatcher: Dispatcher, bot: Bot):
    """
    Sets up the webhook on bot startup.
    Настраивает вебхук при запуске бота.
    """
    await bot.set_webhook(f"{WEBHOOK_URL}{WEBHOOK_PATH}", drop_pending_updates=True)
    await bot.set_my_commands([
        BotCommand(command="start", description="Запуск бота"),
        BotCommand(command="help", description="Помощь"),
        BotCommand(command="speak", description="Превратить текст в голос"),
    ])
    logging.info("Бот запущен с вебхуками.")

async def on_shutdown(dispatcher: Dispatcher, bot: Bot):
    """
    Deletes the webhook on bot shutdown.
    Удаляет вебхук при остановке бота.
    """
    await bot.delete_webhook()
    logging.info("Бот остановлен.")

def main():
    """
    Main function to run the bot with aiohttp web server.
    Основная функция для запуска бота с веб-сервером aiohttp.
    """
    # Добавляем DefaultBotProperties для совместимости с aiogram 3.0+
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN_V2))
    dp = Dispatcher()
    dp.include_router(router)
    
    app = web.Application()
    
    # Исправляем ошибку AttributeError, используя правильный класс для вебхуков
    handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    handler.register(app, path=WEBHOOK_PATH)
    
    setup_application(app, dp, bot=bot)

    app.on_startup.append(lambda app, bot=bot: asyncio.create_task(on_startup(dp, bot)))
    app.on_shutdown.append(lambda app, bot=bot: asyncio.create_task(on_shutdown(dp, bot)))

    web.run_app(app, host=WEB_SERVER_HOST, port=WEB_SERVER_PORT)

if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен.")
