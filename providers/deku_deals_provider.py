import requests
import logging
from bs4 import BeautifulSoup
from typing import Dict, List, Optional
from .base_provider import PriceProvider

logger = logging.getLogger(__name__)

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

    def _get_currency_for_region(self, region: str) -> str:
        """Get currency code for region"""
        currency_map = {
            'us': 'USD',
            'eu': 'EUR',
            'jp': 'JPY'
        }
        return currency_map.get(region.lower(), 'USD')

    def search_games(self, query: str, region: str = "us") -> List[Dict]:
        """Search for games on DekuDeals"""
        logger.info(f"Searching for games with query: '{query}', region: {region}")

        try:
            # Use correct parameter 'q' instead of 'term' and add digital filter
            params = {'q': query, 'filter[format]': 'digital'}
            url = f"{self.SEARCH_URL}?q={query}&filter[format]=digital"
            logger.info(f"Making request to: {url}")

            # Add region-specific headers
            headers = self.session.headers.copy()
            if region.lower() == 'eu':
                headers['Accept-Language'] = 'en-GB,en;q=0.9'
            elif region.lower() == 'jp':
                headers['Accept-Language'] = 'ja,en;q=0.9'

            response = self.session.get(self.SEARCH_URL, params=params, headers=headers)
            logger.info(f"Response status code: {response.status_code}")

            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')
            games = []

            # Parse search results - updated selectors for new site structure
            game_containers = soup.find_all('div', class_='d-flex flex-column', style=lambda x: x and 'gap: 0.2rem' in x)
            logger.info(f"Found {len(game_containers)} game containers on the page")

            # Debug: print some HTML content to see structure
            if len(game_containers) == 0:
                logger.warning("No game containers found. Page structure might have changed.")
                # Log first 2000 characters of response for debugging
                logger.debug(f"Response content preview: {response.text[:2000]}")

            # Filter games by query since search redirects to main page
            filtered_games = []
            query_lower = query.lower()
            currency = self._get_currency_for_region(region)

            for container in game_containers[:50]:  # Check more games to find matches
                title_elem = container.find('a', class_='main-link')
                if not title_elem:
                    continue

                title = title_elem.text.strip()
                game_url = title_elem['href']
                game_id = game_url.split('/')[-1]

                # Check if game title matches the search query
                if query_lower not in title.lower():
                    continue

                logger.debug(f"Found matching game: {title} (ID: {game_id})")

                # Get price info - look for price elements directly in container
                current_price = None
                original_price = None
                discount = None

                # Debug: log container HTML for price debugging
                logger.debug(f"Container HTML preview: {str(container)[:500]}")

                # Find current price (strong tag)
                price_strong = container.find('strong')
                if price_strong:
                    price_text = price_strong.text.strip()
                    logger.debug(f"Found strong tag with text: '{price_text}'")
                    current_price = self._parse_price(price_text)
                    logger.debug(f"Parsed current price: {current_price}")
                else:
                    logger.debug("No strong tag found in container")

                # Find original price (s tag with text-muted class)
                original_price_elem = container.find('s', class_='text-muted')
                if original_price_elem:
                    original_text = original_price_elem.text.strip()
                    logger.debug(f"Found s tag with text: '{original_text}'")
                    original_price = self._parse_price(original_text)
                    logger.debug(f"Parsed original price: {original_price}")
                else:
                    logger.debug("No s tag with text-muted class found in container")

                # Find discount percentage (badge-danger)
                discount_elem = container.find('span', class_='badge-danger')
                if discount_elem:
                    discount_text = discount_elem.text.strip()
                    logger.debug(f"Found badge-danger with text: '{discount_text}'")
                    discount = int(discount_text.replace('%', '').replace('-', ''))
                    logger.debug(f"Parsed discount: {discount}%")
                else:
                    logger.debug("No badge-danger span found in container")

                filtered_games.append({
                    'id': game_id,
                    'title': title,
                    'current_price': current_price,
                    'original_price': original_price,
                    'discount_percent': discount,
                    'currency': currency,
                    'url': f"{self.BASE_URL}{game_url}",
                    'platform': 'switch'  # Assuming Nintendo Switch for MVP
                })

                # Limit to 10 results
                if len(filtered_games) >= 10:
                    break

            logger.info(f"Successfully found {len(filtered_games)} games matching query '{query}'")
            return filtered_games

        except Exception as e:
            logger.error(f"Error searching games: {e}", exc_info=True)
            return []

    def get_game_info(self, game_id: str, region: str = "us") -> Optional[Dict]:
        """Get detailed game information"""
        try:
            url = f"{self.GAME_URL}/{game_id}"

            # Add region-specific headers
            headers = self.session.headers.copy()
            if region.lower() == 'eu':
                headers['Accept-Language'] = 'en-GB,en;q=0.9'
            elif region.lower() == 'jp':
                headers['Accept-Language'] = 'ja,en;q=0.9'

            response = self.session.get(url, headers=headers)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Extract title
            title_elem = soup.find('h1', class_='item-title')
            title = title_elem.text.strip() if title_elem else "Unknown"

            # Extract prices
            price_info = self._extract_price_info(soup)
            currency = self._get_currency_for_region(region)

            return {
                'id': game_id,
                'title': title,
                'platform': 'switch',
                'current_price': price_info['current'],
                'original_price': price_info['original'],
                'discount_percent': price_info['discount'],
                'currency': currency,
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
            # Handle European decimal format (comma instead of dot)
            cleaned = cleaned.replace(',', '.')
            return float(cleaned)
        except (ValueError, AttributeError):
            logger.debug(f"Failed to parse price: '{price_text}' -> '{cleaned}'")
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
