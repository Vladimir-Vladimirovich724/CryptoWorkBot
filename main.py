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
# Configuration and environment variables
# =========================
# We will get environment variables that need to be configured on the hosting.
# We will make the check more reliable to avoid errors.
BOT_TOKEN = os.getenv("BOT_TOKEN")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
WEB_SERVER_HOST = os.getenv("WEB_SERVER_HOST", "0.0.0.0")
WEB_SERVER_PORT = int(os.getenv("PORT", 8080))
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "/webhook")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# Check that all environment variables are set.
if not all([BOT_TOKEN, GOOGLE_API_KEY, WEBHOOK_URL]):
    logging.error("Could not find environment variables BOT_TOKEN, GOOGLE_API_KEY, and WEBHOOK_URL.")
    raise RuntimeError("Could not find all required environment variables.")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

router = Router()

# =========================
# FSM states for TTS
# =========================
class TTSStates(StatesGroup):
    waiting_for_text = State()

# =========================
# Handlers
# =========================
@router.message(CommandStart())
async def cmd_start(message: types.Message):
    """
    Handles the /start command.
    """
    await message.answer("👋 Привет! Я готов к работе. Используйте /help для списка команд.")

@router.message(Command("help"))
async def cmd_help(message: types.Message):
    """
    Handles the /help command.
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
    """
    await message.answer("Пожалуйста, отправьте текст, который нужно озвучить.")
    await state.set_state(TTSStates.waiting_for_text)

@router.message(TTSStates.waiting_for_text)
async def process_tts_text(message: types.Message, state: FSMContext):
    """
    Receives text from the user and sends a request to the Gemini API for TTS.
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
                    
                    # Extract sample rate from the MIME type
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
        logging.error(f"HTTP request error: {e}")
        await message.answer("❌ Произошла ошибка при обращении к API. Попробуйте снова позже.")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        await message.answer("❌ Произошла непредвиденная ошибка.")
    finally:
        await processing_msg.delete()

@router.message()
async def fallback(message: types.Message):
    """
    Handles any unknown messages.
    """
    await message.answer("Неизвестная команда. Напишите /help, чтобы увидеть список доступных команд.")

# =========================
# Main function to run with webhooks
# =========================
async def on_startup(dispatcher: Dispatcher, bot: Bot):
    """
    Sets up the webhook on bot startup.
    """
    await bot.set_webhook(f"{WEBHOOK_URL}{WEBHOOK_PATH}", drop_pending_updates=True)
    await bot.set_my_commands([
        BotCommand(command="start", description="Запуск бота"),
        BotCommand(command="help", description="Помощь"),
        BotCommand(command="speak", description="Превратить текст в голос"),
    ])
    logging.info("Bot is running with webhooks.")

async def on_shutdown(dispatcher: Dispatcher, bot: Bot):
    """
    Deletes the webhook on bot shutdown.
    """
    await bot.delete_webhook()
    logging.info("Bot has been stopped.")

def main():
    """
    Main function to run the bot with aiohttp web server.
    """
    # Remove the Markdown parser to prevent errors
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    
    app = web.Application()
    
    # Correcting the AttributeError by using the correct class for webhooks
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
        logging.info("Bot has been stopped.")
