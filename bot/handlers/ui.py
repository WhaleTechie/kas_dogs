from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.utils.helpers import clean_text, escape_md

def get_main_menu():
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("🔍 Identify a Dog", callback_data="identify"),
        InlineKeyboardButton("🐶 View Catalog", callback_data="catalog"),
        InlineKeyboardButton("☕ Support the Project", url="https://t.me/kasdogs/6")
    )
    text = clean_text(escape_md(
        "👋 Hello! I'm KAS Dogs Bot — your dog recognition assistant 🐾\n\n"
        "📸 Send a photo of a dog to get information,\n"
        "or choose an option below:"
    ))
    return text, keyboard
