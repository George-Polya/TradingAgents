"""
FinnHub Provider with caching support
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from .client import FinnHubClient
from .cache import InMemoryCache
from .models import (
    Quote,
    CompanyProfile,
    CompanyNews,
    MarketNews,
    InsiderSentiment,
    InsiderTransaction
)
from .exceptions import DataFetchError, InvalidSymbolError

logger = logging.getLogger(__name__)


class FinnHubProvider:
    """High-level FinnHub data provider with caching"""
    
    def __init__(self, api_key: Optional[str] = None, cache_ttl: int = 300):
        """
        Initialize FinnHub provider.
        
        Args:
            api_key: FinnHub API key
            cache_ttl: Default cache TTL in seconds (default: 5 minutes)
        """
        self.client = FinnHubClient(api_key)
        self.cache = InMemoryCache()
        self.default_ttl = cache_ttl
    
    def _get_cache_key(self, method: str, *args, **kwargs) -> str:
        """Generate cache key from method and arguments"""
        parts = [method]
        parts.extend(str(arg) for arg in args)
        parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
        return ":".join(parts)
    
    def get_quote(self, symbol: str, use_cache: bool = True) -> Quote:
        """
        Get real-time quote for a symbol.
        
        Args:
            symbol: Stock ticker symbol
            use_cache: Whether to use cache (default: True)
            
        Returns:
            Quote object
        """
        cache_key = self._get_cache_key("quote", symbol)
        
        if use_cache:
            cached = self.cache.get(cache_key)
            if cached is not None:
                logger.debug(f"Quote for {symbol} from cache")
                return cached
        
        try:
            data = self.client.get_quote(symbol)
            quote = Quote(**data)
            
            # Cache for 1 minute for real-time data
            self.cache.set(cache_key, quote, ttl=60)
            
            return quote
            
        except Exception as e:
            logger.error(f"Failed to get quote for {symbol}: {e}")
            raise DataFetchError(f"Failed to get quote for {symbol}: {str(e)}")
    
    def get_company_profile(self, symbol: str) -> CompanyProfile:
        """
        Get company profile information.
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            CompanyProfile object
        """
        cache_key = self._get_cache_key("profile", symbol)
        
        cached = self.cache.get(cache_key)
        if cached is not None:
            logger.debug(f"Profile for {symbol} from cache")
            return cached
        
        try:
            data = self.client.get_company_profile(symbol)
            
            # Add symbol to data if not present
            if 'symbol' not in data:
                data['symbol'] = symbol.upper()
            
            profile = CompanyProfile(**data)
            
            # Cache for 24 hours for static data
            self.cache.set(cache_key, profile, ttl=86400)
            
            return profile
            
        except InvalidSymbolError:
            raise
        except Exception as e:
            logger.error(f"Failed to get profile for {symbol}: {e}")
            raise DataFetchError(f"Failed to get profile for {symbol}: {str(e)}")
    
    def get_company_news(
        self,
        symbol: str,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        days_back: int = 7
    ) -> List[CompanyNews]:
        """
        Get company news.
        
        Args:
            symbol: Stock ticker symbol
            from_date: Start date (YYYY-MM-DD)
            to_date: End date (YYYY-MM-DD)
            days_back: Days to look back if dates not provided (default: 7)
            
        Returns:
            List of CompanyNews objects
        """
        # Handle date parameters
        if not to_date:
            to_date = datetime.now().strftime('%Y-%m-%d')
        if not from_date:
            from_dt = datetime.now() - timedelta(days=days_back)
            from_date = from_dt.strftime('%Y-%m-%d')
        
        cache_key = self._get_cache_key("news", symbol, from_date, to_date)
        
        cached = self.cache.get(cache_key)
        if cached is not None:
            logger.debug(f"News for {symbol} from cache")
            return cached
        
        try:
            data = self.client.get_company_news(symbol, from_date, to_date)
            news = [CompanyNews(**item) for item in data]
            
            # Cache for 1 hour
            self.cache.set(cache_key, news, ttl=3600)
            
            return news
            
        except Exception as e:
            logger.error(f"Failed to get news for {symbol}: {e}")
            raise DataFetchError(f"Failed to get news for {symbol}: {str(e)}")
    
    def get_market_news(self, category: str = 'general', min_id: int = 0) -> List[MarketNews]:
        """
        Get market news.
        
        Args:
            category: News category (general, forex, crypto, merger)
            min_id: Minimum news ID for pagination
            
        Returns:
            List of MarketNews objects
        """
        cache_key = self._get_cache_key("market_news", category, min_id)
        
        cached = self.cache.get(cache_key)
        if cached is not None:
            logger.debug(f"Market news from cache")
            return cached
        
        try:
            data = self.client.get_market_news(category, min_id)
            news = [MarketNews(**item) for item in data]
            
            # Cache for 30 minutes
            self.cache.set(cache_key, news, ttl=1800)
            
            return news
            
        except Exception as e:
            logger.error(f"Failed to get market news: {e}")
            raise DataFetchError(f"Failed to get market news: {str(e)}")
    
    def get_insider_sentiment(
        self,
        symbol: str,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get insider sentiment data.
        
        Args:
            symbol: Stock ticker symbol
            from_date: Start date (YYYY-MM-DD)
            to_date: End date (YYYY-MM-DD)
            
        Returns:
            Insider sentiment data
        """
        # Default to last 3 months
        if not to_date:
            to_date = datetime.now().strftime('%Y-%m-%d')
        if not from_date:
            from_dt = datetime.now() - timedelta(days=90)
            from_date = from_dt.strftime('%Y-%m-%d')
        
        cache_key = self._get_cache_key("insider_sentiment", symbol, from_date, to_date)
        
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached
        
        try:
            data = self.client.get_insider_sentiment(symbol, from_date, to_date)
            
            # Cache for 1 day
            self.cache.set(cache_key, data, ttl=86400)
            
            return data
            
        except Exception as e:
            logger.error(f"Failed to get insider sentiment for {symbol}: {e}")
            raise DataFetchError(f"Failed to get insider sentiment: {str(e)}")
    
    def get_insider_transactions(self, symbol: str) -> Dict[str, Any]:
        """
        Get insider transactions data.
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            Insider transactions data
        """
        cache_key = self._get_cache_key("insider_transactions", symbol)
        
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached
        
        try:
            data = self.client.get_insider_transactions(symbol)
            
            # Cache for 1 day
            self.cache.set(cache_key, data, ttl=86400)
            
            return data
            
        except Exception as e:
            logger.error(f"Failed to get insider transactions for {symbol}: {e}")
            raise DataFetchError(f"Failed to get insider transactions: {str(e)}")
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check provider health by making a test API call.
        
        Returns:
            Health status dictionary
        """
        try:
            # Try to get Apple quote as a test
            quote = self.get_quote('AAPL', use_cache=False)
            return {
                'status': 'healthy',
                'provider': 'finnhub',
                'test_symbol': 'AAPL',
                'test_price': quote.current_price
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'provider': 'finnhub',
                'error': str(e)
            }
    
    def clear_cache(self):
        """Clear all cached data"""
        self.cache.clear()
    
    def close(self):
        """Close provider and cleanup resources"""
        self.client.close()
    
    def __enter__(self):
        """Context manager support"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager cleanup"""
        self.close()


# Singleton instance
_finnhub_provider = None


def get_finnhub_provider() -> FinnHubProvider:
    """Get or create singleton FinnHub provider instance"""
    global _finnhub_provider
    if _finnhub_provider is None:
        _finnhub_provider = FinnHubProvider()
    return _finnhub_provider