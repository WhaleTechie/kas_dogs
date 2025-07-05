import os
import gc
import re
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
from kas_config import BOT_TOKEN
from bot.recognition import get_dog_by_photo

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

def escape_md(text):
    return re.sub(r'([_\*\[\]()~`>#+\-=|{}.!])', r'\\\1', str(text))

# --- MAIN MENU ---
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("🔍 Identify a Dog", callback_data="identify"),
        InlineKeyboardButton("🐶 View Catalog", callback_data="catalog"),
        InlineKeyboardButton("☕ Support the Project", url="https://t.me/kasdogs/6")
    )
    await message.reply(
        escape_md("👋 Hello! I'm KAS Dogs Bot — your dog recognition assistant 🐾\n\n"
                  "📸 Send a photo of a dog to get information,\n"
                  "or choose an option below:"),
        reply_markup=keyboard,
        parse_mode="MarkdownV2"
    )

# --- GET CATEGORIES ---
def get_categories():
    conn = sqlite3.connect("db/dogs.db")
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT category FROM dogs WHERE category IS NOT NULL")
    results = cur.fetchall()
    conn.close()
    return [r[0] for r in results]

# --- VIEW CATALOG ---
@dp.callback_query_handler(lambda c: c.data == 'catalog')
async def handle_catalog_callback(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    categories = get_categories()
    if not categories:
        await bot.send_message(callback_query.from_user.id, "📍 No categories available.")
        return

    keyboard = InlineKeyboardMarkup(row_width=2)
    for cat in categories:
        keyboard.add(InlineKeyboardButton(cat, callback_data=f"category_{cat}"))
    keyboard.add(InlineKeyboardButton("🔙 Back to Menu", callback_data="start_over"))
    await bot.send_message(
        callback_query.from_user.id,
        "📂 Choose a category to view dogs:",
        reply_markup=keyboard
    )

@dp.callback_query_handler(lambda c: c.data.startswith("category_"))
async def handle_category(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    category = callback_query.data[len("category_") :]

    if category.lower() == "shelter":
        conn = sqlite3.connect("db/dogs.db")
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT sector FROM dogs WHERE category = ? AND sector IS NOT NULL", (category,))
        sectors = [row[0] for row in cur.fetchall()]
        conn.close()

        keyboard = InlineKeyboardMarkup(row_width=2)
        for sector in sectors:
            keyboard.add(InlineKeyboardButton(f"{sector}", callback_data=f"sector_{sector}"))
        keyboard.add(InlineKeyboardButton("🔙 Back to Catalog", callback_data="catalog"))

        await bot.send_message(callback_query.from_user.id, escape_md(f"🏠 Select a sector in {category}:") , reply_markup=keyboard, parse_mode="MarkdownV2")
    else:
        await show_dogs_by_filters(callback_query, category=category)

@dp.callback_query_handler(lambda c: c.data.startswith("sector_"))
async def handle_sector(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    sector = callback_query.data[len("sector_" ):]

    conn = sqlite3.connect("db/dogs.db")
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT pen FROM dogs WHERE category = 'shelter' AND sector = ? AND pen IS NOT NULL", (sector,))
    pens = [row[0] for row in cur.fetchall()]
    conn.close()

    if not pens or len(pens) == 1:
        pen = pens[0] if pens else None
        await show_dogs_by_filters(callback_query, category="shelter", sector=sector, pen=pen)
        return

    keyboard = InlineKeyboardMarkup(row_width=2)
    for pen in pens:
        keyboard.add(InlineKeyboardButton(f"{pen}", callback_data=f"pen_{sector}_{pen}"))
    keyboard.add(InlineKeyboardButton("🔙 Back to Sectors", callback_data="category_shelter"))

    await bot.send_message(callback_query.from_user.id, escape_md(f"📦 Select a pen in sector {sector}:") , reply_markup=keyboard, parse_mode="MarkdownV2")

@dp.callback_query_handler(lambda c: c.data.startswith("pen_"))
async def handle_pen(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    _, sector, pen = callback_query.data.split("_", 2)
    await show_dogs_by_filters(callback_query, category="shelter", sector=sector, pen=pen)

async def show_dogs_by_filters(callback_query, category=None, sector=None, pen=None):
    conn = sqlite3.connect("db/dogs.db")
    cur = conn.cursor()
    query = "SELECT name, pen, status, description, photo_folder FROM dogs WHERE category = ?"
    params = [category]
    if sector:
        query += " AND sector = ?"
        params.append(sector)
    if pen:
        query += " AND pen = ?"
        params.append(pen)
    cur.execute(query, tuple(params))
    rows = cur.fetchall()
    conn.close()

    if not rows:
        await bot.send_message(callback_query.from_user.id, "📕 No dogs found.")
        return

    for name, pen, status, desc, folder in rows:
        text = escape_md(
            f"🐶 {name}\n"
            f"📂 Category: {category}\n"
            f"📍 Pen: {pen or 'N/A'}\n"
            f"📋 Status: {status or 'N/A'}\n"
            f"📜 {desc or 'No description yet'}"
        )
        if folder and os.path.isdir(folder):
            images = [f for f in os.listdir(folder) if f.lower().endswith((".jpg", ".jpeg", ".png"))]
            if images:
                photo_path = os.path.join(folder, images[0])
                with open(photo_path, 'rb') as p:
                    await bot.send_photo(callback_query.from_user.id, photo=p, caption=text, parse_mode="MarkdownV2")
                continue
        await bot.send_message(callback_query.from_user.id, text, parse_mode="MarkdownV2")

    keyboard = InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 Main Menu", callback_data="start_over"))
    await bot.send_message(callback_query.from_user.id, "📋 Done showing dogs.", reply_markup=keyboard)

@dp.callback_query_handler(lambda c: c.data == "start_over")
async def return_to_main(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    await start(callback_query.message)

@dp.message_handler(commands=['catalog'])
async def catalog_command(message: types.Message):
    categories = get_categories()
    keyboard = InlineKeyboardMarkup(row_width=2)
    for cat in categories:
        keyboard.add(InlineKeyboardButton(cat, callback_data=f"category_{cat}"))
    keyboard.add(InlineKeyboardButton("🔙 Back to Menu", callback_data="start_over"))
    await message.reply("📂 Choose a category to view dogs:", reply_markup=keyboard)

@dp.message_handler(content_types=['photo'])
async def handle_photo(message: types.Message):
    photo = message.photo[-1]
    file_path = f"photos/{photo.file_id}.jpg"
    await photo.download(destination_file=file_path)

    dog = None
    try:
        dog = get_dog_by_photo(file_path)
    except Exception as e:
        print(f"⚠️ Error during recognition: {e}")

    try:
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("🔙 Back to Main Menu", callback_data="start_over"))

        if dog:
            category = (dog.get('category') or '').strip().lower()
            pen = (dog.get('pen') or '').strip()
            sector = (dog.get('sector') or '').strip()

            if category == 'street':
                location = escape_md("📍 Streets of Kaş")
            else:
                if pen and sector:
                    location = escape_md(f"📍 Pen {pen}, Sector {sector} in the Shelter")
                elif pen:
                    location = escape_md(f"📍 Pen {pen}, in the Shelter")
                elif sector:
                    location = escape_md(f"📍 Sector {sector} in the Shelter")
                else:
                    location = escape_md("📍 In the Shelter (location unknown)")

            text = escape_md(f"🐶 {dog['name']}\n") + location + "\n" + \
                   escape_md(f"📋 Status: {dog['status'] or 'N/A'}\n📜 {dog['description'] or 'No description yet'}")

            if dog.get('photo_path') and os.path.exists(dog['photo_path']):
                with open(dog['photo_path'], 'rb') as p:
                    await bot.send_photo(
                        chat_id=message.chat.id,
                        photo=p,
                        caption=text,
                        reply_markup=keyboard,
                        parse_mode="MarkdownV2",
                    )
            else:
                await message.reply(text, reply_markup=keyboard, parse_mode="MarkdownV2")
        else:
            await message.reply("❌ Dog not found in catalog or photo could not be processed.", reply_markup=keyboard)

    finally:
        gc.collect()
        try:
            os.remove(file_path)
        except Exception as e:
            print(f"⚠️ Still couldn’t delete file: {e}")

@dp.callback_query_handler(lambda c: c.data == 'identify')
async def handle_identify_callback(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(callback_query.from_user.id, "📸 Please send a photo of the dog you want to identify.")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
