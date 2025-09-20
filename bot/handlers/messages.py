import logging
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from models.database import get_db
from models.models import User, Game, UserWishlist
from providers.deku_deals_provider import DekuDealsProvider
from .keyboards import get_main_menu_keyboard
from .commands import search_results, user_states, price_provider

logger = logging.getLogger(__name__)


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
        max_games = 10

        if wishlist_count >= max_games:
            await message.reply(
                f"❌ Wishlist limit reached ({max_games}).\n"
                "Remove some games to add new ones.",
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


def register_messages(dp):
    """Register message handlers"""
    dp.message.register(handle_text_messages)
