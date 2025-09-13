#!/usr/bin/env python3
"""
Test script for DekuDeals provider
"""

import logging
import sys
import os

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from providers.deku_deals_provider import DekuDealsProvider

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_search():
    """Test game search functionality"""
    provider = DekuDealsProvider()

    test_queries = [
        "zelda",
        "mario",
        "pokemon",
        "animal crossing"
    ]

    for query in test_queries:
        print(f"\n{'='*50}")
        print(f"Testing search for: '{query}'")
        print(f"{'='*50}")

        games = provider.search_games(query)

        print(f"Found {len(games)} games")

        if games:
            for i, game in enumerate(games[:3], 1):  # Show first 3 results
                print(f"{i}. {game['title']}")
                print(f"   ID: {game['id']}")
                print(f"   Price: ${game['current_price']}")
                print(f"   URL: {game['url']}")
                print()
        else:
            print("No games found!")

if __name__ == "__main__":
    test_search()
