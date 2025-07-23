import os
import gc
import re
import sqlite3
import uuid
import tempfile
import requests
from bot.utils import escape_md  # if you're escaping MarkdownV2
from aiogram import Bot
from bot.utils import create_collage
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from aiogram.utils import executor
from kas_config import BOT_TOKEN
from bot.recognition import get_dog_by_photo
from supabase import create_client, Client

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

def escape_md(text):
    return re.sub(r'([_\*\[\]()~`>#+\-=|{}.!])', r'\\\1', str(text))

def clean_text(text):
    return text.encode("utf-16", "surrogatepass").decode("utf-16", "ignore")

recognized_dog_photos = {}
user_dog_profiles = {}
user_dog_index = {}

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

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
    try:
        response = supabase.table("dogs").select("category").neq("category", None).execute()
        rows = response.data
        categories = list({row["category"] for row in rows if row["category"]})
        return categories
    except Exception as e:
        print(f"Error fetching categories: {e}")
        return []

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
        response = supabase.table("dogs") \
            .select("sector") \
            .eq("category", category) \
            .neq("sector", None) \
            .execute()

        sectors = list({row["sector"] for row in response.data}) if response.data else []

        keyboard = InlineKeyboardMarkup(row_width=2)
        for sector in sectors:
            keyboard.add(InlineKeyboardButton(f"{sector}", callback_data=f"sector_{sector}"))
        keyboard.add(InlineKeyboardButton("🔙 Back to Catalog", callback_data="catalog"))

        await bot.send_message(
            callback_query.from_user.id,
            clean_text(f"🏠 Select a sector in *{escape_md(category)}*:"), 
            reply_markup=keyboard, 
            parse_mode="MarkdownV2"
        )
    else:
        await show_dogs_by_filters(callback_query, category=category)

@dp.callback_query_handler(lambda c: c.data.startswith("sector_"))
async def handle_sector(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    sector = callback_query.data[len("sector_") :]

    response = supabase.table("dogs") \
        .select("pen") \
        .eq("category", "shelter") \
        .eq("sector", sector) \
        .neq("pen", None) \
        .execute()

    pens = list({row["pen"] for row in response.data}) if response.data else []

    if not pens or len(pens) == 1:
        pen = pens[0] if pens else None
        await show_dogs_by_filters(callback_query, category="shelter", sector=sector, pen=pen)
        return

    keyboard = InlineKeyboardMarkup(row_width=2)
    for pen in pens:
        keyboard.add(InlineKeyboardButton(f"{pen}", callback_data=f"pen_{sector}_{pen}"))
    keyboard.add(InlineKeyboardButton("🔙 Back to Sectors", callback_data="category_shelter"))

    await bot.send_message(
        callback_query.from_user.id,
        clean_text(f"📦 Select a pen in sector *{escape_md(sector)}*:"),
        reply_markup=keyboard,
        parse_mode="MarkdownV2"
    )

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
        text, dog_id, photo_filenames, location = profiles[idx]  # dog_id matches your DB id

        keyboard = InlineKeyboardMarkup()
        if photo_filenames and len(photo_filenames) > 1:
            keyboard.add(InlineKeyboardButton("📷 More Photos", callback_data=f"more_photos_{idx}"))

        remaining = len(profiles) - idx - 1
        if remaining:
            keyboard.add(InlineKeyboardButton(f"📄 View another dog ({remaining} left)", callback_data=f"show_profile_{idx+1}"))

        keyboard.add(InlineKeyboardButton("🔙 Back to Menu", callback_data="start_over"))

        if photo_filenames:
            first_filename = photo_filenames[0]
            result = supabase.storage.from_('kas.dogs').get_public_url(f"{dog_id}/{first_filename}")
            first_photo_url = result.get("publicURL") if isinstance(result, dict) else result

            if first_photo_url and first_photo_url.lower().endswith(('.jpg', '.jpeg', '.png')):
                await bot.send_photo(
                    callback_query.from_user.id,
                    photo=first_photo_url,
                    caption=clean_text(text),
                    parse_mode="MarkdownV2",
                    reply_markup=keyboard
                )
            else:
                print(f"[WARNING] Invalid image URL for dog {dog_id}: {first_photo_url}")
                await bot.send_message(
                    callback_query.from_user.id,
                    clean_text(text),
                    parse_mode="MarkdownV2",
                    reply_markup=keyboard
                )
    else:
        await bot.send_message(
            callback_query.from_user.id,
            clean_text(text),
            parse_mode="MarkdownV2",
            reply_markup=keyboard
        )

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

import os
import tempfile
import requests
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.utils import create_collage
from bot.utils import escape_md  # if you're escaping MarkdownV2
from aiogram import Bot

async def show_dogs_by_filters(callback_query, category=None, sector=None, pen=None):
    wait_msg = await bot.send_message(callback_query.from_user.id, "⏳ Please wait...")

    response = supabase.table("dogs").select(
        "id, name, pen, sector, status, description, photo_folder"
    ).eq("category", category)

    if sector:
        response = response.eq("sector", sector)
    if pen:
        response = response.eq("pen", pen)

    data = response.execute()

    if (hasattr(data, 'error') and data.error) or data.data is None:
        await bot.send_message(callback_query.from_user.id, "❌ Error fetching dogs data.")
        await wait_msg.delete()
        return

    rows = data.data
    if not rows:
        await bot.send_message(callback_query.from_user.id, "📕 No dogs found.")
        await wait_msg.delete()
        return

    profiles = []
    collage_input = []

    for dog in rows:
        dog_id = dog['id']
        name = dog['name']
        pen_ = dog.get('pen')
        sector_ = dog.get('sector')
        status = dog.get('status')
        desc = dog.get('description')

        photos_response = supabase.storage.from_('kas.dogs').list(dog_id, {"limit": 100})
        photo_list = []
        if photos_response:
            photo_filenames = [
                file['name'] for file in photos_response
                if file['name'].lower().endswith(('.jpg', '.jpeg', '.png'))
            ]
            if photo_filenames:
                photo_list = photo_filenames
        if not photo_list:
            continue

        # Download the first photo
        filename = photo_list[0]
        res = supabase.storage.from_('kas.dogs').get_public_url(f"{dog_id}/{filename}")
        url = res.get("publicURL") if isinstance(res, dict) else res
        if url:
            try:
                img_data = requests.get(url).content
                temp_img_path = os.path.join(tempfile.gettempdir(), f"{dog_id}_{filename}")
                with open(temp_img_path, "wb") as f:
                    f.write(img_data)
                clean_name = name.split('\n')[0]  # just first line, or
                clean_name = name.replace('\n', ' ')  # remove newlines
                collage_input.append((temp_img_path, clean_name))

            except Exception as e:
                print(f"[ERROR] Downloading image {filename}: {e}")

        # Save profile info for future use (pagination etc.)
        text = (
            f"🐶 *{escape_md(name)}*\n"
            f"📂 {escape_md(category)}\n"
            f"📍 {escape_md(str(pen_ or sector_ or 'N/A'))}\n"
            f"📋 Status: {escape_md(status or 'N/A')}\n"
            f"📜 {escape_md(desc or 'No description yet')}"
        )
        profiles.append((text, dog_id, photo_list, f"{sector or ''}_{pen or ''}".strip("_")))

    if collage_input:
        collage_path = create_collage(collage_input, collage_name="Filtered_Dogs", cell_size=(300, 300), cols=2)
        if collage_path:
            with open(collage_path, "rb") as file:
                await bot.send_photo(callback_query.from_user.id, photo=file, caption="🐶 Dogs found:")
            os.remove(collage_path)

        # Cleanup temp images
        for path, _ in collage_input:
            if os.path.exists(path):
                os.remove(path)
    else:
        await bot.send_message(callback_query.from_user.id, "❌ No valid dog photos found.")

    # Store for navigation
    user_dog_profiles[callback_query.from_user.id] = profiles
    user_dog_index[callback_query.from_user.id] = 0

    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("📋 View Dog Profiles", callback_data="show_profile_0"))
    keyboard.add(InlineKeyboardButton("🔙 Main Menu", callback_data="start_over"))
    await bot.send_message(callback_query.from_user.id, "✅ Dogs shown in collage. What next?", reply_markup=keyboard)

    await wait_msg.delete()

@dp.callback_query_handler(lambda c: c.data == "start_over")
async def return_to_main(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    await start(callback_query.message)

@dp.callback_query_handler(lambda c: c.data == 'identify')
async def handle_identify_callback(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(callback_query.from_user.id, "📸 Please send a photo of the dog you want to identify.")

@dp.message_handler(content_types=types.ContentType.PHOTO)
async def handle_photo(message: types.Message):
    wait_msg = await message.reply("⏳ Analyzing the photo...")

    photo = message.photo[-1]
    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, f"dog_{uuid.uuid4().hex}.jpg")

    try:
        await photo.download(destination_file=temp_path)
        dog = get_dog_by_photo(temp_path)

        if dog:
            text = (
                f"🐶 *{escape_md(dog['name'])}*\n"
                f"📂 {escape_md(dog['category'])}\n"
                f"📍 {escape_md(dog['pen'] or dog['sector'] or 'N/A')}\n"
                f"📋 Status: {escape_md(dog['status'] or 'N/A')}\n"
                f"📜 {escape_md(dog['description'] or 'No description yet')}"
            )

            keyboard = InlineKeyboardMarkup()
            if dog["photo_path"] and os.path.exists(dog["photo_path"]):
                folder = os.path.dirname(dog["photo_path"])
                photos = [os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith((".jpg", ".jpeg", ".png"))]
                recognized_dog_photos[message.from_user.id] = photos
                if len(photos) > 1:
                    keyboard.add(InlineKeyboardButton("📷 View More Photos", callback_data="more_rec_photos"))

                with open(dog["photo_path"], "rb") as p:
                    keyboard.add(InlineKeyboardButton("🔙 Back to Menu", callback_data="start_over"))
                    await message.reply_photo(
                        photo=p,
                        caption=clean_text(text),
                        parse_mode="MarkdownV2",
                        reply_markup=keyboard
                    )
            else:
                await message.reply(
                    clean_text(text),
                    parse_mode="MarkdownV2",
                    reply_markup=InlineKeyboardMarkup().add(
                        InlineKeyboardButton("🔙 Back to Menu", callback_data="start_over")
                    )
                )
        else:
            await message.reply("🐾 Sorry, I couldn't recognize this dog.")
    except Exception as e:
        await message.reply("❌ Error processing the photo.")
        print(f"Recognition error: {e}")
    finally:
        await wait_msg.delete()
        if os.path.exists(temp_path):
            os.remove(temp_path)
        gc.collect()

@dp.callback_query_handler(lambda c: c.data == "more_rec_photos")
async def handle_more_rec_photos(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    wait_msg = await bot.send_message(callback_query.from_user.id, "⏳ Please wait...")

    photos = recognized_dog_photos.get(callback_query.from_user.id)
    if photos:
        media = [InputMediaPhoto(types.InputFile(p)) for p in photos[:10]]
        await bot.send_media_group(callback_query.from_user.id, media=media)

    await wait_msg.delete()
    keyboard = InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 Back to Menu", callback_data="start_over"))
    await bot.send_message(callback_query.from_user.id, "✅ More photos shown.", reply_markup=keyboard)

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
