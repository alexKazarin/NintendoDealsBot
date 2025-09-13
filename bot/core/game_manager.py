import logging
from typing import List, Dict, Optional

from models.database import get_db
from models.models import Game, UserWishlist, User
from providers.deku_deals_provider import DekuDealsProvider

logger = logging.getLogger(__name__)


class GameManager:
    """Business logic for game and wishlist management"""

    def __init__(self):
        self.price_provider = DekuDealsProvider()

    def search_games(self, query: str, region: str = "us") -> List[Dict]:
        """Search for games using the price provider"""
        logger.info(f"Searching for games with query: '{query}' in region: {region}")
        games = self.price_provider.search_games(query, region)
        logger.info(f"Search returned {len(games)} games")
        return games

    def add_game_to_wishlist(self, user_id: int, game_data: Dict) -> tuple[bool, str]:
        """Add game to user's wishlist"""
        db = next(get_db())

        # Check if game already exists
        existing_game = db.query(Game).filter(Game.source_id == game_data['id']).first()
        if existing_game:
            # Check if already in user's wishlist
            existing_wishlist = db.query(UserWishlist).filter(
                UserWishlist.user_id == user_id,
                UserWishlist.game_id == existing_game.id
            ).first()
            if existing_wishlist:
                return False, "Game is already in your wishlist"
            game = existing_game
        else:
            # Create new game entry
            game = Game(
                source_id=game_data['id'],
                title=game_data['title'],
                platform=game_data['platform'],
                last_price_cents=int(game_data['current_price'] * 100) if game_data['current_price'] else None,
                currency='USD'
            )
            db.add(game)
            db.commit()
            db.refresh(game)

        # Add to wishlist
        wishlist_item = UserWishlist(
            user_id=user_id,
            game_id=game.id
        )
        db.add(wishlist_item)
        db.commit()

        return True, f"✅ {game_data['title']} added to your wishlist!"

    def remove_game_from_wishlist(self, user_id: int, game_index: int) -> tuple[bool, str]:
        """Remove game from user's wishlist by index"""
        db = next(get_db())

        # Get user's wishlist
        wishlist_items = (
            db.query(UserWishlist)
            .filter(UserWishlist.user_id == user_id)
            .all()
        )

        if game_index < 0 or game_index >= len(wishlist_items):
            return False, "Invalid game number"

        # Remove the game
        item_to_remove = wishlist_items[game_index]
        db.delete(item_to_remove)
        db.commit()

        return True, "✅ Game removed from wishlist"

    def get_user_wishlist(self, user_id: int) -> List[Dict]:
        """Get user's wishlist with game details"""
        db = next(get_db())

        wishlist_items = (
            db.query(UserWishlist, Game)
            .join(Game, UserWishlist.game_id == Game.id)
            .filter(UserWishlist.user_id == user_id)
            .all()
        )

        result = []
        for i, (wishlist_item, game) in enumerate(wishlist_items, 1):
            price_text = f"${game.last_price_cents/100:.2f}" if game.last_price_cents else "Price not checked"
            threshold_text = f" (desired: ${wishlist_item.desired_price_cents/100:.2f})" if wishlist_item.desired_price_cents else ""

            result.append({
                "index": i,
                "game": game,
                "wishlist_item": wishlist_item,
                "display_text": f"{i}. {game.title}\n   💰 {price_text}{threshold_text}\n\n"
            })

        return result

    def set_price_threshold(self, user_id: int, game_index: int, price: float) -> tuple[bool, str]:
        """Set price threshold for a game in user's wishlist"""
        db = next(get_db())

        # Get user's wishlist
        wishlist_items = (
            db.query(UserWishlist, Game)
            .join(Game, UserWishlist.game_id == Game.id)
            .filter(UserWishlist.user_id == user_id)
            .all()
        )

        if game_index < 0 or game_index >= len(wishlist_items):
            return False, "Invalid game number"

        wishlist_item, game = wishlist_items[game_index]

        # Update threshold
        wishlist_item.desired_price_cents = int(price * 100)
        db.commit()

        return True, f"✅ Price threshold for {game.title} set: ${price:.2f}"

    def get_game_info(self, game_id: str) -> Optional[Dict]:
        """Get detailed game information"""
        return self.price_provider.get_game_info(game_id)

    def get_game_price(self, game_id: str) -> Optional[float]:
        """Get current game price"""
        return self.price_provider.get_price(game_id)
