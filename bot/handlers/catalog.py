import re
import requests
import os
import tempfile
from aiogram import types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import InputMediaPhoto
from bot.loader import dp, bot               
from bot.utils.helpers import clean_text, escape_md  
from bot.db import supabase              
from bot.main import get_categories     
from bot.utils.show_dogs import show_dogs_by_filters
from bot.utils.helpers import create_collage
from bot.state import user_dog_profiles, user_dog_index, profile_cache, recognized_dog_photos
from bot.utils.helpers import create_placeholder_image
from bot.handlers.start import back_to_menu
from bot.utils.show_dogs import get_dog_by_id
from PIL import Image
import aiohttp
from io import BytesIO

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
    keyboard.add(InlineKeyboardButton("🔙 Main Menu", callback_data="back_to_menu"))
    await bot.send_message(
        callback_query.from_user.id,
        "📂 Choose a category to view dogs:",
        reply_markup=keyboard
    )

@dp.callback_query_handler(lambda c: c.data.startswith("category_"))
async def handle_category(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    category = callback_query.data[len("category_"):]

    if category.lower() == "shelter":
        # 🖼️ Step 1: Fetch and send shelter plan image from Supabase
        try:
            # Adjust the path if you placed it in a subfolder (e.g., 'maps/shelter_plan.jpg')
            res = supabase.storage.from_('kas.dogs').get_public_url("Shelter_plan.jpg")
            image_url = res.get("publicURL") if isinstance(res, dict) else res

            if image_url:
                caption_text = escape_md("🗺️ Shelter Plan\nUse this map to find the sector you're interested in.")

                await bot.send_photo(
                    chat_id=callback_query.from_user.id,
                    photo=image_url,
                    caption=caption_text,
                    parse_mode="MarkdownV2"
                )

            else:
                await bot.send_message(callback_query.from_user.id, "⚠️ Shelter plan image not found.")
        except Exception as e:
            print(f"[ERROR] Failed to load shelter plan from Supabase: {e}")
            await bot.send_message(callback_query.from_user.id, "⚠️ Shelter plan not available.")

        # Step 2: Fetch and display sector list
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

    def natural_sort_key(s):
        return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]

    pens = sorted({row["pen"] for row in response.data}, key=natural_sort_key) if response.data else []

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

@dp.callback_query_handler(lambda c: c.data == "show_profile_")
async def show_filtered_profiles(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    filtered_profiles = user_dog_profiles.get(user_id, [])

    if not filtered_profiles:
        await callback_query.answer("No profiles found.", show_alert=True)
        return

    keyboard = InlineKeyboardMarkup(row_width=2)

    for text, dog_id, photo_list, filter_key in filtered_profiles:
        first_line = text.split("\n")[0]
        dog_name_match = re.match(r"🐶 \*(.*)\*", first_line)
        
        # 🛠️ Updated logic to handle unnamed dogs
        raw_name = dog_name_match.group(1).strip() if dog_name_match else ""
        dog_name = raw_name if raw_name else "** unnamed**"
        
        keyboard.insert(InlineKeyboardButton(dog_name, callback_data=f"dog_{dog_id}"))

    await callback_query.message.edit_text(
        "🐾 Choose a dog to view its profile:",
        reply_markup=keyboard
    )

@dp.callback_query_handler(lambda c: c.data.startswith("dog_"))
async def show_dog_profile_handler(callback_query: types.CallbackQuery):
    dog_id = callback_query.data.split("_")[1]
    dog = await get_dog_by_id(dog_id)  

    if not dog:
        await callback_query.answer("Dog not found.", show_alert=True)
        return

    profile_kb = InlineKeyboardMarkup(row_width=2)
    profile_kb.insert(InlineKeyboardButton(text="📸 Show More Photos", callback_data=f"more_photos_{dog_id}"))
    profile_kb.insert(InlineKeyboardButton(text="🏠 Back to Menu", callback_data="back_to_menu"))

    wait_message = await bot.send_message(callback_query.from_user.id, "Please wait...")

    text = (
        f"🐶 *{escape_md(dog['name'])}*\n"
        f"📂 {escape_md(dog.get('category', 'N/A'))}\n"
        f"📍 {escape_md(str(dog.get('pen') or dog.get('sector') or 'N/A'))}\n"
        f"📋 Status: {escape_md(dog.get('status', 'N/A'))}\n"
        f"📜 {escape_md(dog.get('description', 'No description yet'))}"
    )

    photo_path = None

    photos_response = supabase.storage.from_('kas.dogs').list(str(dog_id), {"limit": 100})
    if photos_response:
        photo_filenames = [
            file['name'] for file in photos_response
            if file['name'].lower().endswith(('.jpg', '.jpeg', '.png'))
        ]
        if photo_filenames:
            first_photo = photo_filenames[0]
            res = supabase.storage.from_('kas.dogs').get_public_url(f"{dog_id}/{first_photo}")
            url = res.get("publicURL") if isinstance(res, dict) else res

            if url:
                try:
                    img_data = requests.get(url, timeout=10).content
                    photo_path = os.path.join(tempfile.gettempdir(), f"{dog_id}_{first_photo}")
                    with open(photo_path, "wb") as f:
                        f.write(img_data)
                except Exception as e:
                    print(f"[ERROR] Downloading image {first_photo}: {e}")

    if not photo_path:
        photo_path = create_placeholder_image(dog['name'])

    if photo_path and os.path.exists(photo_path):
        try:
            with open(photo_path, "rb") as photo_file:
                await bot.send_photo(
                    callback_query.from_user.id,
                    photo=photo_file,
                    caption=text,
                    parse_mode="MarkdownV2",
                    reply_markup=profile_kb
                )
        finally:
            if os.path.exists(photo_path):
                os.remove(photo_path)
    else:
        await bot.send_message(
            callback_query.from_user.id,
            text,
            parse_mode="MarkdownV2",
            reply_markup=profile_kb
        )

    await bot.delete_message(callback_query.from_user.id, wait_message.message_id)
    await callback_query.answer()


@dp.callback_query_handler(lambda c: c.data.startswith("more_photos_"))
async def show_more_photos(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    wait_msg = await bot.send_message(callback_query.from_user.id, "⏳ Please wait...")

    dog_id = callback_query.data.split("_")[2]  # more_photos_<dog_id>

    # Step 1: Get up to 10 filenames from Supabase storage
    try:
        response = supabase.storage.from_('kas.dogs').list(str(dog_id), {"limit": 10})
        photo_filenames = [
            file['name'] for file in response
            if file['name'].lower().endswith(('.jpg', '.jpeg', '.png'))
        ]
    except Exception as e:
        await wait_msg.edit_text("❌ Failed to access Supabase storage.")
        print(f"[Supabase Error] {e}")
        return

    if not photo_filenames:
        await wait_msg.edit_text("⚠️ No photos available for this dog.")
        return

    media = []

    # Step 2: Download and resize each image
    async with aiohttp.ClientSession() as session:
        for filename in photo_filenames[:10]:
            try:
                res = supabase.storage.from_('kas.dogs').get_public_url(f"{dog_id}/{filename}")
                url = res.get("publicURL") if isinstance(res, dict) else res
                if not url:
                    continue

                async with session.get(url) as resp:
                    if resp.status != 200:
                        continue

                    img_bytes = await resp.read()
                    image = Image.open(BytesIO(img_bytes)).convert("RGB")
                    image.thumbnail((400, 400))  # Shrink for fast upload

                    buf = BytesIO()
                    image.save(buf, format="JPEG", quality=80)
                    buf.seek(0)
                    media.append(InputMediaPhoto(media=buf))

            except Exception as e:
                print(f"[Image Error] Failed to process {filename}: {e}")
                continue

    # Step 3: Send photos or fallback message
    if media:
        try:
            await bot.send_media_group(callback_query.from_user.id, media=media)
        except Exception as e:
            print(f"[Telegram Error] Failed to send media group: {e}")
            await bot.send_message(callback_query.from_user.id, "❌ Failed to send images.")
    else:
        await bot.send_message(callback_query.from_user.id, "⚠️ Couldn't load any images.")

    await wait_msg.delete()

    keyboard = InlineKeyboardMarkup().add(
        InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_menu")
    )
    await bot.send_message(callback_query.from_user.id, "✅ Done showing photos.", reply_markup=keyboard)
