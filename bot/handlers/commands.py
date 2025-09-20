import logging
from aiogram import Bot
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from models.database import get_db
from models.models import User, Game, UserWishlist
from providers.deku_deals_provider import DekuDealsProvider
from bot.core.user_manager import UserManager
from bot.utils.helpers import get_currency_symbol
from .keyboards import get_main_menu_keyboard

logger = logging.getLogger(__name__)

# Global variables (will be moved to proper storage later)
search_results = {}
user_states = {}
price_provider = DekuDealsProvider()


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
        "Choose an option from the menu below:"
    )

    await message.reply(welcome_text, reply_markup=get_main_menu_keyboard(), parse_mode="HTML")


async def cmd_menu(message: Message):
    """Handle /menu command - show main menu"""
    menu_text = "🎮 <b>Main Menu</b>\n\nChoose an option:"
    await message.reply(menu_text, reply_markup=get_main_menu_keyboard(), parse_mode="HTML")


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
        "/donate - support development\n\n"
        "💡 <b>How to use:</b>\n"
        "1. Add a game using /add command\n"
        "2. Set desired price with /setthreshold\n"
        "3. Get discount notifications!\n\n"
        "🔗 Free: up to 5 games in wishlist\n💎 Donate to increase limit (+5 games for 6 months)"
    )

    await message.reply(help_text, parse_mode="HTML")


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

    await message.reply(donate_text, parse_mode="HTML")


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
    limits = UserManager.check_user_limits(user.id)
    if not limits["can_add_more"]:
        await message.reply(
            f"❌ Wishlist limit reached ({limits['current_games']} / {limits['max_games']}).\n"
            "Make a donation to increase your limit or remove some games."
        )
        return

    # Search for games
    await message.answer("🔍 Searching for games...")
    logger.info(f"User {user_id} searching for games with query: '{query}' in region: {user.region}")
    games = price_provider.search_games(query, user.region)
    logger.info(f"Search returned {len(games)} games for query '{query}'")

    if not games:
        logger.warning(f"No games found for query '{query}' in region {user.region}")
        await message.answer("❌ No games found. Try a different name.")
        return

    # Show search results
    response = "🎮 Found games:\n\n"
    for i, game in enumerate(games[:5], 1):  # Show top 5 results
        price_text = f"${game['current_price']}" if game['current_price'] else "Price not specified"
        discount_text = f" (-{game['discount_percent']}%)" if game['discount_percent'] else ""
        response += f"{i}. {game['title']}\n   💰 {price_text}{discount_text}\n\n"

    response += "📝 Select game number to add:\n"
    response += "Reply with number (1-5) or 'cancel' to cancel."

    # Store search results and user state
    search_results[user_id] = games[:5]
    user_states[user_id] = {'action': 'select_game'}
    await message.answer(response)


async def cmd_list(message: Message):
    """Handle /list command - show user's wishlist with buttons"""
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
        await message.reply(
            "📝 Your wishlist is empty.\n\nUse /add <game name> to add games or use the menu.",
            reply_markup=get_main_menu_keyboard()
        )
        return

    # Get user limits
    limits = UserManager.check_user_limits(user.id)

    # Create wishlist with buttons
    response = f"📋 <b>Your Wishlist:</b> {limits['current_games']} / {limits['max_games']} games\n\n"
    keyboard_buttons = []

    for i, (wishlist_item, game) in enumerate(wishlist_items, 1):
        # Format price display with current price, crossed out original price, and discount
        currency_symbol = get_currency_symbol(user.region)

        if game.last_price_cents:
            current_price_text = f"<b>{currency_symbol}{game.last_price_cents/100:.2f}</b>"
            if game.original_price_cents and game.original_price_cents != game.last_price_cents:
                original_price_text = f" <s>{currency_symbol}{game.original_price_cents/100:.2f}</s>"
            else:
                original_price_text = ""
            discount_text = f" <i>(-{game.discount_percent}%)</i>" if game.discount_percent else ""
            price_display = f"{current_price_text}{original_price_text}{discount_text}"
        else:
            price_display = "Price not checked"

        threshold_text = f" (desired: {currency_symbol}{wishlist_item.desired_price_cents/100:.2f})" if wishlist_item.desired_price_cents else ""
        response += f"{i}. {game.title}\n   💰 {price_display}{threshold_text}\n\n"

        # Add buttons for each game
        keyboard_buttons.append([
            InlineKeyboardButton(text=f"🗑️ Remove {i}", callback_data=f"wishlist_remove_{i-1}"),
            InlineKeyboardButton(text=f"💰 Set Price {i}", callback_data=f"wishlist_threshold_{i-1}")
        ])

    # Add back button
    keyboard_buttons.append([InlineKeyboardButton(text="🔙 Back to Menu", callback_data="menu_back")])

    wishlist_keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

    await message.reply(response, reply_markup=wishlist_keyboard, parse_mode="HTML")


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
    await message.reply(response, parse_mode="HTML")


def register_commands(dp):
    """Register all command handlers"""
    dp.message.register(cmd_start, Command("start"))
    dp.message.register(cmd_menu, Command("menu"))
    dp.message.register(cmd_help, Command("help"))
    dp.message.register(cmd_region, Command("region"))
    dp.message.register(cmd_donate, Command("donate"))
    dp.message.register(cmd_add, Command("add"))
    dp.message.register(cmd_list, Command("list"))
    dp.message.register(cmd_remove, Command("remove"))
    dp.message.register(cmd_setthreshold, Command("setthreshold"))
