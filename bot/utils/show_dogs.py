import os
import requests
import tempfile
from aiogram import types
from bot.loader import bot, dp
from bot.utils.helpers import escape_md, clean_text, create_collage
from PIL import Image
from bot.db import supabase
from bot.state import user_dog_profiles, user_dog_index
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from PIL import Image, ImageDraw, ImageFont


def create_placeholder_image(text, size=(350, 300)):
    # Create a blank white image
    img = Image.new("RGB", size, color="white")
    draw = ImageDraw.Draw(img)
    font_size = 30
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except:
        font = ImageFont.load_default()

    # Draw "No photo" text centered near the top
    no_photo_text = "No photo"
    bbox = draw.textbbox((0, 0), no_photo_text, font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((size[0] - w) / 2, size[1] // 4 - h // 2), no_photo_text, fill="gray", font=font)

    # Save to temp file and return path
    temp_path = os.path.join(tempfile.gettempdir(), f"placeholder_{text.replace(' ', '_')}.jpg")
    img.save(temp_path)
    return temp_path
async def get_dog_by_id(dog_id):
    try:
        response = supabase.table("dogs").select("*").eq("id", dog_id).single().execute()
        if response:
            return response.data
        else:
            return None
    except Exception as e:
        print(f"Error fetching dog by ID {dog_id}: {e}")
        return None

async def show_dogs_by_filters(callback_query, category=None, sector=None, pen=None):
    wait_msg = await bot.send_message(callback_query.from_user.id, "⏳ Please wait...")

    response = supabase.table("dogs").select(
        "id, name, pen, sector, status, description"
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

        photos_response = supabase.storage.from_('kas.dogs').list(str(dog_id), {"limit": 100})
        photo_list = []
        if photos_response:
            photo_filenames = [
                file['name'] for file in photos_response
                if file['name'].lower().endswith(('.jpg', '.jpeg', '.png'))
            ]
            if photo_filenames:
                photo_list = photo_filenames

        if photo_list:
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
                    clean_name = name.replace('\n', ' ')  # remove newlines
                    collage_input.append((temp_img_path, clean_name))

                except Exception as e:
                    print(f"[ERROR] Downloading image {filename}: {e}")

        else:
            # No photos found - create placeholder image with dog name
            placeholder_path = create_placeholder_image(name)
            collage_input.append((placeholder_path, name.replace('\n', ' ')))

        # Save profile info for future use (pagination etc.)
        text = (
            f"🐶 *{escape_md(name)}*\n"
            f"📂 {escape_md(category or 'N/A')}\n"
            f"📍 {escape_md(str(pen_ or sector_ or 'N/A'))}\n"
            f"📋 Status: {escape_md(status or 'N/A')}\n"
            f"📜 {escape_md(desc or 'No description yet')}"
        )
        profiles.append((text, dog_id, photo_list, f"{sector or ''}_{pen or ''}".strip("_")))

    # Send number of dogs and filter info before the collage
    filter_text = []
    if category:
        filter_text.append(f"{category}")
    if sector:
        filter_text.append(f" {sector}")
    if pen:
        filter_text.append(f"  {pen}")
    filter_summary = "=> ".join(filter_text) if filter_text else "All dogs"

    await bot.send_message(
        callback_query.from_user.id,
        f"🐾 {len(rows)} dog{'s' if len(rows) != 1 else ''} filtered by {filter_summary}."
    )

    if collage_input:
        collage_path = create_collage(collage_input, collage_name="Filtered_Dogs", cell_size=(350, 300), cols=2)
        if collage_path:
            with open(collage_path, "rb") as file:
                await bot.send_photo(callback_query.from_user.id, photo=file, )
            os.remove(collage_path)

        # Cleanup temp images
        for path, _ in collage_input:
            if os.path.exists(path):
                os.remove(path)
    else:
        await bot.send_message(callback_query.from_user.id, "❌ No valid dog photos or placeholders found.")

    # Store for navigation
    user_dog_profiles[callback_query.from_user.id] = profiles
    user_dog_index[callback_query.from_user.id] = 0

    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("📋 View Dog Profiles", callback_data="show_profile_"))
    keyboard.add(InlineKeyboardButton("🔙 Main Menu", callback_data="back_to_menu"))
    await bot.send_message(callback_query.from_user.id, "✅ Dogs shown in collage. What next?", reply_markup=keyboard)

    await wait_msg.delete()
