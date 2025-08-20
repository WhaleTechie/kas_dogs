# bot/main.py

import os
import gc
import uuid
import tempfile
from PIL import Image
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from aiogram.utils import executor
from aiogram.utils.markdown import escape_md
from kas_config import BOT_TOKEN
from bot.loader import dp, bot
import bot.handlers.catalog
from bot.loader import dp, bot
from bot.recognition import get_dog_by_photo
from bot.utils.helpers import create_collage
from supabase import create_client

# --- Supabase Client ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- Store recognized dog photos per user ---
recognized_dog_photos = {}

# --- Startup ---
async def on_startup(_):
    print("🔄 Deleting webhook and flushing old updates...")
    await bot.delete_webhook(drop_pending_updates=True)

# --- Utility ---
def clean_text(text: str) -> str:
    """Escape text for MarkdownV2."""
    return escape_md(text)

def get_categories():
    try:
        response = supabase.table("dogs").select("category").neq("category", None).execute()
        rows = response.data
        return list({row["category"] for row in rows if row["category"]})
    except Exception as e:
        print(f"Error fetching categories: {e}")
        return []

# --- /start handler ---
@dp.message_handler(commands=['start'])
async def send_main_menu_command(message: types.Message):
    from bot.handlers.ui import get_main_menu
    text, keyboard = get_main_menu()
    await message.reply(text, reply_markup=keyboard, parse_mode="MarkdownV2")

@dp.callback_query_handler(lambda c: c.data == "start_over")
async def back_to_menu(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    from bot.handlers.ui import get_main_menu
    text, keyboard = get_main_menu()
    await bot.send_message(callback_query.from_user.id, text, reply_markup=keyboard, parse_mode="MarkdownV2")

# --- Identify callback ---
@dp.callback_query_handler(lambda c: c.data == 'identify')
async def handle_identify_callback(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(callback_query.from_user.id, "📸 Please send a photo of the dog you want to identify.")

# --- Photo handler ---
@dp.message_handler(content_types=types.ContentType.PHOTO)
async def handle_photo(message: types.Message):
    wait_msg = await message.reply("⏳ Analyzing the photo...")

    photo = message.photo[-1]  # highest resolution
    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, f"dog_{uuid.uuid4().hex}.jpg")

    try:
        await photo.download(destination_file=temp_path)
        match = get_dog_by_photo(temp_path)  # robust, won't crash

        if not match:
            await message.reply("🐾 Sorry, I couldn't recognize this dog.")
        else:
            dog_id = match["id"]
            response = supabase.table("dogs").select("*").eq("id", dog_id).execute()
            dog = response.data[0] if response.data else None

            if dog:
                text = (
                    f"🐶 *{escape_md(dog.get('name') or match['name'])}*\n"
                    f"📂 {escape_md(dog.get('category') or match['category'])}\n"
                    f"📍 {escape_md(dog.get('pen') or dog.get('sector') or 'N/A')}\n"
                    f"📋 Status: {escape_md(dog.get('status') or 'N/A')}\n"
                    f"📜 {escape_md(dog.get('description') or 'No description yet')}"
                )

                storage_files = supabase.storage.from_("kas.dogs").list(dog_id)
                photos = [
                    supabase.storage.from_("kas.dogs").get_public_url(f"{dog_id}/{f['name']}").public_url
                    for f in storage_files
                    if f['name'].lower().endswith((".jpg", ".jpeg", ".png"))
                ]

                keyboard = InlineKeyboardMarkup().add(
                    InlineKeyboardButton("🔙 Back to Menu", callback_data="start_over")
                )

                if photos:
                    await message.reply_photo(
                        photo=photos[0],
                        caption=clean_text(text),
                        parse_mode="MarkdownV2",
                        reply_markup=keyboard
                    )
                    recognized_dog_photos[message.from_user.id] = photos
                else:
                    await message.reply(
                        clean_text(text),
                        parse_mode="MarkdownV2",
                        reply_markup=keyboard
                    )
            else:
                await message.reply("🐾 Sorry, I couldn't find this dog in the database.")

    except Exception as e:
        await message.reply("❌ Error processing the photo.")
        print(f"Recognition error: {e}")
    finally:
        await wait_msg.delete()
        if os.path.exists(temp_path):
            os.remove(temp_path)
        gc.collect()

# --- More recognized photos ---
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

# --- Run bot ---
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
