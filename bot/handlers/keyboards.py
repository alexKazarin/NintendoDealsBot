from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


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
