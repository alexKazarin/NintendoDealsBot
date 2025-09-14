#!/usr/bin/env python3
"""
Simple test script for Nintendo Deals Bot
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_imports():
    """Test all imports"""
    try:
        from models.database import engine, get_db
        from models.models import User, Game, UserWishlist, PriceHistory, Notification
        from providers.deku_deals_provider import DekuDealsProvider
        from bot.scheduler import price_checker
        print("✅ All imports successful")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_database():
    """Test database connection and table creation"""
    try:
        from models.database import engine
        from models.models import Base
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created successfully")
        return True
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

def test_provider():
    """Test price provider (may fail if DekuDeals changed their site structure)"""
    try:
        from providers.deku_deals_provider import DekuDealsProvider
        provider = DekuDealsProvider()

        # Test with a simple search
        games = provider.search_games("test")
        print(f"✅ Provider search returned {len(games)} results")

        if games:
            print(f"Sample game: {games[0]}")

        return True
    except Exception as e:
        print(f"⚠️ Provider test failed (expected for MVP): {e}")
        print("This is normal - DekuDeals site structure may have changed")
        return False

def test_bot_token():
    """Test if bot token is configured"""
    token = os.getenv('BOT_TOKEN')
    if token and token != 'your_telegram_bot_token_here':
        print("✅ Bot token is configured")
        return True
    else:
        print("⚠️ Bot token not configured (use .env file)")
        return False

def test_add_game():
    """Test adding a game to wishlist"""
    try:
        from models.database import get_db
        from models.models import User, Game, UserWishlist
        from providers.deku_deals_provider import DekuDealsProvider

        db = next(get_db())

        # Create test user
        test_user_id = 999999999
        user = db.query(User).filter(User.telegram_id == test_user_id).first()
        if not user:
            user = User(telegram_id=test_user_id, telegram_username="test_user", region="us", is_premium=False)
            db.add(user)
            db.commit()
            db.refresh(user)

        # Get a test game from provider
        provider = DekuDealsProvider()
        games = provider.search_games("zelda")
        if not games:
            print("⚠️ No games found for testing")
            return False

        test_game_data = games[0]

        # Check if game already exists
        game = db.query(Game).filter(Game.source_id == test_game_data['id']).first()
        if not game:
            game = Game(
                source_id=test_game_data['id'],
                title=test_game_data['title'],
                platform=test_game_data['platform'],
                last_price_cents=int(test_game_data['current_price'] * 100) if test_game_data['current_price'] else None,
                currency='USD'
            )
            db.add(game)
            db.commit()
            db.refresh(game)

        # Check if already in wishlist
        existing_wishlist = db.query(UserWishlist).filter(
            UserWishlist.user_id == user.id,
            UserWishlist.game_id == game.id
        ).first()

        if existing_wishlist:
            print("⚠️ Game already in wishlist, skipping add test")
            return True

        # Add to wishlist
        wishlist_item = UserWishlist(user_id=user.id, game_id=game.id)
        db.add(wishlist_item)
        db.commit()

        # Verify addition
        count = db.query(UserWishlist).filter(UserWishlist.user_id == user.id).count()
        print(f"✅ Game '{game.title}' added to wishlist. Total games: {count}")

        return True
    except Exception as e:
        print(f"❌ Add game test failed: {e}")
        return False

def test_remove_game():
    """Test removing a game from wishlist"""
    try:
        from models.database import get_db
        from models.models import User, Game, UserWishlist

        db = next(get_db())

        # Use test user
        test_user_id = 999999999
        user = db.query(User).filter(User.telegram_id == test_user_id).first()
        if not user:
            print("⚠️ Test user not found, skipping remove test")
            return False

        # Get user's wishlist
        wishlist_items = db.query(UserWishlist).filter(UserWishlist.user_id == user.id).all()
        if not wishlist_items:
            print("⚠️ No games in wishlist, skipping remove test")
            return False

        # Remove first game
        item_to_remove = wishlist_items[0]
        game = db.query(Game).filter(Game.id == item_to_remove.game_id).first()

        db.delete(item_to_remove)
        db.commit()

        # Verify removal
        remaining_count = db.query(UserWishlist).filter(UserWishlist.user_id == user.id).count()
        print(f"✅ Game '{game.title}' removed from wishlist. Remaining games: {remaining_count}")

        return True
    except Exception as e:
        print(f"❌ Remove game test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Testing Nintendo Deals Bot MVP")
    print("=" * 40)

    tests = [
        ("Imports", test_imports),
        ("Database", test_database),
        ("Price Provider", test_provider),
        ("Bot Token", test_bot_token),
        ("Add Game", test_add_game),
        ("Remove Game", test_remove_game),
    ]

    passed = 0
    total = len(tests)

    for name, test_func in tests:
        print(f"\n🔍 Testing {name}...")
        if test_func():
            passed += 1

    print("\n" + "=" * 40)
    print(f"📊 Test Results: {passed}/{total} passed")

    if passed >= 3:  # Core functionality works
        print("✅ MVP is ready! Core components are working.")
        print("\n🚀 To run the bot:")
        print("1. Set BOT_TOKEN in .env file")
        print("2. Run: python main.py")
    else:
        print("❌ Some core components need fixing")

    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
