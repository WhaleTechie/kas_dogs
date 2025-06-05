from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from kas_config import BOT_TOKEN

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.reply("Hello from KAS Dogs 🐾\nSend me a photo of a dog!")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
