from abc import ABC, abstractmethod
from typing import Dict, List, Optional

class PriceProvider(ABC):
    """Abstract base class for price providers"""

    @abstractmethod
    def get_game_info(self, game_id: str) -> Optional[Dict]:
        """Get game information including title, platform, current price, discount"""
        pass

    @abstractmethod
    def get_price(self, game_id: str) -> Optional[float]:
        """Get current price for a game"""
        pass

    @abstractmethod
    def search_games(self, query: str, region: str = "us") -> List[Dict]:
        """Search for games by title"""
        pass
