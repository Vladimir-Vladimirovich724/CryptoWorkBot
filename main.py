import asyncio
import logging
import os
import json
import io
import wave
import base64
import aiohttp
from aiohttp import web

from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.types import BotCommand, BufferedInputFile
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# =========================
# Configuration and environment variables
# =========================
# We will only need BOT_TOKEN and GOOGLE_API_KEY for polling
BOT_TOKEN = os.getenv("BOT_TOKEN")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Check that all environment variables are set.
if not all([BOT_TOKEN, GOOGLE_API_KEY]):
    logging.error("Could not find environment variables BOT_TOKEN and GOOGLE_API_KEY.")
    raise RuntimeError("Could not find all required environment variables.")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

router = Dispatcher()
bot = Bot(token=BOT_TOKEN)

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
                
                if audio_data and mime_type and mime_type.startswith("audio/"):
                    pcm_data = base64.b64decode(audio_data)
                    
                    sample_rate = 24000
                    if mime_type and "rate=" in mime_type:
                        for part in mime_type.split(";"):
                            if "rate=" in part:
                                try:
                                    sample_rate = int(part.split("=")[1])
                                except ValueError:
                                    pass

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
# Main function to run the bot with long-polling
# =========================
async def main():
    await router.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot has been stopped.")
