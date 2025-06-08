import os
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from kas_config import BOT_TOKEN
from bot.recognition import get_dog_by_photo

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
    cur = conn.cursor()
    cur.execute(
        "SELECT name, pen, status, description, photo_path FROM dogs"
    )
    rows = cur.fetchall()
    for name, pen, status, desc, photo_path in rows:
        text = (
            f"🐶 *{name}*\n"
            f"📍 Pen: {pen or 'N/A'}\n"
            f"📋 Status: {status or 'N/A'}\n"
            f"📝 {desc or 'No description yet'}"
        )

        if photo_path and os.path.exists(photo_path):
            with open(photo_path, "rb") as photo:
                await bot.send_photo(
                    chat_id=message.chat.id,
                    photo=photo,
                    caption=text,
                    parse_mode="Markdown",
                )
        else:
            await message.reply(text, parse_mode="Markdown")

    conn.close()

# ✉️ `/catalog` text command
@dp.message_handler(commands=['catalog'])
async def catalog_command(message: types.Message):
    await show_catalog(message)

# 🧩 Inline button callback handler
@dp.callback_query_handler(lambda c: c.data == 'catalog')
async def handle_catalog_callback(callback_query: types.CallbackQuery):
    await show_catalog(callback_query.message)
    await bot.answer_callback_query(callback_query.id)

# 🔍 Callback for identification button
@dp.callback_query_handler(lambda c: c.data == 'identify')
async def handle_identify_callback(callback_query: types.CallbackQuery):
    await bot.send_message(callback_query.from_user.id, "📸 Please send a photo of the dog you want to identify.")
    await bot.answer_callback_query(callback_query.id)


# 📷 Photo handler using embedding search
@dp.message_handler(content_types=['photo'])
async def handle_photo(message: types.Message):
    photo = message.photo[-1]
    file = await photo.download()
    dog = get_dog_by_photo(file.name)
    os.remove(file.name)
    if dog:
        text = (
            f"🐶 *{dog['name']}*\n"
            f"📍 Pen: {dog['pen'] or 'N/A'}\n"
            f"📋 Status: {dog['status'] or 'N/A'}\n"
            f"📝 {dog['description'] or 'No description yet'}"
        )
        if dog['photo_path'] and os.path.exists(dog['photo_path']):
            with open(dog['photo_path'], 'rb') as p:
                await bot.send_photo(
                    chat_id=message.chat.id,
                    photo=p,
                    caption=text,
                    parse_mode="Markdown",
                )
        else:
            await message.reply(text, parse_mode="Markdown")
    else:
        await message.reply("❌ Dog not found in catalog.")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
