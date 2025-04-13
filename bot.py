import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.filters import Command
from aiogram.exceptions import TelegramAPIError
import config

# Настройка логирования
logging.basicConfig(level=logging.INFO, filename="bot.log", filemode="a",
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Инициализация бота
bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher()

# Команда /start
@dp.message(Command("start"))
async def start_command(message: types.Message):
    try:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Открыть MemeBot 🎉", web_app=WebAppInfo(url=config.WEBAPP_URL))]
        ])
        await message.answer("Добро пожаловать в MemeBot! Нажми кнопку, чтобы открыть приложение.", reply_markup=keyboard)
    except TelegramAPIError as e:
        logger.error(f"Ошибка Telegram API при обработке /start: {e}")
        await message.answer("Произошла ошибка. Попробуйте позже.")
    except Exception as e:
        logger.error(f"Неизвестная ошибка при обработке /start: {e}")
        await message.answer("Что-то пошло не так. Пожалуйста, попробуйте снова.")

# Обработка ошибок
@dp.errors()
async def error_handler(update, exception):
    logger.error(f"Ошибка при обработке обновления: {exception}")
    return True

# Запуск бота
async def main():
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.critical(f"Критическая ошибка при запуске бота: {e}")
        raise

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())