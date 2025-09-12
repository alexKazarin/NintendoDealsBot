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
        "🎮 <b>Welcome to Nintendo Deals Bot!</b>\n\n"
        "I'll help you track discounts on Nintendo Switch games.\n\n"
        "📋 <b>Main commands:</b>\n"
        "/add <game name> - add game to wishlist\n"
        "/list - show your wishlist\n"
        "/remove <number> - remove game from wishlist\n"
        "/setthreshold <price> - set price threshold for notifications\n"
        "/region <region> - change region (us, eu, jp)\n"
        "/help - show this help\n\n"
        "💎 <b>Premium features:</b>\n"
        "/subscribe - get premium subscription\n"
        "/donate - support the project\n\n"
        f"Your ID: {user_id}"
    )

    await message.reply(welcome_text)

@dp.message(Command("help"))
async def cmd_help(message: Message):
    """Handle /help command"""
    help_text = (
        "🎮 <b>Nintendo Deals Bot - Help</b>\n\n"
        "📋 <b>Commands:</b>\n"
        "/start - start using the bot\n"
        "/add <game name> - add game to wishlist\n"
        "/list - show tracked games list\n"
        "/remove <number> - remove game from wishlist\n"
        "/setthreshold <price> - set desired price\n"
        "/region <region> - change region (us/eu/jp)\n"
        "/subscribe - premium subscription (up to 100 games)\n"
        "/donate - support development\n\n"
        "💡 <b>How to use:</b>\n"
        "1. Add a game using /add command\n"
        "2. Set desired price with /setthreshold\n"
        "3. Get discount notifications!\n\n"
        "🔗 Free: up to 10 games in wishlist"
    )

    await message.reply(help_text)

@dp.message(Command("region"))
async def cmd_region(message: Message):
    """Handle /region command"""
    args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    user_id = message.from_user.id

    if not args:
        await message.reply("Specify region: /region us|eu|jp")
        return

    region = args[0].lower()
    if region not in ['us', 'eu', 'jp']:
        await message.reply("Invalid region. Available: us, eu, jp")
        return

    db = next(get_db())
    user = db.query(User).filter(User.telegram_id == user_id).first()
    if user:
        user.region = region
        db.commit()
        await message.reply(f"✅ Region changed to: {region.upper()}")
    else:
        await message.reply("❌ User not found")

@dp.message(Command("subscribe"))
async def cmd_subscribe(message: Message):
    """Handle /subscribe command"""
    user_id = message.from_user.id

    db = next(get_db())
    user = db.query(User).filter(User.telegram_id == user_id).first()

    if user and user.is_premium:
        await message.reply("✅ You already have premium subscription!")
        return

    # In MVP, we'll just set premium for demo purposes
    # In production, this would integrate with payment system
    if user:
        user.is_premium = True
        db.commit()
        await message.reply(
            "🎉 <b>Premium subscription activated!</b>\n\n"
            "Now you can track up to 100 games!\n"
            "Thank you for your support! 💎"
        )
    else:
        await message.reply("❌ User not found")

@dp.message(Command("donate"))
async def cmd_donate(message: Message):
    """Handle /donate command"""
    donate_text = (
        "💝 <b>Support the project</b>\n\n"
        "Your contribution helps develop the bot!\n\n"
        "💳 <b>Support methods:</b>\n"
        "• Telegram Stars: send stars to the bot\n"
        "• Cryptocurrency: coming soon\n"
        "• PayPal: link will be later\n\n"
        "Thank you for your support! 🙏"
    )

    await message.reply(donate_text)

@dp.message(Command("add"))
async def cmd_add(message: Message):
    """Handle /add command - add game to wishlist"""
    args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    user_id = message.from_user.id

    if not args:
        await message.reply("Specify game name: /add <game name>")
        return

    query = " ".join(args)
    db = next(get_db())

    # Get user
    user = db.query(User).filter(User.telegram_id == user_id).first()
    if not user:
        await message.reply("❌ User not found. Use /start")
        return

    # Check wishlist limit
    wishlist_count = db.query(UserWishlist).filter(UserWishlist.user_id == user.id).count()
    max_games = 100 if user.is_premium else 10

    if wishlist_count >= max_games:
        await message.reply(
            f"❌ Wishlist limit reached ({max_games}).\n"
            "Get premium subscription with /subscribe to increase limit to 100 games."
        )
        return

    # Search for games
    await message.reply("🔍 Searching for games...")
    games = price_provider.search_games(query, user.region)

    if not games:
        await message.reply("❌ No games found. Try a different name.")
        return

    # Show search results
    response = "🎮 <b>Found games:</b>\n\n"
    for i, game in enumerate(games[:5], 1):  # Show top 5 results
        price_text = f"${game['current_price']}" if game['current_price'] else "Price not specified"
        discount_text = f" (-{game['discount_percent']}%)" if game['discount_percent'] else ""
        response += f"{i}. {game['title']}\n   💰 {price_text}{discount_text}\n\n"

    response += "📝 <b>Select game number to add:</b>\n"
    response += "Reply with number (1-5) or 'cancel' to cancel."

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
        await message.reply("❌ User not found. Use /start")
        return

    # Get user's wishlist with game info
    wishlist_items = (
        db.query(UserWishlist, Game)
        .join(Game, UserWishlist.game_id == Game.id)
        .filter(UserWishlist.user_id == user.id)
        .all()
    )

    if not wishlist_items:
        await message.reply("📝 Your wishlist is empty.\n\nUse /add <game name> to add games.")
        return

    response = "📋 <b>Your wishlist:</b>\n\n"
    for i, (wishlist_item, game) in enumerate(wishlist_items, 1):
        price_text = f"${game.last_price_cents/100:.2f}" if game.last_price_cents else "Price not checked"
        threshold_text = f" (desired: ${wishlist_item.desired_price_cents/100:.2f})" if wishlist_item.desired_price_cents else ""
        response += f"{i}. {game.title}\n   💰 {price_text}{threshold_text}\n\n"

    response += "💡 Use /remove <number> to remove a game"
    await message.reply(response)

@dp.message(Command("remove"))
async def cmd_remove(message: Message):
    """Handle /remove command - remove game from wishlist"""
    args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    user_id = message.from_user.id

    if not args:
        await message.reply("Specify game number: /remove <number>")
        return

    try:
        game_number = int(args[0]) - 1  # Convert to 0-based index
    except ValueError:
        await message.reply("❌ Invalid number. Specify a number.")
        return

    db = next(get_db())
    user = db.query(User).filter(User.telegram_id == user_id).first()
    if not user:
        await message.reply("❌ User not found. Use /start")
        return

    # Get user's wishlist
    wishlist_items = (
        db.query(UserWishlist)
        .filter(UserWishlist.user_id == user.id)
        .all()
    )

    if game_number < 0 or game_number >= len(wishlist_items):
        await message.reply("❌ Invalid game number.")
        return

    # Remove the game
    item_to_remove = wishlist_items[game_number]
    db.delete(item_to_remove)
    db.commit()

    await message.reply("✅ Game removed from wishlist!")

@dp.message(Command("setthreshold"))
async def cmd_setthreshold(message: Message):
    """Handle /setthreshold command - set price threshold for notifications"""
    args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    user_id = message.from_user.id

    if not args:
        await message.reply("Specify desired price: /setthreshold <price in dollars>")
        return

    try:
        price = float(args[0])
        if price <= 0:
            raise ValueError
    except ValueError:
        await message.reply("❌ Invalid price. Specify a positive number.")
        return

    db = next(get_db())
    user = db.query(User).filter(User.telegram_id == user_id).first()
    if not user:
        await message.reply("❌ User not found. Use /start")
        return

    # Get user's wishlist
    wishlist_items = (
        db.query(UserWishlist, Game)
        .join(Game, UserWishlist.game_id == Game.id)
        .filter(UserWishlist.user_id == user.id)
        .all()
    )

    if not wishlist_items:
        await message.reply("📝 Your wishlist is empty.\n\nAdd games first using /add command")
        return

    # Show games to choose from
    response = "🎯 <b>Select game to set price threshold:</b>\n\n"
    for i, (wishlist_item, game) in enumerate(wishlist_items, 1):
        current_price = f"${game.last_price_cents/100:.2f}" if game.last_price_cents else "not checked"
        response += f"{i}. {game.title} (current: {current_price})\n"

    response += f"\n💰 Desired price: ${price:.2f}\n"
    response += "Reply with game number or 'cancel'."

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
        if text == 'cancel':
            del user_states[user_id]
            await message.reply("❌ Game addition cancelled.")
            return

        try:
            choice = int(text)
            if choice < 1 or choice > 5:
                raise ValueError
        except ValueError:
            await message.reply("❌ Specify number from 1 to 5 or 'cancel'.")
            return

        # Get search results
        if user_id not in search_results:
            await message.reply("❌ Search results expired. Try searching again.")
            return

        games = search_results[user_id]
        if choice > len(games):
            await message.reply("❌ Invalid game number.")
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
                await message.reply("❌ This game is already in your wishlist!")
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
            f"✅ <b>{selected_game['title']}</b> added to your wishlist!\n\n"
            "Use /setthreshold to set desired price."
        )
        return

    # Handle threshold setting
    elif user_id in user_states and user_states[user_id].get('action') == 'set_threshold':
        if text == 'cancel':
            del user_states[user_id]
            await message.reply("❌ Threshold setting cancelled.")
            return

        try:
            choice = int(text)
            if choice < 1:
                raise ValueError
        except ValueError:
            await message.reply("❌ Specify game number or 'cancel'.")
            return

        # Get wishlist items
        wishlist_items = (
            db.query(UserWishlist, Game)
            .join(Game, UserWishlist.game_id == Game.id)
            .filter(UserWishlist.user_id == user.id)
            .all()
        )

        if choice > len(wishlist_items):
            await message.reply("❌ Invalid game number.")
            return

        wishlist_item, game = wishlist_items[choice - 1]
        threshold_price = user_states[user_id]['price']

        # Update threshold
        wishlist_item.desired_price_cents = int(threshold_price * 100)
        db.commit()

        del user_states[user_id]

        await message.reply(
            f"✅ Price threshold for <b>{game.title}</b> set: ${threshold_price:.2f}\n\n"
            "You'll receive notification when price drops below this value!"
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
