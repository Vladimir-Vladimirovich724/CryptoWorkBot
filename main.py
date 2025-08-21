import os
import json
import asyncio
import requests
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InputFile
from aiohttp import web

# ==============================
# ПЕРЕМЕННЫЕ
# ==============================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ELEVEN_API_KEY = os.getenv("ELEVENLABS_API_KEY")
VOICE_ID = "STANDARD_VOICE_ID"  # голос по умолчанию
MY_ID = 123456789  # твой ID администратора

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher(bot)

DATA_FILE = "db.json"

# ==============================
# ФУНКЦИИ ДЛЯ РАБОТЫ С ДАННЫМИ
# ==============================
def load_data():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return {"balances": {}}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

# ==============================
# Существующие команды бота (рефералы, баланс и т.д.)
# Здесь вставь свои старые функции покупки, add_ton и т.д.
# ==============================

# ==============================
# НОВАЯ КОМАНДА: /tts
# ==============================
@dp.message(Command("tts"))
async def tts_command(message: types.Message):
    text = message.get_args()
    if not text:
        await message.answer("❌ Пришлите текст после команды, например: /tts Привет!")
        return
    
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"
    headers = {"xi-api-key": ELEVEN_API_KEY, "Content-Type": "application/json"}
    data = {"text": text, "voice_settings": {"stability": 0.5, "similarity_boost": 0.5}}
    
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        with open("voice.ogg", "wb") as f:
            f.write(response.content)
        await message.reply_voice(InputFile("voice.ogg"))
    else:
        await message.answer(f"❌ Ошибка при генерации голоса: {response.status_code}")

# ==============================
# ФУНКЦИЯ-ЗАГЛУШКА ДЛЯ АНИМАЦИИ
# ==============================
def generate_animation(image_path, audio_path):
    """
    Заглушка: подключим D-ID API позже.
    Возвращает путь к готовому видео (например, result.mp4)
    """
    return "result.mp4"

# ==============================
# НОВАЯ КОМАНДА: /animate
# ==============================
@dp.message(Command("animate"))
async def animate_command(message: types.Message):
    text = message.get_args()
    if not text:
        await message.answer("❌ Пришлите текст после команды, например: /animate Привет!")
        return

    # 1️⃣ Генерируем аудио
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"
    headers = {"xi-api-key": ELEVEN_API_KEY, "Content-Type": "application/json"}
    data = {"text": text, "voice_settings": {"stability": 0.5, "similarity_boost": 0.5}}
    response = requests.post(url, headers=headers, json=data)
    if response.status_code != 200:
        await message.answer("❌ Ошибка при генерации голоса")
        return
    audio_path = "voice.ogg"
    with open(audio_path, "wb") as f:
        f.write(response.content)

    # 2️⃣ Генерируем видео
    image_path = "avatar.png"  # статичное изображение персонажа
    video_path = generate_animation(image_path, audio_path)

    # 3️⃣ Отправляем видео пользователю
    await message.reply_video(InputFile(video_path))

# ==============================
# ГЛАВНАЯ ФУНКЦИЯ ДЛЯ ЗАПУСКА
# ==============================
async def main():
    render_url = os.getenv("RENDER_EXTERNAL_URL")
    if not render_url:
        print("❌ ОШИБКА: Не удалось получить RENDER_EXTERNAL_URL.")
        return

    port = int(os.environ.get("PORT", 8000))
    webhook_url = f"{render_url}/webhook"

    try:
        await bot.delete_webhook()
    except:
        pass

    await bot.set_webhook(webhook_url)

    app = web.Application()
    async def handler(request):
        update = types.Update(**await request.json())
        await dp.process_update(update)
        return web.Response()
    app.router.add_post("/webhook", handler)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"Бот запущен на порту {port}")

if __name__ == "__main__":
    asyncio.run(main())
