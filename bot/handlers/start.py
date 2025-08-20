# bot/handlers/start.py

from aiogram import types
from aiogram.types import InlineKeyboardMarkup
from bot.loader import dp, bot
from bot.handlers.ui import get_main_menu

@dp.message_handler(commands=['start'])
async def send_main_menu_command(message: types.Message):
    text, keyboard = get_main_menu()
    await message.reply(text, reply_markup=keyboard, parse_mode="MarkdownV2")

@dp.callback_query_handler(lambda c: c.data == "start_over")  # match main.py button
async def back_to_menu(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    text, keyboard = get_main_menu()
    await bot.send_message(callback_query.from_user.id, text, reply_markup=keyboard, parse_mode="MarkdownV2")
