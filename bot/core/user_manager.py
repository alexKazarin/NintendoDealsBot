from models.database import get_db
from models.models import User


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
    def upgrade_to_premium(user_id: int) -> bool:
        """Upgrade user to premium"""
        db = next(get_db())
        user = db.query(User).filter(User.id == user_id).first()
        if user and not user.is_premium:
            user.is_premium = True
            db.commit()
            return True
        return False

    @staticmethod
    def check_user_limits(user_id: int) -> dict:
        """Check user's current limits and usage"""
        db = next(get_db())
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"max_games": 10, "current_games": 0, "is_premium": False}

        from models.models import UserWishlist
        current_games = db.query(UserWishlist).filter(UserWishlist.user_id == user.id).count()
        max_games = 100 if user.is_premium else 10

        return {
            "max_games": max_games,
            "current_games": current_games,
            "is_premium": user.is_premium,
            "can_add_more": current_games < max_games
        }
