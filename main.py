import os
import json
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import WebAppInfo
from aiohttp import web
from aiogram.enums import ParseMode

# ==============================
# BOT CONFIGURATION AND ENVIRONMENT VARIABLES
# ==============================
# Get environment variables from Render
BOT_TOKEN = os.getenv("BOT_TOKEN")
BOT_USERNAME = os.getenv("BOT_USERNAME")
MY_ID = int(os.getenv("MY_ID"))
MINI_APP_URL = os.getenv("MINI_APP_URL")

# Check if all variables are loaded
if not all([BOT_TOKEN, BOT_USERNAME, MY_ID, MINI_APP_URL]):
    print("❌ ERROR: Not all environment variables are loaded!")

# Initialize the bot and dispatcher
bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.MARKDOWN_V2)
dp = Dispatcher()

# Dictionary of product prices (in Stars)
PRODUCT_PRICES = {
    "vip": 20,
    "booster": 10,
}

# Dictionary to store user balances (temporary example, for a real database use a different approach)
user_balances = {
    MY_ID: 1000  # Your ID for testing
}

# ==============================
# GENERAL BOT KEYBOARD
# ==============================
# Create a general keyboard for all commands
main_keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
    [
        types.InlineKeyboardButton(text="💰 Balance", callback_data="balance"),
        types.InlineKeyboardButton(text="📋 Tasks", callback_data="tasks")
    ],
    [
        types.InlineKeyboardButton(text="👥 Referrals", callback_data="referrals"),
        types.InlineKeyboardButton(text="🛍️ Shop", web_app=WebAppInfo(url=MINI_APP_URL))
    ],
    [
        types.InlineKeyboardButton(text="💳 Withdraw", callback_data="withdraw")
    ]
])

# ==============================
# COMMAND HANDLERS
# ==============================
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    """
    Handler for the /start command.
    Greets the user and shows all buttons.
    """
    user_id = message.from_user.id
    if user_id not in user_balances:
        user_balances[user_id] = 0 # Initialize a new user's balance
    
    await message.answer(
        f"Hi! 👋 I am CryptoWorkBot\\.\n\n"
        f"Your balance: **{user_balances.get(user_id, 0)} Stars** ✨\n\n"
        f"Complete tasks, invite friends, and earn TON\\!",
        reply_markup=main_keyboard
    )

@dp.message(Command("shop"))
async def cmd_shop(message: types.Message):
    """
    Handler for the /shop command.
    """
    await message.answer(
        "Click the button below to open the shop:",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="🛍️ Open Shop", web_app=WebAppInfo(url=MINI_APP_URL))]
        ])
    )

@dp.message(Command("add_ton"))
async def cmd_add_ton(message: types.Message):
    """
    Admin command to add Stars to a balance.
    Used only for you (the admin).
    """
    if message.from_user.id != MY_ID:
        await message.answer("❌ You do not have permission to use this command\\.")
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
            f"✅ Success\\! Added {amount} Stars to user ID {target_user_id}\\."
        )
    except (ValueError, IndexError):
        await message.answer(
            "❌ Command error\\.\\nUse the format: \\/add\\_ton <user ID> <amount>"
        )

# ==============================
# BUTTON PRESS HANDLERS
# ==============================
@dp.callback_query(F.data == "balance")
async def process_balance_button(callback_query: types.CallbackQuery):
    """
    Handles the "Balance" button press.
    """
    user_id = callback_query.from_user.id
    balance = user_balances.get(user_id, 0)
    await callback_query.answer(f"Your balance: {balance} Stars ✨", show_alert=True)

@dp.callback_query(F.data == "tasks")
async def process_tasks_button(callback_query: types.CallbackQuery):
    """
    Handles the "Tasks" button press.
    """
    await callback_query.answer("The 'Tasks' section is currently under development\\.", show_alert=True)

@dp.callback_query(F.data == "referrals")
async def process_referrals_button(callback_query: types.CallbackQuery):
    """
    Handles the "Referrals" button press.
    """
    await callback_query.answer("The 'Referrals' section is currently under development\\.", show_alert=True)

@dp.callback_query(F.data == "withdraw")
async def process_withdraw_button(callback_query: types.CallbackQuery):
    """
    Handles the "Withdraw" button press.
    """
    await callback_query.answer("The 'Withdraw' section is currently under development\\.", show_alert=True)

# ==============================
# GETTING DATA FROM WEBAPP AND PROCESSING THE PURCHASE
# ==============================
@dp.message(F.web_app_data)
async def handle_web_app_data(message: types.Message):
    """Handles data received from the web app."""
    user_id = message.from_user.id
    
    # Debug message to check if data reached the bot
    print(f"Received data from webapp: {message.web_app_data.data}")

    try:
        data = json.loads(message.web_app_data.data)
        
        if data["action"] == "buy":
            product = data["product"]
            
            # Check if the product exists
            price = PRODUCT_PRICES.get(product)
            if price is None:
                await message.answer(f"❌ Unknown product: {product}")
                return

            # Check user's balance
            current_balance = user_balances.get(user_id, 0)
            if current_balance >= price:
                user_balances[user_id] -= price
                await message.answer(f"🎉 You have successfully purchased **{product.upper()}** for {price} Stars\\!\\n"
                                     f"Your new balance: {user_balances[user_id]} Stars ✨")
            else:
                await message.answer(f"❌ Insufficient funds to purchase **{product.upper()}**\\.\\n"
                                     f"Your balance: {current_balance} Stars\\. Required: {price} Stars\\.")
    except (json.JSONDecodeError, KeyError) as e:
        await message.answer(f"❌ Error processing data from the web app: invalid format\\.")
        print(f"ERROR: Invalid JSON or key in web_app_data: {e}")
    except Exception as e:
        await message.answer(f"❌ An unexpected error occurred: {e}")
        print(f"ERROR: Unhandled exception in web_app_data handler: {e}")

# ==============================
# MAIN FUNCTION TO RUN THE BOT
# ==============================
async def main():
    """
    Main function to run the bot with Webhook.
    """
    # Get the URL and port provided by Render
    render_url = os.getenv("RENDER_EXTERNAL_URL")
    if not render_url:
        print("❌ ERROR: Could not get RENDER_EXTERNAL_URL. Webhook launch is not possible.")
        return
        
    port = int(os.environ.get("PORT", 8000))
    webhook_url = f"{render_url}/webhook"

    print(f"Setting webhook to URL: {webhook_url}")
    await bot.set_webhook(webhook_url)

    # Start the web server to handle the webhook
    app = web.Application()
    app.router.add_post("/webhook", dp.webhooks.aiohttp_handlers["aiogram"])
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    print(f"Bot is running on port {port}")
    await site.start()

if __name__ == "__main__":
    asyncio.run(main())
