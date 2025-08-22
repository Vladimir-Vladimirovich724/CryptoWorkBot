import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, Router, types
from aiogram.enums import ParseMode
from aiogram.types import BotCommand
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import aiohttp
import json
import base64
import io
import wave
import uuid

# =========================
# Конфигурация
# =========================
BOT_TOKEN = os.getenv("BOT_TOKEN")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN env var is required. Задайте переменную окружения BOT_TOKEN.")

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
    waiting_for_voice = State()
    waiting_for_language = State()

# =========================
# Хендлеры
# =========================
@router.message(CommandStart())
async def cmd_start(message: types.Message):
    """
    Обрабатывает команду /start.
    """
    await message.answer("👋 Привет! Я готов к работе. Используйте /help для списка команд.")

@router.message(Command("help"))
async def cmd_help(message: types.Message):
    """
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
    Начинает процесс преобразования текста в голос.
    """
    await message.answer("Пожалуйста, отправьте текст, который нужно озвучить.")
    await state.set_state(TTSStates.waiting_for_text)

@router.message(TTSStates.waiting_for_text)
async def process_tts_text(message: types.Message, state: FSMContext):
    """
    Получает текст от пользователя и отправляет запрос к Gemini API для TTS.
    """
    await state.clear()
    
    # Отправляем сообщение-заглушку, чтобы пользователь знал, что процесс идет
    processing_msg = await message.answer("⏳ Генерирую аудио...")
    
    text_to_speak = message.text
    
    # Конфигурация для TTS API
    payload = {
        "contents": [
            {
                "parts": [
                    { "text": text_to_speak }
                ]
            }
        ],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {
                    "prebuiltVoiceConfig": { "voiceName": "Kore" }
                }
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
                
                # Извлекаем аудиоданные
                audio_data = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("inlineData", {}).get("data")
                mime_type = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("inlineData", {}).get("mimeType")
                
                if audio_data and mime_type.startswith("audio/"):
                    # Декодируем base64 данные
                    pcm_data = base64.b64decode(audio_data)
                    
                    # Получаем частоту дискретизации из MIME-типа
                    sample_rate_match = mime_type.split(';')[0].split('rate=')[1]
                    sample_rate = int(sample_rate_match)
                    
                    # Сохраняем как WAV файл
                    output = io.BytesIO()
                    with wave.open(output, 'wb') as wav_file:
                        wav_file.setnchannels(1)
                        wav_file.setsampwidth(2)
                        wav_file.setframerate(sample_rate)
                        wav_file.writeframes(pcm_data)
                    
                    # Сбрасываем указатель файла
                    output.seek(0)
                    
                    # Отправляем аудиофайл пользователю
                    await message.answer_voice(
                        voice=types.BufferedInputFile(output.getvalue(), filename=f"audio_{uuid.uuid4()}.wav"),
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
        await processing_msg.delete() # Удаляем сообщение-заглушку

@router.message()
async def fallback(message: types.Message):
    """
    Обрабатывает любые сообщения, которые не подошли под другие хендлеры.
    """
    await message.answer("Неизвестная команда. Напишите /help, чтобы увидеть список доступных команд.")

# =========================
# Главная функция запуска
# =========================
async def main():
    """
    Основная функция для запуска бота.
    """
    bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.MARKDOWN_V2)
    dp = Dispatcher()
    dp.include_router(router)
    
    # Регистрация команд для меню бота
    commands = [
        BotCommand(command="start", description="Запуск бота"),
        BotCommand(command="help", description="Помощь"),
        BotCommand(command="speak", description="Превратить текст в голос"),
    ]
    await bot.set_my_commands(commands)
    
    logging.info("Бот запущен.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен.")
