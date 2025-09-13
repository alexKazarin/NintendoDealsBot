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

# Temporary storage for search results (in production, use Redis or database)
search_results = {}
user_states = {}

def get_main_menu_keyboard():
    """Create main menu inline keyboard"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎮 Add Game", callback_data="menu_add_game"),
            InlineKeyboardButton(text="📋 My Wishlist", callback_data="menu_wishlist")
        ],
        [
            InlineKeyboardButton(text="⚙️ Settings", callback_data="menu_settings"),
            InlineKeyboardButton(text="❓ Help", callback_data="menu_help")
        ],
        [
            InlineKeyboardButton(text="💎 Premium", callback_data="menu_premium"),
            InlineKeyboardButton(text="💝 Donate", callback_data="menu_donate")
        ]
    ])
    return keyboard

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
        "Choose an option from the menu below:"
    )

    await message.reply(welcome_text, reply_markup=get_main_menu_keyboard(), parse_mode="HTML")

@dp.message(Command("menu"))
async def cmd_menu(message: Message):
    """Handle /menu command - show main menu"""
    menu_text = "🎮 <b>Main Menu</b>\n\nChoose an option:"
    await message.reply(menu_text, reply_markup=get_main_menu_keyboard(), parse_mode="HTML")

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

    await message.reply(help_text, parse_mode="HTML")

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
            "Thank you for your support! 💎",
            parse_mode="HTML"
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

    await message.reply(donate_text, parse_mode="HTML")

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
    logger.info(f"User {user_id} searching for games with query: '{query}' in region: {user.region}")
    games = price_provider.search_games(query, user.region)
    logger.info(f"Search returned {len(games)} games for query '{query}'")

    if not games:
        logger.warning(f"No games found for query '{query}' in region {user.region}")
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
    await message.reply(response, parse_mode="HTML")

@dp.message(Command("list"))
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

    # Create wishlist with buttons
    response = "📋 <b>Your Wishlist:</b>\n\n"
    keyboard_buttons = []

    for i, (wishlist_item, game) in enumerate(wishlist_items, 1):
        price_text = f"${game.last_price_cents/100:.2f}" if game.last_price_cents else "Price not checked"
        threshold_text = f" (desired: ${wishlist_item.desired_price_cents/100:.2f})" if wishlist_item.desired_price_cents else ""
        response += f"{i}. {game.title}\n   💰 {price_text}{threshold_text}\n\n"

        # Add buttons for each game
        keyboard_buttons.append([
            InlineKeyboardButton(text=f"🗑️ Remove {i}", callback_data=f"wishlist_remove_{i-1}"),
            InlineKeyboardButton(text=f"💰 Set Price {i}", callback_data=f"wishlist_threshold_{i-1}")
        ])

    # Add back button
    keyboard_buttons.append([InlineKeyboardButton(text="🔙 Back to Menu", callback_data="menu_back")])

    wishlist_keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

    await message.reply(response, reply_markup=wishlist_keyboard, parse_mode="HTML")

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
    await message.reply(response, parse_mode="HTML")

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
            "Use /setthreshold to set desired price.",
            parse_mode="HTML"
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
            "You'll receive notification when price drops below this value!",
            parse_mode="HTML"
        )
        return

    # Handle inline threshold setting (from menu)
    elif user_id in user_states and user_states[user_id].get('action') == 'set_threshold_inline':
        try:
            price = float(text)
            if price <= 0:
                raise ValueError
        except ValueError:
            await message.reply("❌ Invalid price. Please enter a positive number.")
            return

        game_index = user_states[user_id]['game_index']

        # Get wishlist items
        wishlist_items = (
            db.query(UserWishlist, Game)
            .join(Game, UserWishlist.game_id == Game.id)
            .filter(UserWishlist.user_id == user.id)
            .all()
        )

        if game_index >= len(wishlist_items):
            await message.reply("❌ Game not found.")
            return

        wishlist_item, game = wishlist_items[game_index]

        # Update threshold
        wishlist_item.desired_price_cents = int(price * 100)
        db.commit()

        del user_states[user_id]

        await message.reply(
            f"✅ Price threshold for <b>{game.title}</b> set: ${price:.2f}\n\n"
            "You'll receive notification when price drops below this value!",
            reply_markup=get_main_menu_keyboard()
        )
        return

    # Handle game search from menu
    elif user_id in user_states and user_states[user_id].get('action') == 'search_game':
        query = text.strip()
        if not query or len(query) < 2:
            await message.reply("❌ Please enter a valid game name (at least 2 characters).")
            return

        # Check wishlist limit
        wishlist_count = db.query(UserWishlist).filter(UserWishlist.user_id == user.id).count()
        max_games = 100 if user.is_premium else 10

        if wishlist_count >= max_games:
            await message.reply(
                f"❌ Wishlist limit reached ({max_games}).\n"
                "Get premium subscription to increase limit to 100 games.",
                reply_markup=get_main_menu_keyboard()
            )
            return

        # Search for games
        await message.reply("🔍 Searching for games...")
        logger.info(f"User {user_id} searching for games with query: '{query}' in region: {user.region}")
        games = price_provider.search_games(query, user.region)
        logger.info(f"Search returned {len(games)} games for query '{query}'")

        if not games:
            logger.warning(f"No games found for query '{query}' in region {user.region}")
            search_again_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔍 Try Again", callback_data="menu_add_game")],
                [InlineKeyboardButton(text="🔙 Back to Menu", callback_data="menu_back")]
            ])
            await message.reply(
                "❌ No games found. Try a different name.",
                reply_markup=search_again_keyboard
            )
            return

        # Show search results with buttons
        response = "🎮 <b>Found games:</b>\n\n"
        keyboard_buttons = []

        for i, game in enumerate(games[:5], 1):
            price_text = f"${game['current_price']}" if game['current_price'] else "Price not specified"
            discount_text = f" (-{game['discount_percent']}%)" if game['discount_percent'] else ""
            response += f"{i}. {game['title']}\n   💰 {price_text}{discount_text}\n\n"

            keyboard_buttons.append([
                InlineKeyboardButton(text=f"✅ Add {i}", callback_data=f"add_game_{i-1}")
            ])

        keyboard_buttons.append([InlineKeyboardButton(text="🔙 Back to Menu", callback_data="menu_back")])

        search_keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

        # Store search results and user state
        search_results[user_id] = games[:5]
        user_states[user_id] = {'action': 'select_game_inline'}

        await message.reply(response, reply_markup=search_keyboard)
        return

# Callback query handlers for menu buttons
@dp.callback_query(lambda c: c.data == "menu_add_game")
async def process_add_game(callback_query: CallbackQuery):
    """Handle add game menu button"""
    user_id = callback_query.from_user.id
    db = next(get_db())

    user = db.query(User).filter(User.telegram_id == user_id).first()
    if not user:
        await callback_query.answer("❌ User not found")
        return

    # Check wishlist limit
    wishlist_count = db.query(UserWishlist).filter(UserWishlist.user_id == user.id).count()
    max_games = 100 if user.is_premium else 10

    if wishlist_count >= max_games:
        await callback_query.message.edit_text(
            f"❌ Wishlist limit reached ({max_games}).\n\n"
            "Get premium subscription to increase limit to 100 games.",
            reply_markup=get_main_menu_keyboard(),
            parse_mode="HTML"
        )
        await callback_query.answer()
        return

    # Ask for game name
    search_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Back to Menu", callback_data="menu_back")]
    ])

    await callback_query.message.edit_text(
        "🎮 <b>Add Game to Wishlist</b>\n\n"
        "Please enter the game name to search:",
        reply_markup=search_keyboard,
        parse_mode="HTML"
    )

    # Set user state for game search
    user_states[user_id] = {'action': 'search_game'}

    await callback_query.answer()

@dp.callback_query(lambda c: c.data == "menu_wishlist")
async def process_wishlist(callback_query: CallbackQuery):
    """Handle wishlist menu button"""
    user_id = callback_query.from_user.id
    db = next(get_db())

    user = db.query(User).filter(User.telegram_id == user_id).first()
    if not user:
        await callback_query.answer("❌ User not found")
        return

    # Get user's wishlist with game info
    wishlist_items = (
        db.query(UserWishlist, Game)
        .join(Game, UserWishlist.game_id == Game.id)
        .filter(UserWishlist.user_id == user.id)
        .all()
    )

    if not wishlist_items:
        empty_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎮 Add Game", callback_data="menu_add_game")],
            [InlineKeyboardButton(text="🔙 Back to Menu", callback_data="menu_back")]
        ])
        await callback_query.message.edit_text(
            "📝 <b>Your wishlist is empty</b>\n\n"
            "Add some games to start tracking prices!",
            reply_markup=empty_keyboard,
            parse_mode="HTML"
        )
        await callback_query.answer()
        return

    # Create wishlist with buttons
    response = "📋 <b>Your Wishlist:</b>\n\n"
    keyboard_buttons = []

    for i, (wishlist_item, game) in enumerate(wishlist_items, 1):
        price_text = f"${game.last_price_cents/100:.2f}" if game.last_price_cents else "Price not checked"
        threshold_text = f" (desired: ${wishlist_item.desired_price_cents/100:.2f})" if wishlist_item.desired_price_cents else ""
        response += f"{i}. {game.title}\n   💰 {price_text}{threshold_text}\n\n"

        # Add buttons for each game
        keyboard_buttons.append([
            InlineKeyboardButton(text=f"🗑️ Remove {i}", callback_data=f"wishlist_remove_{i-1}"),
            InlineKeyboardButton(text=f"💰 Set Price {i}", callback_data=f"wishlist_threshold_{i-1}")
        ])

    # Add back button
    keyboard_buttons.append([InlineKeyboardButton(text="🔙 Back to Menu", callback_data="menu_back")])

    wishlist_keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

    await callback_query.message.edit_text(response, reply_markup=wishlist_keyboard, parse_mode="HTML")
    await callback_query.answer()

@dp.callback_query(lambda c: c.data == "menu_settings")
async def process_settings(callback_query: CallbackQuery):
    """Handle settings menu button"""
    user_id = callback_query.from_user.id
    db = next(get_db())

    user = db.query(User).filter(User.telegram_id == user_id).first()
    if not user:
        await callback_query.answer("❌ User not found")
        return

    settings_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🌍 Region", callback_data="settings_region"),
            InlineKeyboardButton(text="💰 Threshold", callback_data="settings_threshold")
        ],
        [InlineKeyboardButton(text="🔙 Back to Menu", callback_data="menu_back")]
    ])

    current_region = user.region.upper() if user.region else "US"
    settings_text = (
        "⚙️ <b>Settings</b>\n\n"
        f"🌍 Current region: {current_region}\n"
        f"💎 Premium: {'Yes' if user.is_premium else 'No'}\n\n"
        "Choose what to configure:"
    )

    await callback_query.message.edit_text(settings_text, reply_markup=settings_keyboard, parse_mode="HTML")
    await callback_query.answer()

@dp.callback_query(lambda c: c.data == "menu_help")
async def process_help(callback_query: CallbackQuery):
    """Handle help menu button"""
    help_text = (
        "🎮 <b>Nintendo Deals Bot - Help</b>\n\n"
        "📋 <b>How to use:</b>\n"
        "1. Add games to your wishlist\n"
        "2. Set desired prices for notifications\n"
        "3. Get automatic price drop alerts!\n\n"
        "🎯 <b>Features:</b>\n"
        "• Track up to 10 games (free)\n"
        "• Premium: up to 100 games\n"
        "• Real-time price monitoring\n"
        "• Multi-region support (US/EU/JP)\n\n"
        "💡 <b>Tips:</b>\n"
        "• Use exact game names for better search\n"
        "• Set realistic price thresholds\n"
        "• Check notifications regularly"
    )

    help_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Back to Menu", callback_data="menu_back")]
    ])

    await callback_query.message.edit_text(help_text, reply_markup=help_keyboard, parse_mode="HTML")
    await callback_query.answer()

@dp.callback_query(lambda c: c.data == "menu_premium")
async def process_premium(callback_query: CallbackQuery):
    """Handle premium menu button"""
    user_id = callback_query.from_user.id
    db = next(get_db())

    user = db.query(User).filter(User.telegram_id == user_id).first()
    if not user:
        await callback_query.answer("❌ User not found")
        return

    if user.is_premium:
        premium_text = (
            "💎 <b>You have Premium!</b>\n\n"
            "✅ Track up to 100 games\n"
            "✅ Priority notifications\n"
            "✅ Advanced features\n\n"
            "Thank you for your support! 🙏"
        )
    else:
        premium_text = (
            "💎 <b>Premium Subscription</b>\n\n"
            "🎯 <b>Benefits:</b>\n"
            "• Track up to 100 games (vs 10 free)\n"
            "• Priority price check notifications\n"
            "• Advanced filtering options\n"
            "• Support development\n\n"
            "🚀 <b>Get Premium Now!</b>"
        )

    premium_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎉 Subscribe", callback_data="premium_subscribe")],
        [InlineKeyboardButton(text="🔙 Back to Menu", callback_data="menu_back")]
    ])

    await callback_query.message.edit_text(premium_text, reply_markup=premium_keyboard, parse_mode="HTML")
    await callback_query.answer()

@dp.callback_query(lambda c: c.data == "menu_donate")
async def process_donate(callback_query: CallbackQuery):
    """Handle donate menu button"""
    donate_text = (
        "💝 <b>Support the Project</b>\n\n"
        "Your contribution helps:\n"
        "• Keep the bot running\n"
        "• Add new features\n"
        "• Improve performance\n\n"
        "💳 <b>Support methods:</b>\n"
        "• Telegram Stars\n"
        "• Cryptocurrency\n"
        "• PayPal\n\n"
        "Thank you for your support! 🙏"
    )

    donate_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ Send Stars", callback_data="donate_stars")],
        [InlineKeyboardButton(text="🔙 Back to Menu", callback_data="menu_back")]
    ])

    await callback_query.message.edit_text(donate_text, reply_markup=donate_keyboard, parse_mode="HTML")
    await callback_query.answer()

@dp.callback_query(lambda c: c.data == "menu_back")
async def process_back_to_menu(callback_query: CallbackQuery):
    """Handle back to menu button"""
    menu_text = "🎮 <b>Main Menu</b>\n\nChoose an option:"
    await callback_query.message.edit_text(menu_text, reply_markup=get_main_menu_keyboard(), parse_mode="HTML")
    await callback_query.answer()

@dp.callback_query(lambda c: c.data.startswith("wishlist_remove_"))
async def process_wishlist_remove(callback_query: CallbackQuery):
    """Handle remove game from wishlist"""
    user_id = callback_query.from_user.id
    game_index = int(callback_query.data.split("_")[-1])

    db = next(get_db())
    user = db.query(User).filter(User.telegram_id == user_id).first()
    if not user:
        await callback_query.answer("❌ User not found")
        return

    # Get user's wishlist
    wishlist_items = (
        db.query(UserWishlist)
        .filter(UserWishlist.user_id == user.id)
        .all()
    )

    if game_index < 0 or game_index >= len(wishlist_items):
        await callback_query.answer("❌ Invalid game number")
        return

    # Remove the game
    item_to_remove = wishlist_items[game_index]
    db.delete(item_to_remove)
    db.commit()

    await callback_query.answer("✅ Game removed from wishlist!")

    # Refresh wishlist view
    await process_wishlist(callback_query)

@dp.callback_query(lambda c: c.data.startswith("wishlist_threshold_"))
async def process_wishlist_threshold(callback_query: CallbackQuery):
    """Handle set threshold for game"""
    user_id = callback_query.from_user.id
    game_index = int(callback_query.data.split("_")[-1])

    db = next(get_db())
    user = db.query(User).filter(User.telegram_id == user_id).first()
    if not user:
        await callback_query.answer("❌ User not found")
        return

    # Get user's wishlist
    wishlist_items = (
        db.query(UserWishlist, Game)
        .join(Game, UserWishlist.game_id == Game.id)
        .filter(UserWishlist.user_id == user.id)
        .all()
    )

    if game_index < 0 or game_index >= len(wishlist_items):
        await callback_query.answer("❌ Invalid game number")
        return

    wishlist_item, game = wishlist_items[game_index]

    # Ask for price
    threshold_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Back to Wishlist", callback_data="menu_wishlist")]
    ])

    current_price = f"${game.last_price_cents/100:.2f}" if game.last_price_cents else "not checked"
    threshold_text = (
        f"💰 <b>Set Price Threshold</b>\n\n"
        f"🎮 Game: {game.title}\n"
        f"💵 Current price: {current_price}\n\n"
        "Please enter your desired price in dollars:"
    )

    await callback_query.message.edit_text(threshold_text, reply_markup=threshold_keyboard, parse_mode="HTML")
    await callback_query.answer()

    # Store user state for threshold setting
    user_states[user_id] = {'action': 'set_threshold_inline', 'game_index': game_index}

@dp.callback_query(lambda c: c.data == "settings_region")
async def process_settings_region(callback_query: CallbackQuery):
    """Handle region settings"""
    user_id = callback_query.from_user.id
    db = next(get_db())

    user = db.query(User).filter(User.telegram_id == user_id).first()
    if not user:
        await callback_query.answer("❌ User not found")
        return

    region_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇺🇸 US", callback_data="region_us"),
            InlineKeyboardButton(text="🇪🇺 EU", callback_data="region_eu"),
            InlineKeyboardButton(text="🇯🇵 JP", callback_data="region_jp")
        ],
        [InlineKeyboardButton(text="🔙 Back to Settings", callback_data="menu_settings")]
    ])

    current_region = user.region.upper() if user.region else "US"
    region_text = (
        f"🌍 <b>Change Region</b>\n\n"
        f"Current region: {current_region}\n\n"
        "Choose your region:"
    )

    await callback_query.message.edit_text(region_text, reply_markup=region_keyboard, parse_mode="HTML")
    await callback_query.answer()

@dp.callback_query(lambda c: c.data == "settings_threshold")
async def process_settings_threshold(callback_query: CallbackQuery):
    """Handle threshold settings"""
    user_id = callback_query.from_user.id
    db = next(get_db())

    user = db.query(User).filter(User.telegram_id == user_id).first()
    if not user:
        await callback_query.answer("❌ User not found")
        return

    # Get user's wishlist
    wishlist_items = (
        db.query(UserWishlist, Game)
        .join(Game, UserWishlist.game_id == Game.id)
        .filter(UserWishlist.user_id == user.id)
        .all()
    )

    if not wishlist_items:
        threshold_text = (
            "💰 <b>Set Price Thresholds</b>\n\n"
            "Your wishlist is empty.\n\n"
            "Add games first to set price thresholds."
        )
        threshold_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎮 Add Game", callback_data="menu_add_game")],
            [InlineKeyboardButton(text="🔙 Back to Settings", callback_data="menu_settings")]
        ])
    else:
        threshold_text = (
            "💰 <b>Set Price Thresholds</b>\n\n"
            "Choose a game to set desired price:"
        )
        keyboard_buttons = []

        for i, (wishlist_item, game) in enumerate(wishlist_items, 1):
            price_text = f"${game.last_price_cents/100:.2f}" if game.last_price_cents else "not checked"
            threshold_text += f"\n{i}. {game.title} (current: {price_text})"
            keyboard_buttons.append([
                InlineKeyboardButton(text=f"💰 Set Price {i}", callback_data=f"wishlist_threshold_{i-1}")
            ])

        keyboard_buttons.append([InlineKeyboardButton(text="🔙 Back to Settings", callback_data="menu_settings")])
        threshold_keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

    await callback_query.message.edit_text(threshold_text, reply_markup=threshold_keyboard, parse_mode="HTML")
    await callback_query.answer()

@dp.callback_query(lambda c: c.data.startswith("region_"))
async def process_region_change(callback_query: CallbackQuery):
    """Handle region change"""
    user_id = callback_query.from_user.id
    region = callback_query.data.split("_")[-1]

    db = next(get_db())
    user = db.query(User).filter(User.telegram_id == user_id).first()
    if not user:
        await callback_query.answer("❌ User not found")
        return

    user.region = region
    db.commit()

    await callback_query.answer(f"✅ Region changed to {region.upper()}")

    # Refresh settings view
    await process_settings(callback_query)

@dp.callback_query(lambda c: c.data == "premium_subscribe")
async def process_premium_subscribe(callback_query: CallbackQuery):
    """Handle premium subscription"""
    user_id = callback_query.from_user.id
    db = next(get_db())

    user = db.query(User).filter(User.telegram_id == user_id).first()
    if not user:
        await callback_query.answer("❌ User not found")
        return

    if user.is_premium:
        await callback_query.answer("✅ You already have premium!")
        return

    # Set premium (in production, this would handle payment)
    user.is_premium = True
    db.commit()

    await callback_query.answer("🎉 Premium activated!")

    # Refresh premium view
    await process_premium(callback_query)

@dp.callback_query(lambda c: c.data == "donate_stars")
async def process_donate_stars(callback_query: CallbackQuery):
    """Handle donate with stars"""
    donate_text = (
        "⭐ <b>Support with Telegram Stars</b>\n\n"
        "Click the button below to send stars to the bot:\n\n"
        "💫 Your support helps keep the bot running! 💫"
    )

    stars_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ Send Stars", pay=True)],
        [InlineKeyboardButton(text="🔙 Back to Donate", callback_data="menu_donate")]
    ])

    await callback_query.message.edit_text(donate_text, reply_markup=stars_keyboard)
    await callback_query.answer()

@dp.callback_query(lambda c: c.data.startswith("add_game_"))
async def process_add_game_selection(callback_query: CallbackQuery):
    """Handle game selection from search results"""
    user_id = callback_query.from_user.id
    game_index = int(callback_query.data.split("_")[-1])

    db = next(get_db())
    user = db.query(User).filter(User.telegram_id == user_id).first()
    if not user:
        await callback_query.answer("❌ User not found")
        return

    # Get search results
    if user_id not in search_results:
        await callback_query.answer("❌ Search results expired")
        return

    games = search_results[user_id]
    if game_index < 0 or game_index >= len(games):
        await callback_query.answer("❌ Invalid game number")
        return

    selected_game = games[game_index]

    # Check if game already in wishlist
    existing_game = db.query(Game).filter(Game.source_id == selected_game['id']).first()
    if existing_game:
        # Check if already in user's wishlist
        existing_wishlist = db.query(UserWishlist).filter(
            UserWishlist.user_id == user.id,
            UserWishlist.game_id == existing_game.id
        ).first()
        if existing_wishlist:
            await callback_query.message.edit_text(
                "❌ This game is already in your wishlist!",
                reply_markup=get_main_menu_keyboard(),
                parse_mode="HTML"
            )
            await callback_query.answer()
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
    if user_id in user_states:
        del user_states[user_id]
    if user_id in search_results:
        del search_results[user_id]

    success_text = (
        f"✅ <b>{selected_game['title']}</b> added to your wishlist!\n\n"
        "Use the menu to set a price threshold for notifications."
    )

    await callback_query.message.edit_text(success_text, reply_markup=get_main_menu_keyboard(), parse_mode="HTML")
    await callback_query.answer()

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
