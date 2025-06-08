import os
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputFile
from kas_config import BOT_TOKEN

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# 🔘 Start command with buttons
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("🔍 Identify a Dog", callback_data="identify"),
        InlineKeyboardButton("🐶 View Catalog", callback_data="catalog"),
        InlineKeyboardButton("☕ Support the Project", url="https://t.me/proseacode")
    )

    await message.reply(
        "👋 Hello! I'm *KAS Dogs Bot* — your dog recognition assistant 🐾\n\n"
        "📸 Send a photo of a dog to get information,\n"
        "or choose an option below:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

# 📄 Catalog handler as a function
async def show_catalog(message: types.Message):
    conn = sqlite3.connect("db/dogs.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, pen, status, description, photo_path FROM dogs")
    dogs = cursor.fetchall()
    conn.close()

    if not dogs:
        await message.reply("📭 No dogs in the catalog yet.")
        return

    for dog in dogs:
        dog_id, name, pen, status, desc, photo_path = dog
        text = (
            f"🐶 *{name}*\n"
            f"📍 Pen: {pen or 'N/A'}\n"
            f"📋 Status: {status or 'N/A'}\n"
            f"📝 {desc or 'No description yet'}"
        )

        if os.path.exists(photo_path):
            with open(photo_path, 'rb') as photo:
                await bot.send_photo(
                    chat_id=message.chat.id,
                    photo=photo,
                    caption=text,
                    parse_mode="Markdown"
                )
        else:
            await message.reply(text, parse_mode="Markdown")

# ✉️ `/catalog` text command
@dp.message_handler(commands=['catalog'])
async def catalog_command(message: types.Message):
    await show_catalog(message)

# 🧩 Inline button callback handler
@dp.callback_query_handler(lambda c: c.data == 'catalog')
async def handle_catalog_callback(callback_query: types.CallbackQuery):
    await show_catalog(callback_query.message)
    await bot.answer_callback_query(callback_query.id)

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
