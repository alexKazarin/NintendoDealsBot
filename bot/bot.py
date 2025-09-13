import asyncio
import os
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton
from datetime import datetime
from dotenv import load_dotenv

from models.database import get_db
from models.models import User, Game, UserWishlist
from providers.deku_deals_provider import DekuDealsProvider
from .scheduler import price_checker

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize bot and dispatcher
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Initialize price provider
price_provider = DekuDealsProvider()

from .handlers.keyboards import get_main_menu_keyboard
from .handlers import commands, callbacks, messages

# Register command handlers
commands.register_commands(dp)

# Register callback handlers
callbacks.register_callbacks(dp)

# Register message handlers
messages.register_messages(dp)

# Import shared state from commands module
from .handlers.commands import search_results, user_states







async def main():
    """Main function to start the bot"""
    logger.info("Starting Nintendo Deals Bot...")

    # Create database tables
    from models.database import engine
    from models.models import Base
    Base.metadata.create_all(bind=engine)

    # Start polling with error handling for conflicts
    while True:
        try:
            logger.info("Starting bot polling...")
            await dp.start_polling(bot)
            break  # Exit loop if polling succeeds
        except Exception as e:
            logger.error(f"Polling error: {e}")
            if "Conflict" in str(e) or "terminated by other getUpdates" in str(e):
                logger.warning("Conflict detected - another bot instance is running. Waiting before retry...")
                await asyncio.sleep(30)  # Wait 30 seconds before retry
            else:
                logger.error("Non-conflict error, exiting...")
                raise

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
