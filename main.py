import os
import asyncio
import sqlite3
from datetime import datetime

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiohttp import web

# === Конфиг ===
TOKEN = os.getenv("BOT_TOKEN")  # в Render: Settings → Environment → Environment Variables
BOT_USERNAME = "MenqenqmersareryBot"  # без @
ADMIN_USERNAME = "Ferdinantik_ot777"  # без @, чтобы админом был именно твой аккаунт

DB_PATH = "bot.db"

bot = Bot(token=TOKEN)
dp = Dispatcher()

# === База данных ===
def db():
    return sqlite3.connect(DB_PATH)

def init_db():
    with db() as conn:
        c = conn.cursor()
        c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            balance REAL DEFAULT 0.0,
            referrer INTEGER
        )""")
        c.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            url TEXT,
            reward REAL NOT NULL,
            active INTEGER DEFAULT 1
        )""")
        c.execute("""
        CREATE TABLE IF NOT EXISTS task_completions (
            user_id INTEGER,
            task_id INTEGER,
            completed_at TEXT,
            PRIMARY KEY (user_id, task_id)
        )""")
        conn.commit()

# === Утилиты ===
def is_admin(message: types.Message | types.CallbackQuery) -> bool:
    u = message.from_user if isinstance(message, types.CallbackQuery) else message.from_user
    return (u.username or "").lower() == ADMIN_USERNAME.lower()

def main_menu():
    kb = InlineKeyboardBuilder()
    kb.button(text="💰 Баланс", callback_data="balance")
    kb.button(text="📋 Задания", callback_data="tasks")
    kb.button(text="👥 Приглашения", callback_data="invite")
    kb.button(text="💸 Вывод", callback_data="withdraw")
    kb.adjust(2)
    return kb.as_markup()

def admin_menu():
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Добавить задание", callback_data="admin_addtask_help")
    kb.button(text="📋 Список заданий", callback_data="admin_listtasks")
    kb.button(text="📢 Рассылка", callback_data="admin_broadcast_help")
    kb.adjust(1)
    return kb.as_markup()

# === Команда /start + рефералка ===
@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    init_db()  # на всякий случай
    user_id = message.from_user.id
    username = message.from_user.username or "no_username"

    # разбор реферала
    parts = message.text.split()
    referrer = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None

    with db() as conn:
        c = conn.cursor()
        c.execute("SELECT id FROM users WHERE id = ?", (user_id,))
        exists = c.fetchone()
        if not exists:
            c.execute("INSERT INTO users (id, username, balance, referrer) VALUES (?, ?, 0.0, ?)",
                      (user_id, username, referrer))
            # бонус пригласителю
            if referrer and referrer != user_id:
                c.execute("UPDATE users SET balance = balance + 0.1 WHERE id = ?", (referrer,))
        else:
            c.execute("UPDATE users SET username = ? WHERE id = ?", (username, user_id))
        conn.commit()

    await message.answer(
        f"👋 Привет, {message.from_user.first_name}!\n"
        f"Добро пожаловать в <b>CryptoWorkBot</b> 💼\n\n"
        f"Выполняй задания и зарабатывай <b>TON</b>!",
        reply_markup=main_menu(),
        parse_mode="HTML"
    )

# === Баланс ===
@dp.callback_query(F.data == "balance")
async def on_balance(cb: types.CallbackQuery):
    with db() as conn:
        c = conn.cursor()
        c.execute("SELECT balance FROM users WHERE id = ?", (cb.from_user.id,))
        row = c.fetchone()
        bal = row[0] if row else 0.0
    await cb.message.answer(f"💰 Ваш баланс: <b>{bal:.2f} TON</b>", parse_mode="HTML")
    await cb.answer()

# === Задания ===
@dp.callback_query(F.data == "tasks")
async def on_tasks(cb: types.CallbackQuery):
    with db() as conn:
        c = conn.cursor()
        c.execute("SELECT id, title, reward FROM tasks WHERE active = 1 ORDER BY id DESC")
        items = c.fetchall()

    if not items:
        await cb.message.answer("📋 Сейчас нет активных заданий.")
        await cb.answer()
        return

    kb = InlineKeyboardBuilder()
    for tid, title, reward in items:
        kb.button(text=f"{title} (+{reward} TON)", callback_data=f"task_{tid}")
    kb.adjust(1)
    await cb.message.answer("📋 Доступные задания:", reply_markup=kb.as_markup())
    await cb.answer()

@dp.callback_query(F.data.startswith("task_"))
async def on_task(cb: types.CallbackQuery):
    task_id = int(cb.data.split("_")[1])

    with db() as conn:
        c = conn.cursor()
        # проверка существования и активности
        c.execute("SELECT title, url, reward, active FROM tasks WHERE id = ?", (task_id,))
        t = c.fetchone()
        if not t or t[3] != 1:
            await cb.answer("Задание недоступно", show_alert=True)
            return

        title, url, reward, _ = t

        # проверка — не делал ли уже
        c.execute("SELECT 1 FROM task_completions WHERE user_id = ? AND task_id = ?",
                  (cb.from_user.id, task_id))
        done = c.fetchone()
        if done:
            await cb.answer("Вы уже выполнили это задание", show_alert=True)
            return

        # НА СЕЙЧАС: подтверждаем сразу (позже можно добавить проверку подписки/перехода)
        c.execute("INSERT INTO task_completions (user_id, task_id, completed_at) VALUES (?, ?, ?)",
                  (cb.from_user.id, task_id, datetime.utcnow().isoformat()))
        c.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (reward, cb.from_user.id))
        conn.commit()

    text = f"✅ Задание выполнено: <b>{title}</b>\n" \
           f"Начислено: <b>{reward} TON</b>"
    if url:
        text += f"\n🔗 Ссылка: {url}"

    await cb.message.answer(text, parse_mode="HTML")
    await cb.answer()

# === Рефералка ===
@dp.callback_query(F.data == "invite")
async def on_invite(cb: types.CallbackQuery):
    link = f"https://t.me/{BOT_USERNAME}?start={cb.from_user.id}"
    with db() as conn:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM users WHERE referrer = ?", (cb.from_user.id,))
        count = c.fetchone()[0]
    await cb.message.answer(
        "👥 Приглашай друзей и получай <b>0.1 TON</b> за каждого!\n\n"
        f"🔗 Твоя ссылка:\n<code>{link}</code>\n\n"
        f"Приглашено: {count}",
        parse_mode="HTML"
    )
    await cb.answer()

# === Вывод (пока вручную) ===
@dp.callback_query(F.data == "withdraw")
async def on_withdraw(cb: types.CallbackQuery):
    await cb.message.answer(
        "💸 Вывод временно доступен через администратора.\n"
        f"Напишите: @{ADMIN_USERNAME}"
    )
    await cb.answer()

# === Админка ===
@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if not is_admin(message):
        await message.reply("⛔️ Доступ запрещён.")
        return
    await message.answer("⚙️ Админ-панель", reply_markup=admin_menu())

@dp.callback_query(F.data == "admin_addtask_help")
async def admin_addtask_help(cb: types.CallbackQuery):
    if not is_admin(cb):
        await cb.answer("Нет доступа", show_alert=True)
        return
    await cb.message.answer(
        "Чтобы добавить задание, отправь команду в чат:\n\n"
        "<code>/addtask Заголовок | 0.2 | https://t.me/your_channel</code>\n\n"
        "• Заголовок — текст кнопки и карточки\n"
        "• 0.2 — награда в TON\n"
        "• ссылка — необязательно (можно пропустить)",
        parse_mode="HTML"
    )
    await cb.answer()

@dp.message(Command("addtask"))
async def admin_addtask(message: types.Message):
    if not is_admin(message):
        await message.reply("⛔️ Доступ запрещён.")
        return

    text = message.text[len("/addtask"):].strip()
    if not text:
        await message.reply("Формат: /addtask Заголовок | 0.2 | https://link (ссылка опционально)")
        return

    # парсинг "title | reward | url?"
    parts = [p.strip() for p in text.split("|")]
    if len(parts) < 2:
        await message.reply("Нужно минимум: заголовок и награда. Пример: /addtask Подпишись | 0.2 | https://t.me/...")
        return

    title = parts[0]
    try:
        reward = float(parts[1].replace(",", "."))
    except ValueError:
        await message.reply("Награда должна быть числом, например: 0.2")
        return

    url = parts[2] if len(parts) >= 3 else None

    with db() as conn:
        c = conn.cursor()
        c.execute("INSERT INTO tasks (title, url, reward, active) VALUES (?, ?, ?, 1)",
                  (title, url, reward))
        conn.commit()
    await message.reply(f"✅ Задание добавлено: {title} (+{reward} TON)")

@dp.callback_query(F.data == "admin_listtasks")
async def admin_list(cb: types.CallbackQuery):
    if not is_admin(cb):
        await cb.answer("Нет доступа", show_alert=True)
        return
    with db() as conn:
        c = conn.cursor()
        c.execute("SELECT id, title, reward, active FROM tasks ORDER BY id DESC")
        rows = c.fetchall()
    if not rows:
        await cb.message.answer("Список заданий пуст.")
        await cb.answer()
        return

    text = "📋 Задания:\n"
    for tid, title, reward, active in rows:
        status = "✅" if active == 1 else "⏸"
        text += f"• #{tid} {status} {title} (+{reward} TON)\n"
    await cb.message.answer(text)
    await cb.answer()

@dp.callback_query(F.data == "admin_broadcast_help")
async def admin_broadcast_help(cb: types.CallbackQuery):
    if not is_admin(cb):
        await cb.answer("Нет доступа", show_alert=True)
        return
    await cb.message.answer(
        "Рассылка: отправь в личку боту сообщение в формате:\n\n"
        "<code>/broadcast текст рассылки</code>",
        parse_mode="HTML"
    )
    await cb.answer()

@dp.message(Command("broadcast"))
async def admin_broadcast(message: types.Message):
    if not is_admin(message):
        await message.reply("⛔️ Доступ запрещён.")
        return
    payload = message.text[len("/broadcast"):].strip()
    if not payload:
        await message.reply("Напиши: /broadcast текст")
        return

    # собираем всех пользователей
    with db() as conn:
        c = conn.cursor()
        c.execute("SELECT id FROM users")
        ids = [row[0] for row in c.fetchall()]

    sent, failed = 0, 0
    for uid in ids:
        try:
            await bot.send_message(uid, f"📢 {payload}")
            sent += 1
        except Exception:
            failed += 1
            await asyncio.sleep(0.05)

    await message.reply(f"✅ Рассылка отправлена. Успешно: {sent}, ошибок: {failed}")

# === HTTP-сервер для Render (держит сервис живым) ===
async def handle_root(_):
    return web.Response(text="Bot is running!")

async def start_webserver():
    app = web.Application()
    app.router.add_get("/", handle_root)
    port = int(os.getenv("PORT", 10000))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

# === main ===
async def main():
    init_db()
    await start_webserver()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
