from datetime import datetime, timedelta
from models.database import get_db
from models.models import User, UserPremiumPurchase


class UserManager:
    """Business logic for user management"""

    @staticmethod
    def create_or_get_user(telegram_id: int, username: str = None) -> User:
        """Create or get existing user"""
        db = next(get_db())
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            user = User(telegram_id=telegram_id, telegram_username=username)
            db.add(user)
            db.commit()
            db.refresh(user)
        return user

    @staticmethod
    def update_user_region(user_id: int, region: str) -> bool:
        """Update user's region"""
        db = next(get_db())
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.region = region
            db.commit()
            return True
        return False

    @staticmethod
    def check_user_limits(user_id: int) -> dict:
        """Check user's current limits and usage"""
        db = next(get_db())
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"max_games": 20, "current_games": 0, "can_add_more": True}

        from models.models import UserWishlist
        current_games = db.query(UserWishlist).filter(UserWishlist.user_id == user.id).count()

        # Calculate max games: base 5 + active premium bonuses
        now = datetime.utcnow()
        active_purchases = db.query(UserPremiumPurchase).filter(
            UserPremiumPurchase.user_id == user.id,
            UserPremiumPurchase.expires_at > now
        ).all()

        bonus_games = sum(purchase.bonus_games for purchase in active_purchases)
        max_games = 20 + bonus_games

        return {
            "max_games": max_games,
            "current_games": current_games,
            "can_add_more": current_games < max_games
        }

    @staticmethod
    def add_premium_purchase(user_id: int, bonus_games: int = 5, months: int = 6) -> bool:
        """Add premium purchase for user"""
        db = next(get_db())
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return False

        expires_at = datetime.utcnow() + timedelta(days=30 * months)
        purchase = UserPremiumPurchase(
            user_id=user.id,
            bonus_games=bonus_games,
            expires_at=expires_at
        )
        db.add(purchase)
        db.commit()
        return True
