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
from aiogram.types import BotCommand, BufferedInputFile
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

# =========================
# Configuration and environment variables
# =========================
BOT_TOKEN = os.getenv("BOT_TOKEN")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
WEB_SERVER_HOST = os.getenv("WEB_SERVER_HOST", "0.0.0.0")
WEB_SERVER_PORT = int(os.getenv("PORT", 8080))
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "/webhook")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

if not all([BOT_TOKEN, GOOGLE_API_KEY, WEBHOOK_URL]):
    logging.error("Could not find environment variables BOT_TOKEN, GOOGLE_API_KEY, and WEBHOOK_URL.")
    raise RuntimeError("Missing environment variables!")

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
    await message.answer("👋 Привет! Я бот, который превращает текст в голос. Напиши /help чтобы узнать команды.")

@router.message(Command("help"))
async def cmd_help(message: types.Message):
    commands_list = (
        "Список команд:\n"
        "/speak - превратить текст в голос"
    )
    await message.answer(commands_list)

@router.message(Command("speak"))
async def cmd_speak(message: types.Message, state: FSMContext):
    await message.answer("✍️ Отправьте текст, который нужно озвучить.")
    await state.set_state(TTSStates.waiting_for_text)

@router.message(TTSStates.waiting_for_text)
async def process_tts_text(message: types.Message, state: FSMContext):
    await state.clear()
    processing_msg = await message.answer("⏳ Генерирую аудио...")

    text_to_speak = message.text
    payload = {
        "contents": [
            {"parts": [{"text": text_to_speak}]}
        ],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": "Kore"}}
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

                audio_data = (
                    data.get("candidates", [{}])[0]
                        .get("content", {}).get("parts", [{}])[0]
                        .get("inlineData", {}).get("data")
                )
                mime_type = (
                    data.get("candidates", [{}])[0]
                        .get("content", {}).get("parts", [{}])[0]
                        .get("inlineData", {}).get("mimeType")
                )

                if audio_data and mime_type and mime_type.startswith("audio/"):
                    pcm_data = base64.b64decode(audio_data)

                    # По умолчанию sample_rate
                    sample_rate = 24000
                    if ";" in mime_type:
                        for part in mime_type.split(";"):
                            if "rate=" in part:
                                try:
                                    sample_rate = int(part.split("=")[1])
                                except ValueError:
                                    pass

                    output = io.BytesIO()
                    with wave.open(output, "wb") as wav_file:
                        wav_file.setnchannels(1)
                        wav_file.setsampwidth(2)
                        wav_file.setframerate(sample_rate)
                        wav_file.writeframes(pcm_data)
                    output.seek(0)

                    await message.answer_voice(
                        voice=BufferedInputFile(output.getvalue(), filename="audio.wav"),
                        caption="✅ Ваше аудио готово!"
                    )
                else:
                    await message.answer("❌ Ошибка: не удалось сгенерировать аудио.")

    except aiohttp.ClientError as e:
        logging.error(f"HTTP error: {e}")
        await message.answer("❌ Ошибка API, попробуйте позже.")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        await message.answer("❌ Непредвиденная ошибка.")
    finally:
        await processing_msg.delete()

@router.message()
async def fallback(message: types.Message):
    await message.answer("Неизвестная команда. Используйте /help.")

# =========================
# Webhook setup
# =========================
async def on_startup(dispatcher: Dispatcher, bot: Bot):
    await bot.set_webhook(f"{WEBHOOK_URL}{WEBHOOK_PATH}", drop_pending_updates=True)
    await bot.set_my_commands([
        BotCommand(command="start", description="Запуск бота"),
        BotCommand(command="help", description="Помощь"),
        BotCommand(command="speak", description="Превратить текст в голос"),
    ])
    logging.info("Bot started with webhooks.")

async def on_shutdown(dispatcher: Dispatcher, bot: Bot):
    await bot.delete_webhook()
    logging.info("Bot stopped.")

def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)

    app = web.Application()
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
