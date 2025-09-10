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

def main():
    """Run all tests"""
    print("🧪 Testing Nintendo Deals Bot MVP")
    print("=" * 40)

    tests = [
        ("Imports", test_imports),
        ("Database", test_database),
        ("Price Provider", test_provider),
        ("Bot Token", test_bot_token),
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
