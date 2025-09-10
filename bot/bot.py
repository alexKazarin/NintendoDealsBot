import os
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import Message
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
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize bot and dispatcher
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Initialize price provider
price_provider = DekuDealsProvider()

# Temporary storage for search results (in production, use Redis or database)
search_results = {}
user_states = {}

@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Handle /start command"""
    user_id = message.from_user.id
    username = message.from_user.username

    # Create or get user
    db = next(get_db())
    user = db.query(User).filter(User.telegram_id == user_id).first()
    if not user:
        user = User(telegram_id=user_id, telegram_username=username)
        db.add(user)
        db.commit()
        db.refresh(user)

    welcome_text = (
        "🎮 <b>Добро пожаловать в Nintendo Deals Bot!</b>\n\n"
        "Я помогу вам отслеживать скидки на игры Nintendo Switch.\n\n"
        "📋 <b>Основные команды:</b>\n"
        "/add <название игры> - добавить игру в виш-лист\n"
        "/list - показать ваш виш-лист\n"
        "/remove <номер> - удалить игру из виш-листа\n"
        "/setthreshold <цена> - установить порог цены для уведомлений\n"
        "/region <регион> - изменить регион (us, eu, jp)\n"
        "/help - показать эту справку\n\n"
        "💎 <b>Премиум возможности:</b>\n"
        "/subscribe - оформить премиум подписку\n"
        "/donate - поддержать проект\n\n"
        f"Ваш ID: {user_id}"
    )

    await message.reply(welcome_text)

@dp.message(Command("help"))
async def cmd_help(message: Message):
    """Handle /help command"""
    help_text = (
        "🎮 <b>Nintendo Deals Bot - Справка</b>\n\n"
        "📋 <b>Команды:</b>\n"
        "/start - начать работу с ботом\n"
        "/add <название игры> - добавить игру в виш-лист\n"
        "/list - показать список отслеживаемых игр\n"
        "/remove <номер> - удалить игру из виш-листа\n"
        "/setthreshold <цена> - установить желаемую цену\n"
        "/region <регион> - изменить регион (us/eu/jp)\n"
        "/subscribe - премиум подписка (до 100 игр)\n"
        "/donate - поддержать разработку\n\n"
        "💡 <b>Как пользоваться:</b>\n"
        "1. Добавьте игру командой /add\n"
        "2. Установите желаемую цену /setthreshold\n"
        "3. Получайте уведомления о скидках!\n\n"
        "🔗 Бесплатно: до 10 игр в виш-листе"
    )

    await message.reply(help_text)

@dp.message(Command("region"))
async def cmd_region(message: Message):
    """Handle /region command"""
    args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    user_id = message.from_user.id

    if not args:
        await message.reply("Укажите регион: /region us|eu|jp")
        return

    region = args[0].lower()
    if region not in ['us', 'eu', 'jp']:
        await message.reply("Неверный регион. Доступные: us, eu, jp")
        return

    db = next(get_db())
    user = db.query(User).filter(User.telegram_id == user_id).first()
    if user:
        user.region = region
        db.commit()
        await message.reply(f"✅ Регион изменен на: {region.upper()}")
    else:
        await message.reply("❌ Пользователь не найден")

@dp.message(Command("subscribe"))
async def cmd_subscribe(message: Message):
    """Handle /subscribe command"""
    user_id = message.from_user.id

    db = next(get_db())
    user = db.query(User).filter(User.telegram_id == user_id).first()

    if user and user.is_premium:
        await message.reply("✅ У вас уже есть премиум подписка!")
        return

    # In MVP, we'll just set premium for demo purposes
    # In production, this would integrate with payment system
    if user:
        user.is_premium = True
        db.commit()
        await message.reply(
            "🎉 <b>Премиум подписка активирована!</b>\n\n"
            "Теперь вы можете отслеживать до 100 игр!\n"
            "Спасибо за поддержку! 💎"
        )
    else:
        await message.reply("❌ Пользователь не найден")

@dp.message(Command("donate"))
async def cmd_donate(message: Message):
    """Handle /donate command"""
    donate_text = (
        "💝 <b>Поддержать проект</b>\n\n"
        "Ваш вклад помогает развивать бота!\n\n"
        "💳 <b>Способы поддержки:</b>\n"
        "• Telegram Stars: отправьте звезды боту\n"
        "• Криптовалюта: скоро добавим\n"
        "• PayPal: ссылка будет позже\n\n"
        "Спасибо за поддержку! 🙏"
    )

    await message.reply(donate_text)

@dp.message(Command("add"))
async def cmd_add(message: Message):
    """Handle /add command - add game to wishlist"""
    args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    user_id = message.from_user.id

    if not args:
        await message.reply("Укажите название игры: /add <название игры>")
        return

    query = " ".join(args)
    db = next(get_db())

    # Get user
    user = db.query(User).filter(User.telegram_id == user_id).first()
    if not user:
        await message.reply("❌ Пользователь не найден. Используйте /start")
        return

    # Check wishlist limit
    wishlist_count = db.query(UserWishlist).filter(UserWishlist.user_id == user.id).count()
    max_games = 100 if user.is_premium else 10

    if wishlist_count >= max_games:
        await message.reply(
            f"❌ Достигнут лимит игр в виш-листе ({max_games}).\n"
            "Оформите премиум подписку командой /subscribe для увеличения лимита до 100 игр."
        )
        return

    # Search for games
    await message.reply("🔍 Ищу игры...")
    games = price_provider.search_games(query, user.region)

    if not games:
        await message.reply("❌ Игры не найдены. Попробуйте другое название.")
        return

    # Show search results
    response = "🎮 <b>Найденные игры:</b>\n\n"
    for i, game in enumerate(games[:5], 1):  # Show top 5 results
        price_text = f"${game['current_price']}" if game['current_price'] else "Цена не указана"
        discount_text = f" (-{game['discount_percent']}%)" if game['discount_percent'] else ""
        response += f"{i}. {game['title']}\n   💰 {price_text}{discount_text}\n\n"

    response += "📝 <b>Выберите номер игры для добавления:</b>\n"
    response += "Ответьте номером (1-5) или 'отмена' для отмены."

    # Store search results and user state
    search_results[user_id] = games[:5]
    user_states[user_id] = {'action': 'select_game'}
    await message.reply(response)

@dp.message(Command("list"))
async def cmd_list(message: Message):
    """Handle /list command - show user's wishlist"""
    user_id = message.from_user.id
    db = next(get_db())

    user = db.query(User).filter(User.telegram_id == user_id).first()
    if not user:
        await message.reply("❌ Пользователь не найден. Используйте /start")
        return

    # Get user's wishlist with game info
    wishlist_items = (
        db.query(UserWishlist, Game)
        .join(Game, UserWishlist.game_id == Game.id)
        .filter(UserWishlist.user_id == user.id)
        .all()
    )

    if not wishlist_items:
        await message.reply("📝 Ваш виш-лист пуст.\n\nИспользуйте /add <название игры> для добавления игр.")
        return

    response = "📋 <b>Ваш виш-лист:</b>\n\n"
    for i, (wishlist_item, game) in enumerate(wishlist_items, 1):
        price_text = f"${game.last_price_cents/100:.2f}" if game.last_price_cents else "Цена не проверена"
        threshold_text = f" (желаемая: ${wishlist_item.desired_price_cents/100:.2f})" if wishlist_item.desired_price_cents else ""
        response += f"{i}. {game.title}\n   💰 {price_text}{threshold_text}\n\n"

    response += "💡 Используйте /remove <номер> для удаления игры"
    await message.reply(response)

@dp.message(Command("remove"))
async def cmd_remove(message: Message):
    """Handle /remove command - remove game from wishlist"""
    args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    user_id = message.from_user.id

    if not args:
        await message.reply("Укажите номер игры: /remove <номер>")
        return

    try:
        game_number = int(args[0]) - 1  # Convert to 0-based index
    except ValueError:
        await message.reply("❌ Неверный номер. Укажите число.")
        return

    db = next(get_db())
    user = db.query(User).filter(User.telegram_id == user_id).first()
    if not user:
        await message.reply("❌ Пользователь не найден. Используйте /start")
        return

    # Get user's wishlist
    wishlist_items = (
        db.query(UserWishlist)
        .filter(UserWishlist.user_id == user.id)
        .all()
    )

    if game_number < 0 or game_number >= len(wishlist_items):
        await message.reply("❌ Неверный номер игры.")
        return

    # Remove the game
    item_to_remove = wishlist_items[game_number]
    db.delete(item_to_remove)
    db.commit()

    await message.reply("✅ Игра удалена из виш-листа!")

@dp.message(Command("setthreshold"))
async def cmd_setthreshold(message: Message):
    """Handle /setthreshold command - set price threshold for notifications"""
    args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    user_id = message.from_user.id

    if not args:
        await message.reply("Укажите желаемую цену: /setthreshold <цена в долларах>")
        return

    try:
        price = float(args[0])
        if price <= 0:
            raise ValueError
    except ValueError:
        await message.reply("❌ Неверная цена. Укажите положительное число.")
        return

    db = next(get_db())
    user = db.query(User).filter(User.telegram_id == user_id).first()
    if not user:
        await message.reply("❌ Пользователь не найден. Используйте /start")
        return

    # Get user's wishlist
    wishlist_items = (
        db.query(UserWishlist, Game)
        .join(Game, UserWishlist.game_id == Game.id)
        .filter(UserWishlist.user_id == user.id)
        .all()
    )

    if not wishlist_items:
        await message.reply("📝 Ваш виш-лист пуст.\n\nСначала добавьте игры командой /add")
        return

    # Show games to choose from
    response = "🎯 <b>Выберите игру для установки порога цены:</b>\n\n"
    for i, (wishlist_item, game) in enumerate(wishlist_items, 1):
        current_price = f"${game.last_price_cents/100:.2f}" if game.last_price_cents else "не проверена"
        response += f"{i}. {game.title} (текущая: {current_price})\n"

    response += f"\n💰 Желаемая цена: ${price:.2f}\n"
    response += "Ответьте номером игры или 'отмена'."

    # Store user state
    user_states[user_id] = {'action': 'set_threshold', 'price': price}
    await message.reply(response)

@dp.message()
async def handle_text_messages(message: Message):
    """Handle text messages for game selection and other interactions"""
    user_id = message.from_user.id
    text = message.text.strip().lower()

    db = next(get_db())
    user = db.query(User).filter(User.telegram_id == user_id).first()
    if not user:
        return

    # Handle game selection from search results
    if user_id in user_states and user_states[user_id].get('action') == 'select_game':
        if text == 'отмена':
            del user_states[user_id]
            await message.reply("❌ Добавление игры отменено.")
            return

        try:
            choice = int(text)
            if choice < 1 or choice > 5:
                raise ValueError
        except ValueError:
            await message.reply("❌ Укажите число от 1 до 5 или 'отмена'.")
            return

        # Get search results
        if user_id not in search_results:
            await message.reply("❌ Результаты поиска устарели. Попробуйте поиск заново.")
            return

        games = search_results[user_id]
        if choice > len(games):
            await message.reply("❌ Неверный номер игры.")
            return

        selected_game = games[choice - 1]

        # Check if game already in wishlist
        existing_game = db.query(Game).filter(Game.source_id == selected_game['id']).first()
        if existing_game:
            # Check if already in user's wishlist
            existing_wishlist = db.query(UserWishlist).filter(
                UserWishlist.user_id == user.id,
                UserWishlist.game_id == existing_game.id
            ).first()
            if existing_wishlist:
                await message.reply("❌ Эта игра уже в вашем виш-листе!")
                del user_states[user_id]
                del search_results[user_id]
                return
            game = existing_game
        else:
            # Create new game entry
            game = Game(
                source_id=selected_game['id'],
                title=selected_game['title'],
                platform=selected_game['platform'],
                last_price_cents=int(selected_game['current_price'] * 100) if selected_game['current_price'] else None,
                currency='USD'
            )
            db.add(game)
            db.commit()
            db.refresh(game)

        # Add to wishlist
        wishlist_item = UserWishlist(
            user_id=user.id,
            game_id=game.id
        )
        db.add(wishlist_item)
        db.commit()

        # Clean up
        del user_states[user_id]
        del search_results[user_id]

        await message.reply(
            f"✅ <b>{selected_game['title']}</b> добавлена в ваш виш-лист!\n\n"
            "Используйте /setthreshold для установки желаемой цены."
        )
        return

    # Handle threshold setting
    elif user_id in user_states and user_states[user_id].get('action') == 'set_threshold':
        if text == 'отмена':
            del user_states[user_id]
            await message.reply("❌ Установка порога отменена.")
            return

        try:
            choice = int(text)
            if choice < 1:
                raise ValueError
        except ValueError:
            await message.reply("❌ Укажите номер игры или 'отмена'.")
            return

        # Get wishlist items
        wishlist_items = (
            db.query(UserWishlist, Game)
            .join(Game, UserWishlist.game_id == Game.id)
            .filter(UserWishlist.user_id == user.id)
            .all()
        )

        if choice > len(wishlist_items):
            await message.reply("❌ Неверный номер игры.")
            return

        wishlist_item, game = wishlist_items[choice - 1]
        threshold_price = user_states[user_id]['price']

        # Update threshold
        wishlist_item.desired_price_cents = int(threshold_price * 100)
        db.commit()

        del user_states[user_id]

        await message.reply(
            f"✅ Порог цены для <b>{game.title}</b> установлен: ${threshold_price:.2f}\n\n"
            "Вы получите уведомление, когда цена опустится ниже этого значения!"
        )
        return

async def main():
    """Main function to start the bot"""
    logger.info("Starting Nintendo Deals Bot...")

    # Create database tables
    from models.database import engine
    from models.models import Base
    Base.metadata.create_all(bind=engine)

    # Start polling
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
