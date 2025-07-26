import os
import gc
import re
import uuid
import tempfile
from bot.utils.helpers import escape_md
from bot.utils.helpers import create_collage
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from aiogram.utils import executor
from kas_config import BOT_TOKEN
from bot.recognition import get_dog_by_photo
from supabase import create_client, Client
from PIL import Image, ImageDraw, ImageFont
from bot.loader import dp, bot
from bot.db import supabase
from bot import handlers
from bot.state import recognized_dog_photos


async def on_startup(_):
    print("🔄 Deleting webhook and flushing old updates...")
    await bot.delete_webhook(drop_pending_updates=True)


def get_categories():
    try:
        response = supabase.table("dogs").select("category").neq("category", None).execute()
        rows = response.data
        categories = list({row["category"] for row in rows if row["category"]})
        return categories
    except Exception as e:
        print(f"Error fetching categories: {e}")
        return []


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
