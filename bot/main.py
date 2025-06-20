import os
import gc
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
from kas_config import BOT_TOKEN
from bot.recognition import get_dog_by_photo

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# 🔘 Start menu
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("🔍 Identify a Dog", callback_data="identify"),
        InlineKeyboardButton("🐶 View Catalog", callback_data="catalog"),
        InlineKeyboardButton("☕ Support the Project", url="https://t.me/kasdogs/6")
    )
    await message.reply(
        "👋 Hello! I'm *KAS Dogs Bot* — your dog recognition assistant 🐾\n\n"
        "📸 Send a photo of a dog to get information,\n"
        "or choose an option below:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

# 📂 Get all distinct categories
def get_categories():
    conn = sqlite3.connect("db/dogs.db")
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT category FROM dogs WHERE category IS NOT NULL")
    results = cur.fetchall()
    conn.close()
    return [r[0] for r in results]

# 🧭 Callback: Show categories
@dp.callback_query_handler(lambda c: c.data == 'catalog')
async def handle_catalog_callback(callback_query: types.CallbackQuery):
    categories = get_categories()
    if not categories:
        await bot.send_message(callback_query.from_user.id, "📭 No categories available.")
        await bot.answer_callback_query(callback_query.id)
        return

    keyboard = InlineKeyboardMarkup(row_width=2)
    for cat in categories:
        keyboard.add(InlineKeyboardButton(cat, callback_data=f"category_{cat}"))

    await bot.send_message(
        callback_query.from_user.id,
        "📂 Choose a category to view dogs:",
        reply_markup=keyboard
    )
    await bot.answer_callback_query(callback_query.id)

# 🐾 Show dogs in a category
@dp.callback_query_handler(lambda c: c.data.startswith("category_"))
async def show_catalog_by_category(callback_query: types.CallbackQuery):
    category = callback_query.data[len("category_"):]  # Extract category

    conn = sqlite3.connect("db/dogs.db")
    cur = conn.cursor()
    cur.execute(
        "SELECT name, pen, status, description, photo_folder FROM dogs WHERE category = ?",
        (category,)
    )
    rows = cur.fetchall()
    conn.close()

    if not rows:
        await bot.send_message(callback_query.from_user.id, f"📭 No dogs found in *{category}*.", parse_mode="Markdown")
        await bot.answer_callback_query(callback_query.id)
        return

    for name, pen, status, desc, folder in rows:
        text = (
            f"🐶 *{name}*\n"
            f"📂 Category: {category}\n"
            f"📍 Pen: {pen or 'N/A'}\n"
            f"📋 Status: {status or 'N/A'}\n"
            f"📝 {desc or 'No description yet'}"
        )
        if folder and os.path.isdir(folder):
            images = [f for f in os.listdir(folder) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
            if images:
                photo_path = os.path.join(folder, images[0])
                with open(photo_path, 'rb') as p:
                    await bot.send_photo(callback_query.from_user.id, photo=p, caption=text, parse_mode="Markdown")
                continue

        await bot.send_message(callback_query.from_user.id, text, parse_mode="Markdown")

    # ⬅️ Add Main Menu button at the end
    keyboard = InlineKeyboardMarkup().add(
        InlineKeyboardButton("🔙 Main Menu", callback_data="start_over")
    )
    await bot.send_message(callback_query.from_user.id, "📋 Done showing catalog.", reply_markup=keyboard)
    await bot.answer_callback_query(callback_query.id)

# 🔁 Go back to Main Menu
@dp.callback_query_handler(lambda c: c.data == "start_over")
async def return_to_main(callback_query: types.CallbackQuery):
    await start(callback_query.message)
    await bot.answer_callback_query(callback_query.id)

# ✉️ /catalog text command = show category menu
@dp.message_handler(commands=['catalog'])
async def catalog_command(message: types.Message):
    categories = get_categories()
    if not categories:
        await message.reply("📭 No categories available.")
        return

    keyboard = InlineKeyboardMarkup(row_width=2)
    for cat in categories:
        keyboard.add(InlineKeyboardButton(cat, callback_data=f"category_{cat}"))

    await message.reply("📂 Choose a category to view dogs:", reply_markup=keyboard)

# 🔍 Handle "Identify a Dog"
@dp.callback_query_handler(lambda c: c.data == 'identify')
async def handle_identify_callback(callback_query: types.CallbackQuery):
    await bot.send_message(callback_query.from_user.id, "📸 Please send a photo of the dog you want to identify.")
    await bot.answer_callback_query(callback_query.id)

# 📷 Handle incoming photos
@dp.message_handler(content_types=['photo'])
async def handle_photo(message: types.Message):
    photo = message.photo[-1]
    file_path = f"photos/{photo.file_id}.jpg"
    await photo.download(destination_file=file_path)

    try:
        dog = get_dog_by_photo(file_path)
    except Exception as e:
        print(f"⚠️ Error during recognition: {e}")
        dog = None

    try:
        if dog:
            text = (
                f"🐶 *{dog['name']}*\n"
                f"📍 Pen: {dog['pen'] or 'N/A'}\n"
                f"📋 Status: {dog['status'] or 'N/A'}\n"
                f"📝 {dog['description'] or 'No description yet'}"
            )
            folder = dog.get("photo_folder")
            if folder and os.path.isdir(folder):
                images = [f for f in os.listdir(folder) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
                if images:
                    with open(os.path.join(folder, images[0]), 'rb') as p:
                        await bot.send_photo(message.chat.id, photo=p, caption=text, parse_mode="Markdown")
                        return
            await message.reply(text, parse_mode="Markdown")
        else:
            await message.reply("❌ Dog not found in catalog or photo could not be processed.")
    finally:
        gc.collect()
        try:
            os.remove(file_path)
        except Exception as e:
            print(f"⚠️ Still couldn’t delete file: {e}")

# 🚀 Start bot
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
