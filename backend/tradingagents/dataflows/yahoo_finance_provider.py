"""
Yahoo Finance Data Provider Module

This module provides real-time financial data from Yahoo Finance.
It uses the yfinance library to fetch stock prices, company information,
and financial statements.
"""

import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
import pandas as pd
import yfinance as yf
from dataclasses import dataclass, field
from enum import Enum
import re
from pydantic import BaseModel, field_validator, Field, ConfigDict
import time
from functools import wraps
import threading
from collections import deque, OrderedDict
import json
import os
from pathlib import Path
from abc import ABC, abstractmethod

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# Custom exceptions for better error handling
class YahooFinanceError(Exception):
    """Base exception for Yahoo Finance data provider"""
    pass


class InvalidTickerError(YahooFinanceError):
    """Raised when an invalid ticker symbol is provided"""
    pass


class DataFetchError(YahooFinanceError):
    """Raised when data fetching fails"""
    pass


class RateLimitError(YahooFinanceError):
    """Raised when rate limit is exceeded"""
    pass


class DataValidationError(YahooFinanceError):
    """Raised when data validation fails"""
    pass


class NetworkError(YahooFinanceError):
    """Raised when network-related errors occur"""
    pass


class ErrorRecoveryStrategy(ABC):
    """Abstract base class for error recovery strategies"""
    
    @abstractmethod
    def handle_error(self, error: Exception, context: Dict[str, Any]) -> Optional[Any]:
        """Handle an error and potentially recover"""
        pass


class DefaultErrorRecoveryStrategy(ErrorRecoveryStrategy):
    """Default error recovery strategy with fallback options"""
    
    def __init__(self, fallback_providers: Optional[List[Any]] = None):
        """
        Initialize recovery strategy.
        
        Args:
            fallback_providers: List of fallback data providers
        """
        self.fallback_providers = fallback_providers or []
        self.error_counts: Dict[str, int] = {}
        self.last_errors: Dict[str, Exception] = {}
        
    def handle_error(self, error: Exception, context: Dict[str, Any]) -> Optional[Any]:
        """
        Handle an error with various recovery strategies.
        
        Args:
            error: The exception that occurred
            context: Context information (method, symbol, etc.)
            
        Returns:
            Recovery result or None
        """
        method = context.get('method', 'unknown')
        symbol = context.get('symbol', 'unknown')
        key = f"{method}:{symbol}"
        
        # Track error counts
        self.error_counts[key] = self.error_counts.get(key, 0) + 1
        self.last_errors[key] = error
        
        # Log the error
        logger.error(f"Error in {method} for {symbol}: {error}")
        
        # Try different recovery strategies based on error type
        if isinstance(error, NetworkError):
            # For network errors, maybe try alternative endpoints
            logger.info("Attempting recovery from network error...")
            # Could implement fallback to different API endpoints
            
        elif isinstance(error, InvalidTickerError):
            # For invalid tickers, could suggest alternatives
            logger.warning(f"Invalid ticker {symbol}, no recovery possible")
            return None
            
        elif isinstance(error, RateLimitError):
            # For rate limits, could queue for later
            logger.warning("Rate limit hit, consider increasing delay")
            
        elif isinstance(error, DataValidationError):
            # For validation errors, could return partial data
            logger.warning("Data validation failed, returning raw data if available")
            if 'raw_data' in context:
                return context['raw_data']
                
        # Try fallback providers if available
        for provider in self.fallback_providers:
            try:
                logger.info(f"Trying fallback provider: {provider.__class__.__name__}")
                if hasattr(provider, method):
                    return getattr(provider, method)(symbol)
            except Exception as e:
                logger.warning(f"Fallback provider failed: {e}")
                
        return None
        
    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics"""
        return {
            'error_counts': dict(self.error_counts),
            'total_errors': sum(self.error_counts.values()),
            'unique_errors': len(set(self.last_errors.values()))
        }


class CacheManager:
    """
    Thread-safe cache manager with TTL and LRU eviction.
    Supports both in-memory and persistent caching.
    """
    
    def __init__(
        self,
        ttl: int = 60,
        max_size: int = 1000,
        persistent: bool = False,
        cache_dir: Optional[str] = None
    ):
        """
        Initialize cache manager.
        
        Args:
            ttl: Time-to-live in seconds
            max_size: Maximum number of items in cache
            persistent: Whether to persist cache to disk
            cache_dir: Directory for persistent cache
        """
        self.ttl = ttl
        self.max_size = max_size
        self.persistent = persistent
        self.cache_dir = Path(cache_dir) if cache_dir else Path.home() / '.yfinance_cache'
        
        # Use OrderedDict for LRU implementation
        self._cache: OrderedDict[str, tuple[Any, float]] = OrderedDict()
        self._lock = threading.RLock()
        
        # Statistics
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        
        # Load persistent cache if enabled
        if self.persistent:
            self._load_cache()
            
    def _load_cache(self) -> None:
        """Load cache from disk if exists."""
        cache_file = self.cache_dir / 'cache.json'
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                    # Only load non-expired items
                    now = time.time()
                    for key, (value, timestamp) in data.items():
                        if now - timestamp < self.ttl:
                            self._cache[key] = (value, timestamp)
                logger.info(f"Loaded {len(self._cache)} items from persistent cache")
            except Exception as e:
                logger.error(f"Failed to load cache: {e}")
                
    def _save_cache(self) -> None:
        """Save cache to disk."""
        if not self.persistent:
            return
            
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            cache_file = self.cache_dir / 'cache.json'
            
            # Convert cache to JSON-serializable format
            data = {}
            for key, (value, timestamp) in self._cache.items():
                # Skip non-serializable objects
                try:
                    json.dumps(value)
                    data[key] = (value, timestamp)
                except (TypeError, ValueError):
                    pass
                    
            with open(cache_file, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            logger.error(f"Failed to save cache: {e}")
            
    def get(self, key: str) -> Optional[Any]:
        """
        Get item from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        with self._lock:
            if key in self._cache:
                value, timestamp = self._cache[key]
                
                # Check if expired
                if time.time() - timestamp > self.ttl:
                    del self._cache[key]
                    self._misses += 1
                    return None
                    
                # Move to end (LRU)
                self._cache.move_to_end(key)
                self._hits += 1
                return value
            
            self._misses += 1
            return None
            
    def set(self, key: str, value: Any) -> None:
        """
        Set item in cache.
        
        Args:
            key: Cache key
            value: Value to cache
        """
        with self._lock:
            # Check if we need to evict
            if key not in self._cache and len(self._cache) >= self.max_size:
                # Remove oldest item (LRU)
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
                self._evictions += 1
                
            self._cache[key] = (value, time.time())
            self._cache.move_to_end(key)
            
            # Save to disk if persistent
            if self.persistent:
                self._save_cache()
                
    def delete(self, key: str) -> bool:
        """
        Delete item from cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if item was deleted, False if not found
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                if self.persistent:
                    self._save_cache()
                return True
            return False
            
    def clear(self) -> None:
        """Clear all items from cache."""
        with self._lock:
            self._cache.clear()
            if self.persistent:
                cache_file = self.cache_dir / 'cache.json'
                if cache_file.exists():
                    cache_file.unlink()
                    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = self._hits / total_requests if total_requests > 0 else 0
            
            return {
                'size': len(self._cache),
                'max_size': self.max_size,
                'ttl': self.ttl,
                'hits': self._hits,
                'misses': self._misses,
                'evictions': self._evictions,
                'hit_rate': hit_rate,
                'total_requests': total_requests
            }
            
    def cleanup_expired(self) -> int:
        """
        Remove expired items from cache.
        
        Returns:
            Number of items removed
        """
        with self._lock:
            now = time.time()
            expired_keys = [
                key for key, (_, timestamp) in self._cache.items()
                if now - timestamp > self.ttl
            ]
            
            for key in expired_keys:
                del self._cache[key]
                
            if expired_keys and self.persistent:
                self._save_cache()
                
            return len(expired_keys)


class RateLimiter:
    """Rate limiter using token bucket algorithm"""
    
    def __init__(self, rate: int = 10, per: float = 1.0):
        """
        Initialize rate limiter.
        
        Args:
            rate: Number of allowed requests
            per: Time period in seconds
        """
        self.rate = rate
        self.per = per
        self.tokens = rate
        self.last_update = time.time()
        self.lock = threading.Lock()
        self.request_times = deque()
        logger.info(f"RateLimiter initialized: {rate} requests per {per} seconds")
    
    def acquire(self) -> None:
        """Acquire permission to make a request, blocking if necessary"""
        with self.lock:
            now = time.time()
            
            # Remove old request times
            cutoff = now - self.per
            while self.request_times and self.request_times[0] < cutoff:
                self.request_times.popleft()
            
            # Check if we've hit the rate limit
            if len(self.request_times) >= self.rate:
                # Calculate wait time
                sleep_time = self.per - (now - self.request_times[0])
                if sleep_time > 0:
                    logger.debug(f"Rate limit reached, sleeping for {sleep_time:.2f}s")
                    time.sleep(sleep_time)
                    now = time.time()
                    
                    # Clean up old times again after sleep
                    cutoff = now - self.per
                    while self.request_times and self.request_times[0] < cutoff:
                        self.request_times.popleft()
            
            # Record this request
            self.request_times.append(now)


def retry_with_exponential_backoff(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """
    Decorator for retrying functions with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        exponential_base: Base for exponential backoff calculation
        exceptions: Tuple of exceptions to catch and retry on
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_retries:
                        logger.error(f"{func.__name__} failed after {max_retries + 1} attempts: {str(e)}")
                        raise
                    
                    # Calculate next delay
                    delay = min(delay * exponential_base, max_delay)
                    
                    # Add jitter to prevent thundering herd
                    jittered_delay = delay * (0.5 + 0.5 * time.time() % 1)
                    
                    logger.warning(f"{func.__name__} attempt {attempt + 1} failed: {str(e)}. Retrying in {jittered_delay:.2f}s...")
                    time.sleep(jittered_delay)
            
            # This should never be reached, but just in case
            if last_exception:
                raise last_exception
                
        return wrapper
    return decorator


class DataPeriod(Enum):
    """Valid data period options for historical data"""
    ONE_DAY = "1d"
    FIVE_DAYS = "5d"
    ONE_MONTH = "1mo"
    THREE_MONTHS = "3mo"
    SIX_MONTHS = "6mo"
    ONE_YEAR = "1y"
    TWO_YEARS = "2y"
    FIVE_YEARS = "5y"
    TEN_YEARS = "10y"
    YTD = "ytd"
    MAX = "max"


class DataInterval(Enum):
    """Valid data interval options for historical data"""
    ONE_MINUTE = "1m"
    TWO_MINUTES = "2m"
    FIVE_MINUTES = "5m"
    FIFTEEN_MINUTES = "15m"
    THIRTY_MINUTES = "30m"
    SIXTY_MINUTES = "60m"
    NINETY_MINUTES = "90m"
    ONE_HOUR = "1h"
    ONE_DAY = "1d"
    FIVE_DAYS = "5d"
    ONE_WEEK = "1wk"
    ONE_MONTH = "1mo"
    THREE_MONTHS = "3mo"


class StockPriceModel(BaseModel):
    """Stock price data model with validation"""
    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})
    
    symbol: str = Field(..., min_length=1, max_length=10)
    current_price: float = Field(..., ge=0)
    previous_close: float = Field(..., ge=0)
    open_price: float = Field(..., ge=0)
    day_high: float = Field(..., ge=0)
    day_low: float = Field(..., ge=0)
    volume: int = Field(..., ge=0)
    market_cap: Optional[float] = Field(None, ge=0)
    timestamp: datetime = Field(default_factory=datetime.now)
    
    @field_validator('symbol')
    @classmethod
    def validate_symbol(cls, v):
        """Validate stock symbol format"""
        if not re.match(r'^[A-Z0-9\-\.]+$', v.upper()):
            raise ValueError(f"Invalid symbol format: {v}")
        return v.upper()
    
    @field_validator('day_high')
    @classmethod
    def validate_high_low(cls, v, info):
        """Ensure high is greater than or equal to low"""
        if 'day_low' in info.data and v < info.data['day_low']:
            raise ValueError("Day high must be >= day low")
        return v


@dataclass
class StockPrice:
    """Stock price data model (legacy dataclass for compatibility)"""
    symbol: str
    current_price: float
    previous_close: float
    open_price: float
    day_high: float
    day_low: float
    volume: int
    market_cap: Optional[float] = None
    timestamp: Optional[datetime] = None


class CompanyInfoModel(BaseModel):
    """Company information data model with validation"""
    symbol: str = Field(..., min_length=1, max_length=10)
    name: str = Field(..., min_length=1)
    sector: Optional[str] = None
    industry: Optional[str] = None
    country: Optional[str] = None
    website: Optional[str] = Field(None, pattern=r'^https?://')
    description: Optional[str] = Field(None, max_length=5000)
    employees: Optional[int] = Field(None, ge=0)
    market_cap: Optional[float] = Field(None, ge=0)
    
    @field_validator('symbol')
    @classmethod
    def validate_symbol(cls, v):
        """Validate stock symbol format"""
        if not re.match(r'^[A-Z0-9\-\.]+$', v.upper()):
            raise ValueError(f"Invalid symbol format: {v}")
        return v.upper()


@dataclass
class CompanyInfo:
    """Company information data model (legacy dataclass for compatibility)"""
    symbol: str
    name: str
    sector: Optional[str] = None
    industry: Optional[str] = None
    country: Optional[str] = None
    website: Optional[str] = None
    description: Optional[str] = None
    employees: Optional[int] = None
    market_cap: Optional[float] = None


class YahooFinanceDataProvider:
    """
    Yahoo Finance Data Provider
    
    Provides real-time stock market data using the yfinance library.
    Implements caching and error handling for robust data fetching.
    """
    
    def __init__(
        self, 
        cache_ttl: int = 60, 
        validate_data: bool = True,
        rate_limit: int = 10,
        rate_period: float = 1.0,
        max_retries: int = 3,
        initial_retry_delay: float = 1.0,
        cache_max_size: int = 1000,
        persistent_cache: bool = False,
        cache_dir: Optional[str] = None,
        error_recovery_strategy: Optional[ErrorRecoveryStrategy] = None
    ):
        """
        Initialize the Yahoo Finance data provider.
        
        Args:
            cache_ttl: Cache time-to-live in seconds (default: 60)
            validate_data: Whether to validate data using Pydantic models (default: True)
            rate_limit: Maximum number of requests per rate_period (default: 10)
            rate_period: Time period for rate limiting in seconds (default: 1.0)
            max_retries: Maximum number of retry attempts (default: 3)
            initial_retry_delay: Initial delay between retries in seconds (default: 1.0)
            cache_max_size: Maximum number of items in cache (default: 1000)
            persistent_cache: Whether to persist cache to disk (default: False)
            cache_dir: Directory for persistent cache (default: ~/.yfinance_cache)
            error_recovery_strategy: Custom error recovery strategy (default: DefaultErrorRecoveryStrategy)
        """
        self.cache_ttl = cache_ttl
        self.validate_data = validate_data
        self.max_retries = max_retries
        self.initial_retry_delay = initial_retry_delay
        self.error_recovery_strategy = error_recovery_strategy or DefaultErrorRecoveryStrategy()
        
        # Initialize cache managers for different data types
        self._price_cache = CacheManager(
            ttl=cache_ttl,
            max_size=cache_max_size,
            persistent=persistent_cache,
            cache_dir=os.path.join(cache_dir, 'prices') if cache_dir else None
        )
        
        self._info_cache = CacheManager(
            ttl=cache_ttl * 10,  # Company info changes less frequently
            max_size=cache_max_size // 2,
            persistent=persistent_cache,
            cache_dir=os.path.join(cache_dir, 'info') if cache_dir else None
        )
        
        self._historical_cache = CacheManager(
            ttl=cache_ttl * 5,  # Historical data can be cached longer
            max_size=cache_max_size // 2,
            persistent=persistent_cache,
            cache_dir=os.path.join(cache_dir, 'historical') if cache_dir else None
        )
        
        # Simple caches for internal use
        self._ticker_cache: Dict[str, yf.Ticker] = {}
        self._valid_tickers_cache: Dict[str, bool] = {}
        
        # Initialize rate limiter
        self._rate_limiter = RateLimiter(rate=rate_limit, per=rate_period)
        
        # Connection pool settings for yfinance
        # Configure yfinance to use connection pooling
        import requests
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        
        session = requests.Session()
        retry = Retry(
            total=3,
            backoff_factor=0.3,
            status_forcelist=[500, 502, 503, 504]
        )
        adapter = HTTPAdapter(
            pool_connections=10,
            pool_maxsize=20,
            max_retries=retry
        )
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        
        # Set the session for yfinance (if supported in the version)
        try:
            yf.set_tz_cache_location("/tmp/yfinance_cache")
        except:
            pass  # Older versions might not support this
            
        logger.info(
            f"YahooFinanceDataProvider initialized with cache_ttl={cache_ttl}s, "
            f"validate_data={validate_data}, rate_limit={rate_limit}/{rate_period}s, "
            f"max_retries={max_retries}, cache_max_size={cache_max_size}, "
            f"persistent_cache={persistent_cache}"
        )
    
    def _get_ticker(self, symbol: str) -> yf.Ticker:
        """
        Get or create a ticker object with caching.
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL', 'MSFT')
            
        Returns:
            yf.Ticker object
        """
        # Normalize symbol
        symbol = symbol.upper().strip()
        
        if symbol not in self._ticker_cache:
            self._ticker_cache[symbol] = yf.Ticker(symbol)
            logger.debug(f"Created new ticker object for {symbol}")
        return self._ticker_cache[symbol]
    
    def _validate_ticker(self, symbol: str) -> bool:
        """
        Validate if a ticker symbol exists.
        
        Args:
            symbol: Stock symbol to validate
            
        Returns:
            bool: True if ticker is valid, False otherwise
        """
        symbol = symbol.upper().strip()
        
        # Check cache first
        if symbol in self._valid_tickers_cache:
            return self._valid_tickers_cache[symbol]
        
        try:
            ticker = self._get_ticker(symbol)
            info = ticker.info
            
            # Check if we got valid data back
            is_valid = bool(info and 'symbol' in info)
            self._valid_tickers_cache[symbol] = is_valid
            
            return is_valid
        except Exception as e:
            logger.debug(f"Ticker validation failed for {symbol}: {str(e)}")
            self._valid_tickers_cache[symbol] = False
            return False
    
    def _normalize_price_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize price data from various Yahoo Finance response formats.
        
        Args:
            data: Raw data from Yahoo Finance
            
        Returns:
            Normalized data dictionary
        """
        # Handle different key variations
        normalized = {}
        
        # Price mappings
        price_keys = [
            ('regularMarketPrice', 'currentPrice', 'price'),
            ('regularMarketPreviousClose', 'previousClose'),
            ('regularMarketOpen', 'open'),
            ('regularMarketDayHigh', 'dayHigh'),
            ('regularMarketDayLow', 'dayLow'),
            ('regularMarketVolume', 'volume'),
            ('marketCap',)
        ]
        
        for key_group in price_keys:
            for key in key_group:
                if key in data and data[key] is not None:
                    # Use the first key in the group as the normalized key
                    normalized_key = key_group[0] if len(key_group) > 1 else key
                    normalized[normalized_key] = data[key]
                    break
        
        return normalized
    
    def get_current_price(self, symbol: str) -> Optional[StockPrice]:
        """
        Get current stock price information.
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL', 'MSFT')
            
        Returns:
            StockPrice object or None if error occurs
        """
        symbol = symbol.upper().strip()
        
        # Check cache first
        cached_data = self._price_cache.get(symbol)
        if cached_data is not None:
            logger.debug(f"Returning cached price for {symbol}")
            return cached_data
        
        # Apply rate limiting
        self._rate_limiter.acquire()
        
        @retry_with_exponential_backoff(
            max_retries=self.max_retries,
            initial_delay=self.initial_retry_delay,
            exceptions=(Exception,)
        )
        def _fetch_price():
            ticker = self._get_ticker(symbol)
            info = ticker.info
            
            # Validate ticker first
            if not self._validate_ticker(symbol):
                logger.warning(f"Invalid ticker symbol: {symbol}")
                return None
            
            # Normalize the data
            normalized = self._normalize_price_data(info)
            
            # Extract essential price information with defaults
            current_price = normalized.get('regularMarketPrice', 0)
            
            if current_price == 0:
                logger.warning(f"No valid price data for {symbol}")
                return None
            
            stock_price_data = {
                'symbol': symbol.upper(),
                'current_price': current_price,
                'previous_close': normalized.get('regularMarketPreviousClose', 0),
                'open_price': normalized.get('regularMarketOpen', 0),
                'day_high': normalized.get('regularMarketDayHigh', 0),
                'day_low': normalized.get('regularMarketDayLow', 0),
                'volume': normalized.get('regularMarketVolume', 0),
                'market_cap': normalized.get('marketCap'),
                'timestamp': datetime.now()
            }
            
            # Validate data if enabled
            if self.validate_data:
                try:
                    validated = StockPriceModel(**stock_price_data)
                    stock_price = StockPrice(**validated.model_dump())
                except Exception as e:
                    logger.error(f"Data validation failed for {symbol}: {str(e)}")
                    return None
            else:
                stock_price = StockPrice(**stock_price_data)
            
            logger.info(f"Successfully fetched price for {symbol}: ${current_price}")
            return stock_price
        
        try:
            result = _fetch_price()
            if result:
                # Cache the result
                self._price_cache.set(symbol, result)
            return result
        except Exception as e:
            logger.error(f"Failed to fetch price for {symbol} after retries: {str(e)}")
            return None
    
    def get_historical_data(
        self, 
        symbol: str, 
        period: Union[str, DataPeriod] = DataPeriod.ONE_MONTH,
        interval: Union[str, DataInterval] = DataInterval.ONE_DAY,
        start: Optional[Union[str, datetime]] = None,
        end: Optional[Union[str, datetime]] = None
    ) -> Optional[pd.DataFrame]:
        """
        Get historical stock data.
        
        Args:
            symbol: Stock symbol
            period: Data period (used when start/end not specified)
            interval: Data interval (granularity)
            start: Start date (optional)
            end: End date (optional)
            
        Returns:
            pandas DataFrame with historical data or None if error occurs
        """
        symbol = symbol.upper().strip()
        
        # Create cache key
        cache_key = f"{symbol}_{period}_{interval}_{start}_{end}"
        
        # Check cache first
        cached_data = self._historical_cache.get(cache_key)
        if cached_data is not None:
            logger.debug(f"Returning cached historical data for {symbol}")
            return cached_data
        
        # Apply rate limiting
        self._rate_limiter.acquire()
        
        @retry_with_exponential_backoff(
            max_retries=self.max_retries,
            initial_delay=self.initial_retry_delay,
            exceptions=(Exception,)
        )
        def _fetch_historical():
            ticker = self._get_ticker(symbol)
            
            # Convert enums to strings
            if isinstance(period, DataPeriod):
                period_str = period.value
            else:
                period_str = period
                
            if isinstance(interval, DataInterval):
                interval_str = interval.value
            else:
                interval_str = interval
            
            # Fetch data based on parameters
            if start and end:
                data = ticker.history(start=start, end=end, interval=interval_str)
            else:
                data = ticker.history(period=period_str, interval=interval_str)
            
            if data.empty:
                logger.warning(f"No historical data available for {symbol}")
                return None
                
            logger.info(f"Successfully fetched historical data for {symbol}: {len(data)} rows")
            return data
        
        try:
            result = _fetch_historical()
            if result is not None and not result.empty:
                # Cache the result
                self._historical_cache.set(cache_key, result)
            return result
        except Exception as e:
            logger.error(f"Failed to fetch historical data for {symbol} after retries: {str(e)}")
            return None
    
    def get_company_info(self, symbol: str) -> Optional[CompanyInfo]:
        """
        Get company information.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            CompanyInfo object or None if error occurs
        """
        symbol = symbol.upper().strip()
        
        # Check cache first
        cached_data = self._info_cache.get(symbol)
        if cached_data is not None:
            logger.debug(f"Returning cached company info for {symbol}")
            return cached_data
        
        # Apply rate limiting
        self._rate_limiter.acquire()
        
        @retry_with_exponential_backoff(
            max_retries=self.max_retries,
            initial_delay=self.initial_retry_delay,
            exceptions=(Exception,)
        )
        def _fetch_info():
            ticker = self._get_ticker(symbol)
            info = ticker.info
            
            # Validate ticker first
            if not self._validate_ticker(symbol):
                logger.warning(f"Invalid ticker symbol: {symbol}")
                return None
            
            company_info_data = {
                'symbol': symbol.upper(),
                'name': info.get('longName', info.get('shortName', symbol)),
                'sector': info.get('sector'),
                'industry': info.get('industry'),
                'country': info.get('country'),
                'website': info.get('website'),
                'description': info.get('longBusinessSummary'),
                'employees': info.get('fullTimeEmployees'),
                'market_cap': info.get('marketCap')
            }
            
            # Validate data if enabled
            if self.validate_data:
                try:
                    validated = CompanyInfoModel(**company_info_data)
                    company_info = CompanyInfo(**validated.model_dump())
                except Exception as e:
                    logger.error(f"Data validation failed for {symbol}: {str(e)}")
                    # Return with basic info even if validation fails
                    company_info = CompanyInfo(
                        symbol=symbol.upper(),
                        name=company_info_data['name']
                    )
            else:
                company_info = CompanyInfo(**company_info_data)
            
            logger.info(f"Successfully fetched company info for {symbol}: {company_info.name}")
            return company_info
        
        try:
            result = _fetch_info()
            if result:
                # Cache the result
                self._info_cache.set(symbol, result)
            return result
        except Exception as e:
            logger.error(f"Failed to fetch company info for {symbol} after retries: {str(e)}")
            return None
    
    def get_financial_statements(
        self, 
        symbol: str, 
        statement_type: str = 'all'
    ) -> Optional[Dict[str, pd.DataFrame]]:
        """
        Get financial statements for a company.
        
        Args:
            symbol: Stock symbol
            statement_type: Type of statement ('income', 'balance', 'cash', 'all')
            
        Returns:
            Dictionary of financial statements or None if error occurs
        """
        symbol = symbol.upper().strip()
        
        # Apply rate limiting
        self._rate_limiter.acquire()
        
        @retry_with_exponential_backoff(
            max_retries=self.max_retries,
            initial_delay=self.initial_retry_delay,
            exceptions=(Exception,)
        )
        def _fetch_statements():
            ticker = self._get_ticker(symbol)
            statements = {}
            
            if statement_type in ['income', 'all']:
                statements['income'] = ticker.financials
                statements['quarterly_income'] = ticker.quarterly_financials
                
            if statement_type in ['balance', 'all']:
                statements['balance'] = ticker.balance_sheet
                statements['quarterly_balance'] = ticker.quarterly_balance_sheet
                
            if statement_type in ['cash', 'all']:
                statements['cashflow'] = ticker.cashflow
                statements['quarterly_cashflow'] = ticker.quarterly_cashflow
            
            # Remove empty dataframes
            statements = {k: v for k, v in statements.items() if not v.empty}
            
            if not statements:
                logger.warning(f"No financial statements available for {symbol}")
                return None
                
            logger.info(f"Successfully fetched financial statements for {symbol}: {list(statements.keys())}")
            return statements
        
        try:
            return _fetch_statements()
        except Exception as e:
            logger.error(f"Failed to fetch financial statements for {symbol} after retries: {str(e)}")
            return None
    
    def clear_cache(self, symbol: Optional[str] = None) -> None:
        """
        Clear cached data.
        
        Args:
            symbol: Specific symbol to clear from cache, or None to clear all
        """
        if symbol:
            symbol = symbol.upper().strip()
            # Clear from all cache managers
            self._price_cache.delete(symbol)
            self._info_cache.delete(symbol)
            # Clear historical data for this symbol (all variations)
            # This is a simple approach - in production you might want more sophisticated key matching
            stats = self._historical_cache.get_stats()
            if stats['size'] > 0:
                # For now, just log that historical cache exists
                logger.info(f"Note: Historical cache contains {stats['size']} entries")
            
            # Clear from simple caches
            if symbol in self._valid_tickers_cache:
                del self._valid_tickers_cache[symbol]
            if symbol in self._ticker_cache:
                del self._ticker_cache[symbol]
            logger.info(f"Cleared cache for {symbol}")
        else:
            # Clear all caches
            self._price_cache.clear()
            self._info_cache.clear()
            self._historical_cache.clear()
            self._valid_tickers_cache.clear()
            self._ticker_cache.clear()
            logger.info("Cleared all caches")
    
    def get_rate_limiter_stats(self) -> Dict[str, Any]:
        """
        Get rate limiter statistics.
        
        Returns:
            Dictionary with rate limiter information
        """
        with self._rate_limiter.lock:
            return {
                'rate': self._rate_limiter.rate,
                'period': self._rate_limiter.per,
                'current_requests': len(self._rate_limiter.request_times),
                'available_requests': self._rate_limiter.rate - len(self._rate_limiter.request_times)
            }
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive cache statistics.
        
        Returns:
            Dictionary with cache statistics for all cache types
        """
        return {
            'price_cache': self._price_cache.get_stats(),
            'info_cache': self._info_cache.get_stats(),
            'historical_cache': self._historical_cache.get_stats(),
            'ticker_cache_size': len(self._ticker_cache),
            'valid_tickers_cache_size': len(self._valid_tickers_cache)
        }
    
    def cleanup_expired_cache(self) -> Dict[str, int]:
        """
        Clean up expired items from all caches.
        
        Returns:
            Dictionary with number of items removed from each cache
        """
        return {
            'price_cache': self._price_cache.cleanup_expired(),
            'info_cache': self._info_cache.cleanup_expired(),
            'historical_cache': self._historical_cache.cleanup_expired()
        }
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check on the data provider.
        
        Returns:
            Dictionary with health status information
        """
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'checks': {},
            'errors': []
        }
        
        # Check rate limiter
        try:
            rate_stats = self.get_rate_limiter_stats()
            health_status['checks']['rate_limiter'] = {
                'status': 'ok',
                'available_requests': rate_stats['available_requests']
            }
        except Exception as e:
            health_status['checks']['rate_limiter'] = {'status': 'error', 'error': str(e)}
            health_status['errors'].append(f"Rate limiter error: {e}")
            
        # Check cache health
        try:
            cache_stats = self.get_cache_stats()
            total_size = sum(
                stats.get('size', 0) for name, stats in cache_stats.items()
                if isinstance(stats, dict)
            )
            health_status['checks']['cache'] = {
                'status': 'ok',
                'total_items': total_size
            }
        except Exception as e:
            health_status['checks']['cache'] = {'status': 'error', 'error': str(e)}
            health_status['errors'].append(f"Cache error: {e}")
            
        # Check API connectivity with a test symbol
        try:
            test_price = self.get_current_price('AAPL')
            if test_price:
                health_status['checks']['api_connectivity'] = {'status': 'ok'}
            else:
                health_status['checks']['api_connectivity'] = {
                    'status': 'degraded',
                    'message': 'API returned no data'
                }
        except Exception as e:
            health_status['checks']['api_connectivity'] = {'status': 'error', 'error': str(e)}
            health_status['errors'].append(f"API connectivity error: {e}")
            
        # Check error recovery strategy
        if hasattr(self.error_recovery_strategy, 'get_error_stats'):
            error_stats = self.error_recovery_strategy.get_error_stats()
            health_status['checks']['error_recovery'] = {
                'status': 'ok',
                'total_errors': error_stats['total_errors']
            }
            
        # Determine overall health
        if health_status['errors']:
            health_status['status'] = 'unhealthy'
        elif any(check.get('status') == 'degraded' for check in health_status['checks'].values()):
            health_status['status'] = 'degraded'
            
        return health_status
    
    def _handle_error(self, error: Exception, method: str, symbol: str, **kwargs) -> Optional[Any]:
        """
        Handle errors using the configured recovery strategy.
        
        Args:
            error: The exception that occurred
            method: The method where error occurred
            symbol: The symbol being processed
            **kwargs: Additional context
            
        Returns:
            Recovery result or None
        """
        context = {
            'method': method,
            'symbol': symbol,
            'timestamp': datetime.now(),
            **kwargs
        }
        
        # Classify the error
        if isinstance(error, (ConnectionError, TimeoutError)):
            classified_error = NetworkError(str(error))
        elif "Invalid" in str(error) or "not found" in str(error).lower():
            classified_error = InvalidTickerError(str(error))
        elif "rate limit" in str(error).lower():
            classified_error = RateLimitError(str(error))
        elif isinstance(error, (ValueError, TypeError)):
            classified_error = DataValidationError(str(error))
        else:
            classified_error = DataFetchError(str(error))
            
        return self.error_recovery_strategy.handle_error(classified_error, context)


# Test code for module
if __name__ == "__main__":
    # Add console handler for testing
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)
    
    # Run tests with enhanced caching
    provider = YahooFinanceDataProvider(
        rate_limit=5, 
        rate_period=1.0,
        cache_ttl=60,
        cache_max_size=100,
        persistent_cache=True,
        cache_dir="/tmp/yfinance_test_cache"
    )
    
    # Test current price with caching
    print("\n=== Testing current price with caching ===")
    price1 = provider.get_current_price("AAPL")
    if price1:
        print(f"AAPL current price (1st call): ${price1.current_price}")
    
    price2 = provider.get_current_price("AAPL")  # Should hit cache
    if price2:
        print(f"AAPL current price (2nd call - cached): ${price2.current_price}")
    
    # Test company info
    print("\n=== Testing company info ===")
    info = provider.get_company_info("MSFT")
    if info:
        print(f"MSFT company name: {info.name}")
    
    # Test historical data caching
    print("\n=== Testing historical data caching ===")
    start_hist = time.time()
    hist1 = provider.get_historical_data("AAPL", period="5d", interval="1d")
    if hist1 is not None:
        print(f"Fetched {len(hist1)} rows of historical data in {time.time() - start_hist:.2f}s")
    
    start_hist2 = time.time()
    hist2 = provider.get_historical_data("AAPL", period="5d", interval="1d")  # Should hit cache
    if hist2 is not None:
        print(f"Fetched {len(hist2)} rows (cached) in {time.time() - start_hist2:.2f}s")
    
    # Test cache statistics
    print("\n=== Cache statistics ===")
    cache_stats = provider.get_cache_stats()
    for cache_name, stats in cache_stats.items():
        if isinstance(stats, dict):
            print(f"\n{cache_name}:")
            print(f"  Size: {stats.get('size', 'N/A')}/{stats.get('max_size', 'N/A')}")
            print(f"  Hit rate: {stats.get('hit_rate', 0):.2%}")
            print(f"  Hits: {stats.get('hits', 0)}, Misses: {stats.get('misses', 0)}")
        else:
            print(f"{cache_name}: {stats}")
    
    # Test rate limiter stats
    print("\n=== Rate limiter stats ===")
    stats = provider.get_rate_limiter_stats()
    print(f"Rate limiter: {stats}")
    
    # Test rate limiting with multiple rapid requests
    print("\n=== Testing rate limiting ===")
    symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META"]
    start_time = time.time()
    for symbol in symbols:
        price = provider.get_current_price(symbol)
        if price:
            print(f"{symbol}: ${price.current_price}")
    elapsed = time.time() - start_time
    print(f"Fetched {len(symbols)} prices in {elapsed:.2f} seconds")
    
    # Test cache cleanup
    print("\n=== Testing cache cleanup ===")
    cleanup_stats = provider.cleanup_expired_cache()
    print(f"Expired items removed: {cleanup_stats}")
    
    # Test clearing cache for specific symbol
    print("\n=== Testing cache clear ===")
    provider.clear_cache("AAPL")
    
    # Final cache stats
    print("\n=== Final cache statistics ===")
    final_stats = provider.get_cache_stats()
    print(f"Price cache size: {final_stats['price_cache']['size']}")
    print(f"Info cache size: {final_stats['info_cache']['size']}")
    print(f"Historical cache size: {final_stats['historical_cache']['size']}")
    
    # Test health check
    print("\n=== Health Check ===")
    health = provider.health_check()
    print(f"Overall status: {health['status']}")
    for check_name, check_result in health['checks'].items():
        print(f"  {check_name}: {check_result['status']}")
    
    # Test error handling with invalid symbol
    print("\n=== Testing error handling ===")
    invalid_result = provider.get_current_price("INVALID_TICKER_XYZ123")
    print(f"Invalid ticker result: {invalid_result}")
    
    # Show error recovery stats
    if hasattr(provider.error_recovery_strategy, 'get_error_stats'):
        error_stats = provider.error_recovery_strategy.get_error_stats()
        print(f"\nError statistics:")
        print(f"  Total errors: {error_stats['total_errors']}")
        print(f"  Error counts by endpoint: {error_stats['error_counts']}")