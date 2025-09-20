"""Helper functions and utilities"""

from typing import Optional
from models.models import Game, UserWishlist


def format_price(cents: Optional[int], currency: str = "USD") -> str:
    """Format price from cents to dollars"""
    if cents is None:
        return "Price not available"

    dollars = cents / 100
    return f"${dollars:.2f}"


def validate_price_input(price_str: str) -> tuple[bool, Optional[float]]:
    """Validate and parse price input"""
    try:
        price = float(price_str)
        if price <= 0:
            return False, None
        return True, price
    except ValueError:
        return False, None


def get_game_display_info(game: Game, wishlist_item: Optional[UserWishlist] = None) -> str:
    """Get formatted display info for a game"""
    price_text = format_price(game.last_price_cents)

    if wishlist_item and wishlist_item.desired_price_cents:
        threshold_text = f" (desired: {format_price(wishlist_item.desired_price_cents)})"
    else:
        threshold_text = ""

    return f"{game.title}\n💰 {price_text}{threshold_text}"


def format_wishlist_item(index: int, game: Game, wishlist_item: UserWishlist) -> str:
    """Format wishlist item for display"""
    price_text = format_price(game.last_price_cents)
    threshold_text = f" (desired: {format_price(wishlist_item.desired_price_cents)})" if wishlist_item.desired_price_cents else ""

    return f"{index}. {game.title}\n   💰 {price_text}{threshold_text}\n\n"


def calculate_savings(old_price: int, new_price: int) -> float:
    """Calculate savings amount"""
    return (old_price - new_price) / 100


def is_price_below_threshold(current_price: int, threshold_price: Optional[int]) -> bool:
    """Check if current price is below threshold"""
    if threshold_price is None:
        return False
    return current_price <= threshold_price


def clean_game_title(title: str) -> str:
    """Clean and normalize game title"""
    return title.strip()


def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text to max length"""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def validate_region(region: str) -> bool:
    """Validate region code"""
    valid_regions = ['us', 'eu', 'jp']
    return region.lower() in valid_regions


def get_region_display_name(region: str) -> str:
    """Get display name for region"""
    region_names = {
        'us': '🇺🇸 United States',
        'eu': '🇪🇺 Europe',
        'jp': '🇯🇵 Japan'
    }
    return region_names.get(region.lower(), region.upper())


def get_currency_symbol(region: str) -> str:
    """Get currency symbol for region"""
    currency_symbols = {
        'us': '$',
        'eu': '€',
        'jp': '¥'
    }
    return currency_symbols.get(region.lower(), '$')
