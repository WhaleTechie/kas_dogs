import os
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from kas_config import BOT_TOKEN
from bot.recognition import get_dog_by_photo

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

def get_main_menu_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("🔍 Identify a Dog", callback_data="identify"),
        InlineKeyboardButton("🐶 View Catalog", callback_data="catalog"),
        InlineKeyboardButton("☕ Support the Project", url="https://t.me/kasdogs/6")
    )
    return keyboard

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.reply(
        "👋 Hello! I'm *KAS Dogs Bot* — your dog recognition assistant 🐾\n\n"
        "📸 Send a photo of a dog to get information,\n"
        "or choose an option below:",
        reply_markup=get_main_menu_keyboard(),
        parse_mode="Markdown"
    )

def get_categories():
    conn = sqlite3.connect("db/dogs.db")
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT category FROM dogs WHERE category IS NOT NULL")
    results = cur.fetchall()
    conn.close()
    return [r[0] for r in results]

@dp.callback_query_handler(lambda c: c.data == 'catalog')
async def handle_catalog_callback(callback_query: types.CallbackQuery):
    categories = get_categories()
    if not categories:
        await bot.send_message(callback_query.from_user.id, "📭 No categories available.")
        return

    keyboard = InlineKeyboardMarkup(row_width=2)
    for cat in categories:
        keyboard.add(InlineKeyboardButton(cat, callback_data=f"category_{cat}"))
    keyboard.add(InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu"))

    await bot.send_message(callback_query.from_user.id, "📂 Choose a category to view dogs:", reply_markup=keyboard)
    await bot.answer_callback_query(callback_query.id)

@dp.callback_query_handler(lambda c: c.data.startswith("category_"))
async def show_catalog_by_category(callback_query: types.CallbackQuery):
    category = callback_query.data[len("category_"):]  # Extract category name

    conn = sqlite3.connect("db/dogs.db")
    cur = conn.cursor()
    cur.execute(
        "SELECT name, pen, status, description, photo_folder FROM dogs WHERE category = ? ORDER BY pen",
        (category,)
    )
    rows = cur.fetchall()
    conn.close()

    if not rows:
        await bot.send_message(callback_query.from_user.id, f"📭 No dogs found in *{category}*.", parse_mode="Markdown")
        await bot.answer_callback_query(callback_query.id)
        return

    current_pen = None
    for name, pen, status, desc, folder in rows:
        pen = pen or "Unassigned"

        if pen != current_pen:
            await bot.send_message(callback_query.from_user.id, f"📦 *Pen: {pen}*", parse_mode="Markdown")
            current_pen = pen

        text = (
            f"🐶 *{name}*\n"
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

    await bot.send_message(callback_query.from_user.id, "⬇️ Return to menu:", reply_markup=get_main_menu_keyboard())
    await bot.answer_callback_query(callback_query.id)

@dp.message_handler(commands=['catalog'])
async def catalog_command(message: types.Message):
    await handle_catalog_callback(types.CallbackQuery(from_user=message.from_user, data='catalog', id='0', message=message))

@dp.callback_query_handler(lambda c: c.data == 'identify')
async def handle_identify_callback(callback_query: types.CallbackQuery):
    await bot.send_message(callback_query.from_user.id, "📸 Please send a photo of the dog you want to identify.")
    await bot.answer_callback_query(callback_query.id)

@dp.callback_query_handler(lambda c: c.data == 'main_menu')
async def handle_main_menu(callback_query: types.CallbackQuery):
    await bot.send_message(callback_query.from_user.id, "🏠 Main menu:", reply_markup=get_main_menu_keyboard())
    await bot.answer_callback_query(callback_query.id)

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
            if dog.get('photo_path') and os.path.exists(dog['photo_path']):
                with open(dog['photo_path'], 'rb') as p:
                    await bot.send_photo(message.chat.id, photo=p, caption=text, parse_mode="Markdown")
            else:
                await message.reply(text, parse_mode="Markdown")
        else:
            await message.reply("❌ Dog not found in catalog or photo could not be processed.")
    finally:
        await message.reply("⬇️ Return to menu:", reply_markup=get_main_menu_keyboard())
        import gc
        gc.collect()
        try:
            os.remove(file_path)
        except Exception as e:
            print(f"⚠️ Still couldn’t delete file: {e}")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
