import logging
from typing import Dict, List

from aiogram import Bot
from models.database import get_db
from models.models import User, Game, UserWishlist, Notification

logger = logging.getLogger(__name__)


class NotificationManager:
    """Business logic for notifications"""

    def __init__(self, bot: Bot):
        self.bot = bot

    async def send_price_alert(self, user_id: int, game: Game, old_price: int, new_price: int) -> bool:
        """Send price drop notification to user"""
        try:
            db = next(get_db())
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return False

            # Format message
            message = self._format_price_alert_message(game, old_price, new_price)

            # Send message
            await self.bot.send_message(
                chat_id=user.telegram_id,
                text=message,
                parse_mode="HTML"
            )

            # Log notification
            notification = Notification(
                user_id=user_id,
                game_id=game.id,
                price_cents=new_price,
                rule="price_drop"
            )
            db.add(notification)
            db.commit()

            logger.info(f"Price alert sent to user {user_id} for game {game.title}")
            return True

        except Exception as e:
            logger.error(f"Failed to send price alert to user {user_id}: {e}")
            return False

    def _format_price_alert_message(self, game: Game, old_price: int, new_price: int) -> str:
        """Format price alert message"""
        old_price_dollars = old_price / 100
        new_price_dollars = new_price / 100
        savings = old_price_dollars - new_price_dollars

        message = (
            f"🎮 <b>Price Drop Alert!</b>\n\n"
            f"🎯 <b>{game.title}</b>\n"
            f"💰 Old price: ${old_price_dollars:.2f}\n"
            f"💥 New price: ${new_price_dollars:.2f}\n"
            f"💸 You save: ${savings:.2f}\n\n"
            f"🔗 Check it out on DekuDeals!"
        )

        return message

    async def send_custom_notification(self, user_id: int, message: str) -> bool:
        """Send custom notification to user"""
        try:
            db = next(get_db())
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return False

            await self.bot.send_message(
                chat_id=user.telegram_id,
                text=message,
                parse_mode="HTML"
            )

            logger.info(f"Custom notification sent to user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to send custom notification to user {user_id}: {e}")
            return False

    def get_user_notifications(self, user_id: int, limit: int = 10) -> List[Dict]:
        """Get user's recent notifications"""
        db = next(get_db())

        notifications = (
            db.query(Notification, Game)
            .join(Game, Notification.game_id == Game.id)
            .filter(Notification.user_id == user_id)
            .order_by(Notification.sent_at.desc())
            .limit(limit)
            .all()
        )

        result = []
        for notification, game in notifications:
            result.append({
                "notification": notification,
                "game": game,
                "price_dollars": notification.price_cents / 100,
                "sent_at": notification.sent_at
            })

        return result

    def check_price_alerts(self, game: Game, current_price: int) -> List[Dict]:
        """Check if any users should be notified about price change"""
        db = next(get_db())

        # Find users who have this game in wishlist with threshold
        alerts = (
            db.query(UserWishlist, User)
            .join(User, UserWishlist.user_id == User.id)
            .filter(
                UserWishlist.game_id == game.id,
                UserWishlist.desired_price_cents.isnot(None),
                UserWishlist.desired_price_cents >= current_price,
                UserWishlist.last_notified_price_cents.is_(None) | (UserWishlist.last_notified_price_cents > current_price)
            )
            .all()
        )

        result = []
        for wishlist_item, user in alerts:
            result.append({
                "user": user,
                "wishlist_item": wishlist_item,
                "threshold_price": wishlist_item.desired_price_cents,
                "current_price": current_price
            })

        return result

    async def process_price_alerts(self, game: Game, current_price: int) -> int:
        """Process and send price alerts for a game"""
        alerts = self.check_price_alerts(game, current_price)
        sent_count = 0

        for alert in alerts:
            user = alert["user"]
            wishlist_item = alert["wishlist_item"]

            # Send notification
            success = await self.send_price_alert(
                user.id,
                game,
                wishlist_item.last_notified_price_cents or game.last_price_cents,
                current_price
            )

            if success:
                # Update last notified price
                db = next(get_db())
                wishlist_item.last_notified_price_cents = current_price
                db.commit()
                sent_count += 1

        return sent_count
