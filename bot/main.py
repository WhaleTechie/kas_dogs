import os
import gc
import re
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from aiogram.utils import executor
from kas_config import BOT_TOKEN
from bot.recognition import get_dog_by_photo

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

def escape_md(text):
    return re.sub(r'([_\*\[\]()~`>#+\-=|{}.!])', r'\\\1', str(text))

def clean_text(text):
    return text.encode("utf-16", "surrogatepass").decode("utf-16", "ignore")

user_dog_profiles = {}
user_dog_index = {}

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("🔍 Identify a Dog", callback_data="identify"),
        InlineKeyboardButton("🐶 View Catalog", callback_data="catalog"),
        InlineKeyboardButton("☕ Support the Project", url="https://t.me/kasdogs/6")
    )
    await message.reply(
        clean_text(escape_md("👋 Hello! I'm KAS Dogs Bot — your dog recognition assistant 🐾\n\n"
                             "📸 Send a photo of a dog to get information,\n"
                             "or choose an option below:")),
        reply_markup=keyboard,
        parse_mode="MarkdownV2"
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
    await bot.answer_callback_query(callback_query.id)
    categories = get_categories()
    if not categories:
        await bot.send_message(callback_query.from_user.id, "📍 No categories available.")
        return

    keyboard = InlineKeyboardMarkup(row_width=2)
    for cat in categories:
        keyboard.add(InlineKeyboardButton(cat, callback_data=f"category_{cat}"))
    keyboard.add(InlineKeyboardButton("🔙 Main Menu", callback_data="start_over"))
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

        await bot.send_message(callback_query.from_user.id, clean_text(f"🏠 Select a sector in *{escape_md(category)}*:"), reply_markup=keyboard, parse_mode="MarkdownV2")
    else:
        await show_dogs_by_filters(callback_query, category=category)

@dp.callback_query_handler(lambda c: c.data.startswith("sector_"))
async def handle_sector(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    sector = callback_query.data[len("sector_") :]

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

    await bot.send_message(callback_query.from_user.id, clean_text(f"📦 Select a pen in sector *{escape_md(sector)}*:"), reply_markup=keyboard, parse_mode="MarkdownV2")

@dp.callback_query_handler(lambda c: c.data.startswith("pen_"))
async def handle_pen(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    _, sector, pen = callback_query.data.split("_", 2)
    await show_dogs_by_filters(callback_query, category="shelter", sector=sector, pen=pen)

@dp.callback_query_handler(lambda c: c.data.startswith("show_profile_"))
async def show_next_profile(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    user_id = callback_query.from_user.id
    idx = int(callback_query.data.split("_")[-1])
    profiles = user_dog_profiles.get(user_id, [])

    if idx < len(profiles):
        text, photo_path, photo_list, location = profiles[idx]
        keyboard = InlineKeyboardMarkup()
        if photo_list:
            keyboard.add(InlineKeyboardButton("📷 More Photos", callback_data=f"more_photos_{idx}"))

        remaining = len(profiles) - idx - 1
        if remaining:
            keyboard.add(InlineKeyboardButton(f"📄 View another dog ({remaining} left)", callback_data=f"show_profile_{idx+1}"))

        keyboard.add(InlineKeyboardButton("🔙 Back to Menu", callback_data="start_over"))

        if photo_path and os.path.exists(photo_path):
            with open(photo_path, 'rb') as p:
                await bot.send_photo(callback_query.from_user.id, photo=p, caption=clean_text(text), parse_mode="MarkdownV2", reply_markup=keyboard)
        else:
            await bot.send_message(callback_query.from_user.id, clean_text(text), parse_mode="MarkdownV2", reply_markup=keyboard)

@dp.callback_query_handler(lambda c: c.data.startswith("more_photos_"))
async def show_more_photos(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    wait_msg = await bot.send_message(callback_query.from_user.id, "⏳ Please wait...")

    user_id = callback_query.from_user.id
    idx = int(callback_query.data.split("_")[-1])
    profiles = user_dog_profiles.get(user_id, [])

    if idx < len(profiles):
        _, _, photo_list, _ = profiles[idx]
        if photo_list:
            media = [InputMediaPhoto(types.InputFile(path)) for path in photo_list[:10]]
            await bot.send_media_group(callback_query.from_user.id, media=media)

    await wait_msg.delete()
    keyboard = InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 Back to Menu", callback_data="start_over"))
    await bot.send_message(callback_query.from_user.id, "✅ Done showing photos.", reply_markup=keyboard)

async def show_dogs_by_filters(callback_query, category=None, sector=None, pen=None):
    wait_msg = await bot.send_message(callback_query.from_user.id, "⏳ Please wait...")

    conn = sqlite3.connect("db/dogs.db")
    cur = conn.cursor()
    query = "SELECT name, pen, sector, status, description, photo_folder FROM dogs WHERE category = ?"
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

    media_group = []
    profiles = []
    location_key = f"{sector or ''}_{pen or ''}".strip("_")

    for idx, (name, pen, sector, status, desc, folder) in enumerate(rows):
        photo_path = None
        photo_list = []
        if folder and os.path.isdir(folder):
            images = [f for f in os.listdir(folder) if f.lower().endswith((".jpg", ".jpeg", ".png"))]
            photo_list = [os.path.join(folder, img) for img in images]
            if images:
                photo_path = os.path.join(folder, images[0])
                media_group.append(InputMediaPhoto(types.InputFile(photo_path)))

        text = (
            f"🐶 *{escape_md(name)}*\n"
            f"📂 {escape_md(category)}\n"
            f"📍 {escape_md(pen or sector or 'N/A')}\n"
            f"📋 Status: {escape_md(status or 'N/A')}\n"
            f"📜 {escape_md(desc or 'No description yet')}"
        )
        profiles.append((text, photo_path, photo_list, location_key))

    user_dog_profiles[callback_query.from_user.id] = profiles
    user_dog_index[callback_query.from_user.id] = 0

    for i in range(0, len(media_group), 10):
        await bot.send_media_group(callback_query.from_user.id, media=media_group[i:i+10])

    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("📋 View Dog Profiles", callback_data="show_profile_0"))
    keyboard.add(InlineKeyboardButton("🔙 Main Menu", callback_data="start_over"))
    await bot.send_message(callback_query.from_user.id, "✅ Dogs shown in groups. What would you like next?", reply_markup=keyboard)

    await wait_msg.delete()

@dp.callback_query_handler(lambda c: c.data == "start_over")
async def return_to_main(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    await start(callback_query.message)

@dp.callback_query_handler(lambda c: c.data == 'identify')
async def handle_identify_callback(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(callback_query.from_user.id, "📸 Please send a photo of the dog you want to identify.")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
