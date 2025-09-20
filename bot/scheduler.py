import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from models.database import get_db, SessionLocal
from models.models import User, Game, UserWishlist, PriceHistory, Notification
from providers.deku_deals_provider import DekuDealsProvider

logger = logging.getLogger(__name__)

class PriceChecker:
    """Service for checking game prices and sending notifications"""

    def __init__(self):
        self.price_provider = DekuDealsProvider()
        self.scheduler = AsyncIOScheduler()
        self.bot = None  # Will be set later to avoid circular imports

    def set_bot(self, bot):
        """Set the bot instance for sending notifications"""
        self.bot = bot

    def start(self):
        """Start the price checking scheduler"""
        # Check prices every 30 minutes
        self.scheduler.add_job(
            self.check_all_prices,
            trigger=IntervalTrigger(minutes=30),
            id='price_checker',
            name='Check game prices',
            replace_existing=True
        )

        self.scheduler.start()
        logger.info("Price checker scheduler started")

    def stop(self):
        """Stop the scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Price checker scheduler stopped")

    async def check_all_prices(self):
        """Check prices for all games in all users' wishlists"""
        logger.info("Starting price check for all games...")

        db = SessionLocal()

        try:
            # Get all unique games that are in users' wishlists
            games_to_check = (
                db.query(Game)
                .join(UserWishlist, UserWishlist.game_id == Game.id)
                .distinct()
                .all()
            )

            logger.info(f"Found {len(games_to_check)} games to check")

            for game in games_to_check:
                await self.check_game_price(db, game)

            db.commit()

        except Exception as e:
            logger.error(f"Error during price check: {e}")
            db.rollback()
        finally:
            db.close()

    async def check_game_price(self, db, game: Game):
        """Check price for a specific game and send notifications if needed"""
        try:
            # Get full game info from provider
            game_info = self.price_provider.get_game_info(game.source_id)

            if game_info is None:
                logger.warning(f"Could not get info for game {game.title} (ID: {game.source_id})")
                return

            current_price_cents = int(game_info['current_price'] * 100) if game_info['current_price'] else None
            original_price_cents = int(game_info['original_price'] * 100) if game_info['original_price'] else None

            # Update game info
            game.last_price_cents = current_price_cents
            game.original_price_cents = original_price_cents
            game.discount_percent = game_info['discount_percent']
            game.last_checked = datetime.utcnow()

            # Add to price history
            if current_price_cents:
                price_history = PriceHistory(
                    game_id=game.id,
                    price_cents=current_price_cents,
                    currency='USD'
                )
                db.add(price_history)

            # Check if price changed and send notifications
            if current_price_cents:
                await self.check_price_alerts(db, game, current_price_cents)

        except Exception as e:
            logger.error(f"Error checking price for game {game.title}: {e}")

    async def check_price_alerts(self, db, game: Game, current_price_cents: int):
        """Check if any users should be notified about price changes"""
        # Get all wishlist items for this game
        wishlist_items = (
            db.query(UserWishlist)
            .filter(UserWishlist.game_id == game.id)
            .all()
        )

        for wishlist_item in wishlist_items:
            user = db.query(User).filter(User.id == wishlist_item.user_id).first()
            if not user:
                continue

            should_notify = False
            notification_reason = ""

            # Check desired price threshold
            if (wishlist_item.desired_price_cents and
                current_price_cents <= wishlist_item.desired_price_cents and
                (wishlist_item.last_notified_price_cents is None or
                 current_price_cents < wishlist_item.last_notified_price_cents)):

                should_notify = True
                notification_reason = f"Price dropped to ${current_price_cents/100:.2f} (desired: ${wishlist_item.desired_price_cents/100:.2f})"

            # Check minimum discount (if implemented)
            # This could be added later based on game history

            if should_notify:
                await self.send_notification(user, game, current_price_cents, notification_reason)

                # Update last notified price
                wishlist_item.last_notified_price_cents = current_price_cents

                # Log notification
                notification = Notification(
                    user_id=user.id,
                    game_id=game.id,
                    price_cents=current_price_cents,
                    rule=notification_reason
                )
                db.add(notification)

    async def send_notification(self, user: User, game: Game, price_cents: int, reason: str):
        """Send notification to user about price change"""
        if not self.bot:
            logger.error("Bot not set for price checker")
            return

        try:
            message_text = (
                f"🎉 <b>Game discount!</b>\n\n"
                f"🎮 <b>{game.title}</b>\n"
                f"💰 New price: ${price_cents/100:.2f}\n"
                f"📊 {reason}\n\n"
                f"🔗 Check on DekuDeals: https://www.dekudeals.com/items/{game.source_id}"
            )

            await self.bot.send_message(
                chat_id=user.telegram_id,
                text=message_text,
                parse_mode='HTML'
            )

            logger.info(f"Notification sent to user {user.telegram_id} for game {game.title}")

        except Exception as e:
            logger.error(f"Error sending notification to user {user.telegram_id}: {e}")

# Global instance
price_checker = PriceChecker()
