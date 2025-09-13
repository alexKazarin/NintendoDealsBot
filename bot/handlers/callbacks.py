import logging
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from models.database import get_db
from models.models import User, Game, UserWishlist
from providers.deku_deals_provider import DekuDealsProvider
from .keyboards import get_main_menu_keyboard
from .commands import search_results, user_states, price_provider

logger = logging.getLogger(__name__)


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


async def process_back_to_menu(callback_query: CallbackQuery):
    """Handle back to menu button"""
    menu_text = "🎮 <b>Main Menu</b>\n\nChoose an option:"
    await callback_query.message.edit_text(menu_text, reply_markup=get_main_menu_keyboard(), parse_mode="HTML")
    await callback_query.answer()


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


def register_callbacks(dp):
    """Register all callback query handlers"""
    dp.callback_query.register(process_add_game, lambda c: c.data == "menu_add_game")
    dp.callback_query.register(process_wishlist, lambda c: c.data == "menu_wishlist")
    dp.callback_query.register(process_settings, lambda c: c.data == "menu_settings")
    dp.callback_query.register(process_help, lambda c: c.data == "menu_help")
    dp.callback_query.register(process_premium, lambda c: c.data == "menu_premium")
    dp.callback_query.register(process_donate, lambda c: c.data == "menu_donate")
    dp.callback_query.register(process_back_to_menu, lambda c: c.data == "menu_back")
    dp.callback_query.register(process_wishlist_remove, lambda c: c.data.startswith("wishlist_remove_"))
    dp.callback_query.register(process_wishlist_threshold, lambda c: c.data.startswith("wishlist_threshold_"))
    dp.callback_query.register(process_settings_region, lambda c: c.data == "settings_region")
    dp.callback_query.register(process_settings_threshold, lambda c: c.data == "settings_threshold")
    dp.callback_query.register(process_region_change, lambda c: c.data.startswith("region_"))
    dp.callback_query.register(process_premium_subscribe, lambda c: c.data == "premium_subscribe")
    dp.callback_query.register(process_donate_stars, lambda c: c.data == "donate_stars")
    dp.callback_query.register(process_add_game_selection, lambda c: c.data.startswith("add_game_"))
