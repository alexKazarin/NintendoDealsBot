from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, TIMESTAMP, Text
from sqlalchemy.sql import func
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    telegram_username = Column(String)
    region = Column(String, default="us")
    created_at = Column(TIMESTAMP, server_default=func.now())

class UserPremiumPurchase(Base):
    __tablename__ = "user_premium_purchases"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    purchased_at = Column(TIMESTAMP, server_default=func.now())
    expires_at = Column(TIMESTAMP, nullable=False)
    bonus_games = Column(Integer, default=5)

class Game(Base):
    __tablename__ = "games"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(String, nullable=False)  # id from DekuDeals or other system
    title = Column(String, nullable=False)
    platform = Column(String, default="switch")
    last_checked = Column(TIMESTAMP)
    last_price_cents = Column(Integer)
    original_price_cents = Column(Integer)  # Original price before discount
    discount_percent = Column(Integer)  # Discount percentage
    currency = Column(String)

class UserWishlist(Base):
    __tablename__ = "user_wishlist"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    desired_price_cents = Column(Integer)
    min_discount_percent = Column(Integer)
    last_notified_price_cents = Column(Integer)
    created_at = Column(TIMESTAMP, server_default=func.now())

class PriceHistory(Base):
    __tablename__ = "price_history"

    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    price_cents = Column(Integer, nullable=False)
    currency = Column(String, nullable=False)
    recorded_at = Column(TIMESTAMP, server_default=func.now())

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    price_cents = Column(Integer, nullable=False)
    sent_at = Column(TIMESTAMP, server_default=func.now())
    rule = Column(Text)
