"""
FinnHub API Client

Low-level client for interacting with FinnHub API.
"""

import os
import logging
import time
import requests
from typing import Dict, Any, Optional, List
from urllib.parse import urljoin

from .exceptions import (
    APIKeyError,
    RateLimitError,
    DataFetchError,
    InvalidSymbolError
)

logger = logging.getLogger(__name__)


class FinnHubClient:
    """Low-level FinnHub API client"""
    
    BASE_URL = "https://finnhub.io/api/v1/"
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize FinnHub client.
        
        Args:
            api_key: FinnHub API key. If not provided, will try to get from environment.
        """
        self.api_key = api_key or os.getenv('FINNHUB_API_KEY')
        if not self.api_key:
            raise APIKeyError("FinnHub API key not provided. Set FINNHUB_API_KEY environment variable.")
        
        self.session = requests.Session()
        self.session.headers.update({
            'X-Finnhub-Token': self.api_key
        })
        
        # Rate limiting: 60 calls/minute for free tier
        self.last_request_time = 0
        self.min_request_interval = 1.0  # 1 second between requests
    
    def _rate_limit(self):
        """Enforce rate limiting"""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last_request
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f}s")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """
        Make API request to FinnHub.
        
        Args:
            endpoint: API endpoint
            params: Query parameters
            
        Returns:
            JSON response data
            
        Raises:
            RateLimitError: If rate limit exceeded
            DataFetchError: If request fails
        """
        self._rate_limit()
        
        url = urljoin(self.BASE_URL, endpoint)
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            
            # Check for rate limit
            if response.status_code == 429:
                raise RateLimitError("FinnHub API rate limit exceeded")
            
            # Check for unauthorized
            if response.status_code == 401:
                raise APIKeyError("Invalid FinnHub API key")
            
            # Check for other errors
            response.raise_for_status()
            
            # Parse JSON
            data = response.json()
            
            # Check for API error messages
            if isinstance(data, dict) and 'error' in data:
                raise DataFetchError(f"FinnHub API error: {data['error']}")
            
            return data
            
        except requests.exceptions.Timeout:
            raise DataFetchError("Request timeout")
        except requests.exceptions.ConnectionError:
            raise DataFetchError("Connection error")
        except requests.exceptions.RequestException as e:
            raise DataFetchError(f"Request failed: {str(e)}")
        except ValueError as e:
            raise DataFetchError(f"Invalid JSON response: {str(e)}")
    
    def get_quote(self, symbol: str) -> Dict[str, Any]:
        """Get real-time quote"""
        return self.request('quote', {'symbol': symbol.upper()})
    
    def get_company_profile(self, symbol: str) -> Dict[str, Any]:
        """Get company profile"""
        data = self.request('stock/profile2', {'symbol': symbol.upper()})
        if not data:
            raise InvalidSymbolError(f"Invalid symbol or no data available: {symbol}")
        return data
    
    def get_company_news(self, symbol: str, from_date: str, to_date: str) -> List[Dict[str, Any]]:
        """Get company news"""
        return self.request('company-news', {
            'symbol': symbol.upper(),
            'from': from_date,
            'to': to_date
        })
    
    def get_market_news(self, category: str = 'general', min_id: int = 0) -> List[Dict[str, Any]]:
        """Get market news"""
        params = {'category': category}
        if min_id > 0:
            params['minId'] = min_id
        return self.request('news', params)
    
    def get_insider_sentiment(self, symbol: str, from_date: str, to_date: str) -> Dict[str, Any]:
        """Get insider sentiment"""
        return self.request('stock/insider-sentiment', {
            'symbol': symbol.upper(),
            'from': from_date,
            'to': to_date
        })
    
    def get_insider_transactions(self, symbol: str) -> Dict[str, Any]:
        """Get insider transactions"""
        return self.request('stock/insider-transactions', {
            'symbol': symbol.upper()
        })
    
    def close(self):
        """Close the session"""
        self.session.close()