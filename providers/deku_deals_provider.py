import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Optional
from .base_provider import PriceProvider

class DekuDealsProvider(PriceProvider):
    """Price provider implementation for DekuDeals"""

    BASE_URL = "https://www.dekudeals.com"
    SEARCH_URL = f"{BASE_URL}/search"
    GAME_URL = f"{BASE_URL}/items"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def search_games(self, query: str, region: str = "us") -> List[Dict]:
        """Search for games on DekuDeals"""
        try:
            params = {'term': query}
            response = self.session.get(self.SEARCH_URL, params=params)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')
            games = []

            # Parse search results
            game_items = soup.find_all('div', class_='item-grid-item')

            for item in game_items[:10]:  # Limit to 10 results
                title_elem = item.find('a', class_='item-grid-item-name')
                if not title_elem:
                    continue

                title = title_elem.text.strip()
                game_url = title_elem['href']
                game_id = game_url.split('/')[-1]

                # Get price info
                price_elem = item.find('span', class_='price')
                current_price = None
                original_price = None
                discount = None

                if price_elem:
                    current_price_text = price_elem.find('span', class_='price-current')
                    if current_price_text:
                        current_price = self._parse_price(current_price_text.text.strip())

                    original_price_elem = price_elem.find('span', class_='price-original')
                    if original_price_elem:
                        original_price = self._parse_price(original_price_elem.text.strip())

                    discount_elem = price_elem.find('span', class_='price-discount')
                    if discount_elem:
                        discount_text = discount_elem.text.strip()
                        discount = int(discount_text.replace('%', '').replace('-', ''))

                games.append({
                    'id': game_id,
                    'title': title,
                    'current_price': current_price,
                    'original_price': original_price,
                    'discount_percent': discount,
                    'url': f"{self.BASE_URL}{game_url}",
                    'platform': 'switch'  # Assuming Nintendo Switch for MVP
                })

            return games

        except Exception as e:
            print(f"Error searching games: {e}")
            return []

    def get_game_info(self, game_id: str) -> Optional[Dict]:
        """Get detailed game information"""
        try:
            url = f"{self.GAME_URL}/{game_id}"
            response = self.session.get(url)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Extract title
            title_elem = soup.find('h1', class_='item-title')
            title = title_elem.text.strip() if title_elem else "Unknown"

            # Extract prices
            price_info = self._extract_price_info(soup)

            return {
                'id': game_id,
                'title': title,
                'platform': 'switch',
                'current_price': price_info['current'],
                'original_price': price_info['original'],
                'discount_percent': price_info['discount'],
                'currency': 'USD',
                'url': url
            }

        except Exception as e:
            print(f"Error getting game info: {e}")
            return None

    def get_price(self, game_id: str) -> Optional[float]:
        """Get current price for a game"""
        info = self.get_game_info(game_id)
        return info['current_price'] if info else None

    def _parse_price(self, price_text: str) -> Optional[float]:
        """Parse price string to float"""
        try:
            # Remove currency symbols and convert to float
            cleaned = price_text.replace('$', '').replace('€', '').replace('£', '').strip()
            return float(cleaned)
        except (ValueError, AttributeError):
            return None

    def _extract_price_info(self, soup: BeautifulSoup) -> Dict:
        """Extract price information from game page"""
        current_price = None
        original_price = None
        discount = None

        # Look for price elements
        price_container = soup.find('div', class_='price-container')
        if price_container:
            current_elem = price_container.find('span', class_='price-current')
            if current_elem:
                current_price = self._parse_price(current_elem.text.strip())

            original_elem = price_container.find('span', class_='price-original')
            if original_elem:
                original_price = self._parse_price(original_elem.text.strip())

            discount_elem = price_container.find('span', class_='price-discount')
            if discount_elem:
                discount_text = discount_elem.text.strip()
                discount = int(discount_text.replace('%', '').replace('-', ''))

        return {
            'current': current_price,
            'original': original_price,
            'discount': discount
        }
