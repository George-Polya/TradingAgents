"""
Unit tests for Yahoo Finance Data Provider Module

This module tests the YahooFinanceDataProvider class functionality
including data fetching, error handling, and caching.
"""

import unittest
from unittest.mock import patch, MagicMock, call
from datetime import datetime, timedelta
import pandas as pd
import yfinance as yf
import time

from tradingagents.dataflows.yahoo_finance_provider import (
    YahooFinanceDataProvider,
    StockPrice,
    CompanyInfo,
    DataPeriod,
    DataInterval,
    RateLimiter,
    retry_with_exponential_backoff,
    CacheManager,
    YahooFinanceError,
    InvalidTickerError,
    NetworkError,
    DataValidationError,
    DefaultErrorRecoveryStrategy
)


class TestYahooFinanceDataProvider(unittest.TestCase):
    """Test cases for YahooFinanceDataProvider"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.provider = YahooFinanceDataProvider(cache_ttl=60)
        
    def test_initialization(self):
        """Test provider initialization"""
        self.assertEqual(self.provider.cache_ttl, 60)
        self.assertIsInstance(self.provider._ticker_cache, dict)
        
    @patch('yfinance.Ticker')
    def test_get_ticker_caching(self, mock_ticker):
        """Test ticker object caching"""
        mock_ticker_instance = MagicMock()
        mock_ticker.return_value = mock_ticker_instance
        
        # First call should create new ticker
        ticker1 = self.provider._get_ticker('AAPL')
        self.assertEqual(ticker1, mock_ticker_instance)
        mock_ticker.assert_called_once_with('AAPL')
        
        # Second call should return cached ticker
        ticker2 = self.provider._get_ticker('AAPL')
        self.assertEqual(ticker2, ticker1)
        # Should still be called only once
        mock_ticker.assert_called_once()
        
    @patch('yfinance.Ticker')
    def test_get_current_price_success(self, mock_ticker):
        """Test successful price fetching"""
        mock_ticker_instance = MagicMock()
        mock_ticker.return_value = mock_ticker_instance
        
        # Mock ticker info
        mock_ticker_instance.info = {
            'regularMarketPrice': 150.25,
            'previousClose': 149.80,
            'regularMarketOpen': 149.90,
            'dayHigh': 151.00,
            'dayLow': 149.50,
            'volume': 1000000,
            'marketCap': 2500000000000,
            'symbol': 'AAPL'  # Add symbol for validation
        }
        
        with patch.object(self.provider, '_validate_ticker', return_value=True):
            result = self.provider.get_current_price('AAPL')
        
            self.assertIsInstance(result, StockPrice)
            self.assertEqual(result.symbol, 'AAPL')
            self.assertEqual(result.current_price, 150.25)
            self.assertEqual(result.previous_close, 149.80)
            self.assertEqual(result.open_price, 149.90)
            self.assertEqual(result.day_high, 151.00)
            self.assertEqual(result.day_low, 149.50)
            self.assertEqual(result.volume, 1000000)
            self.assertEqual(result.market_cap, 2500000000000)
            self.assertIsInstance(result.timestamp, datetime)
        
    @patch('yfinance.Ticker')
    def test_get_current_price_error(self, mock_ticker):
        """Test price fetching error handling"""
        mock_ticker.side_effect = Exception("Network error")
        
        result = self.provider.get_current_price('INVALID')
        
        self.assertIsNone(result)
        
    @patch('yfinance.Ticker')
    def test_get_historical_data_with_period(self, mock_ticker):
        """Test historical data fetching with period"""
        mock_ticker_instance = MagicMock()
        mock_ticker.return_value = mock_ticker_instance
        
        # Create mock dataframe
        mock_data = pd.DataFrame({
            'Date': pd.date_range(start='2024-01-01', periods=5),
            'Open': [100, 101, 102, 103, 104],
            'High': [101, 102, 103, 104, 105],
            'Low': [99, 100, 101, 102, 103],
            'Close': [100.5, 101.5, 102.5, 103.5, 104.5],
            'Volume': [1000000, 1100000, 1200000, 1300000, 1400000]
        })
        
        mock_ticker_instance.history.return_value = mock_data
        
        result = self.provider.get_historical_data(
            'AAPL',
            period=DataPeriod.ONE_MONTH,
            interval=DataInterval.ONE_DAY
        )
        
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 5)
        mock_ticker_instance.history.assert_called_once_with(
            period='1mo',
            interval='1d'
        )
        
    @patch('yfinance.Ticker')
    def test_get_historical_data_with_dates(self, mock_ticker):
        """Test historical data fetching with start/end dates"""
        mock_ticker_instance = MagicMock()
        mock_ticker.return_value = mock_ticker_instance
        
        mock_data = pd.DataFrame({'Close': [100, 101, 102]})
        mock_ticker_instance.history.return_value = mock_data
        
        start = '2024-01-01'
        end = '2024-01-31'
        
        result = self.provider.get_historical_data(
            'AAPL',
            start=start,
            end=end,
            interval='1d'
        )
        
        self.assertIsInstance(result, pd.DataFrame)
        mock_ticker_instance.history.assert_called_once_with(
            start=start,
            end=end,
            interval='1d'
        )
        
    @patch('yfinance.Ticker')
    def test_get_historical_data_empty(self, mock_ticker):
        """Test historical data when no data available"""
        mock_ticker_instance = MagicMock()
        mock_ticker.return_value = mock_ticker_instance
        
        mock_ticker_instance.history.return_value = pd.DataFrame()
        
        result = self.provider.get_historical_data('INVALID')
        
        self.assertIsNone(result)
        
    @patch('yfinance.Ticker')
    def test_get_company_info_success(self, mock_ticker):
        """Test company info fetching"""
        mock_ticker_instance = MagicMock()
        mock_ticker.return_value = mock_ticker_instance
        
        mock_ticker_instance.info = {
            'longName': 'Apple Inc.',
            'sector': 'Technology',
            'industry': 'Consumer Electronics',
            'country': 'United States',
            'website': 'https://www.apple.com',
            'longBusinessSummary': 'Apple designs and manufactures...',
            'fullTimeEmployees': 150000,
            'marketCap': 2500000000000,
            'symbol': 'AAPL'
        }
        
        with patch.object(self.provider, '_validate_ticker', return_value=True):
            result = self.provider.get_company_info('AAPL')
        
            self.assertIsInstance(result, CompanyInfo)
            self.assertEqual(result.symbol, 'AAPL')
            self.assertEqual(result.name, 'Apple Inc.')
            self.assertEqual(result.sector, 'Technology')
            self.assertEqual(result.industry, 'Consumer Electronics')
            self.assertEqual(result.country, 'United States')
            self.assertEqual(result.website, 'https://www.apple.com')
            self.assertIn('Apple designs', result.description)
            self.assertEqual(result.employees, 150000)
            self.assertEqual(result.market_cap, 2500000000000)
        
    @patch('yfinance.Ticker')
    def test_get_company_info_minimal(self, mock_ticker):
        """Test company info with minimal data"""
        mock_ticker_instance = MagicMock()
        mock_ticker.return_value = mock_ticker_instance
        
        # Only symbol returned
        mock_ticker_instance.info = {'symbol': 'UNKNOWN'}
        
        with patch.object(self.provider, '_validate_ticker', return_value=True):
            result = self.provider.get_company_info('UNKNOWN')
        
            self.assertIsInstance(result, CompanyInfo)
            self.assertEqual(result.symbol, 'UNKNOWN')
            self.assertEqual(result.name, 'UNKNOWN')  # Falls back to symbol
            self.assertIsNone(result.sector)
        
    @patch('yfinance.Ticker')
    def test_get_financial_statements_all(self, mock_ticker):
        """Test fetching all financial statements"""
        mock_ticker_instance = MagicMock()
        mock_ticker.return_value = mock_ticker_instance
        
        # Create mock financial data
        mock_income = pd.DataFrame({'Revenue': [1000, 1100, 1200]})
        mock_balance = pd.DataFrame({'Assets': [5000, 5500, 6000]})
        mock_cash = pd.DataFrame({'Cash': [100, 110, 120]})
        
        mock_ticker_instance.financials = mock_income
        mock_ticker_instance.quarterly_financials = mock_income
        mock_ticker_instance.balance_sheet = mock_balance
        mock_ticker_instance.quarterly_balance_sheet = mock_balance
        mock_ticker_instance.cashflow = mock_cash
        mock_ticker_instance.quarterly_cashflow = mock_cash
        
        result = self.provider.get_financial_statements('AAPL', 'all')
        
        self.assertIsInstance(result, dict)
        self.assertIn('income', result)
        self.assertIn('balance', result)
        self.assertIn('cashflow', result)
        self.assertIn('quarterly_income', result)
        self.assertIn('quarterly_balance', result)
        self.assertIn('quarterly_cashflow', result)
        
    @patch('yfinance.Ticker')
    def test_get_financial_statements_specific(self, mock_ticker):
        """Test fetching specific financial statement"""
        mock_ticker_instance = MagicMock()
        mock_ticker.return_value = mock_ticker_instance
        
        mock_income = pd.DataFrame({'Revenue': [1000, 1100, 1200]})
        mock_ticker_instance.financials = mock_income
        mock_ticker_instance.quarterly_financials = mock_income
        
        result = self.provider.get_financial_statements('AAPL', 'income')
        
        self.assertIsInstance(result, dict)
        self.assertIn('income', result)
        self.assertIn('quarterly_income', result)
        self.assertNotIn('balance', result)
        self.assertNotIn('cashflow', result)
        
    @patch('yfinance.Ticker')
    def test_get_financial_statements_empty(self, mock_ticker):
        """Test financial statements when no data available"""
        mock_ticker_instance = MagicMock()
        mock_ticker.return_value = mock_ticker_instance
        
        # All statements are empty
        mock_ticker_instance.financials = pd.DataFrame()
        mock_ticker_instance.quarterly_financials = pd.DataFrame()
        mock_ticker_instance.balance_sheet = pd.DataFrame()
        mock_ticker_instance.quarterly_balance_sheet = pd.DataFrame()
        mock_ticker_instance.cashflow = pd.DataFrame()
        mock_ticker_instance.quarterly_cashflow = pd.DataFrame()
        
        result = self.provider.get_financial_statements('INVALID')
        
        self.assertIsNone(result)
        
    def test_data_period_enum(self):
        """Test DataPeriod enum values"""
        self.assertEqual(DataPeriod.ONE_DAY.value, '1d')
        self.assertEqual(DataPeriod.ONE_MONTH.value, '1mo')
        self.assertEqual(DataPeriod.ONE_YEAR.value, '1y')
        
    def test_data_interval_enum(self):
        """Test DataInterval enum values"""
        self.assertEqual(DataInterval.ONE_MINUTE.value, '1m')
        self.assertEqual(DataInterval.ONE_DAY.value, '1d')
        self.assertEqual(DataInterval.ONE_WEEK.value, '1wk')


class TestRateLimiter(unittest.TestCase):
    """Test cases for RateLimiter"""
    
    def test_rate_limiter_initialization(self):
        """Test rate limiter initialization"""
        limiter = RateLimiter(rate=5, per=1.0)
        self.assertEqual(limiter.rate, 5)
        self.assertEqual(limiter.per, 1.0)
        
    def test_rate_limiting_blocking(self):
        """Test that rate limiter blocks when limit is exceeded"""
        limiter = RateLimiter(rate=2, per=0.5)  # 2 requests per 0.5 seconds
        
        start = time.time()
        
        # First two requests should be immediate
        limiter.acquire()
        limiter.acquire()
        
        # Third request should be delayed
        limiter.acquire()
        
        elapsed = time.time() - start
        
        # Should have taken at least 0.5 seconds
        self.assertGreaterEqual(elapsed, 0.5)
        
    def test_rate_limiting_cleanup(self):
        """Test that old requests are cleaned up"""
        limiter = RateLimiter(rate=2, per=0.5)
        
        # Make two requests
        limiter.acquire()
        limiter.acquire()
        
        # Wait for cleanup
        time.sleep(0.6)
        
        # Should be able to make more requests immediately
        start = time.time()
        limiter.acquire()
        elapsed = time.time() - start
        
        # Should be immediate (less than 0.1 seconds)
        self.assertLess(elapsed, 0.1)


class TestRetryDecorator(unittest.TestCase):
    """Test cases for retry_with_exponential_backoff decorator"""
    
    def test_retry_success_first_attempt(self):
        """Test function succeeds on first attempt"""
        mock_func = MagicMock(return_value="success")
        
        @retry_with_exponential_backoff(max_retries=3, initial_delay=0.1)
        def test_func():
            return mock_func()
            
        result = test_func()
        
        self.assertEqual(result, "success")
        self.assertEqual(mock_func.call_count, 1)
        
    def test_retry_success_after_failures(self):
        """Test function succeeds after failures"""
        mock_func = MagicMock(side_effect=[Exception("fail"), Exception("fail"), "success"])
        
        @retry_with_exponential_backoff(max_retries=3, initial_delay=0.01, max_delay=0.02)
        def test_func():
            return mock_func()
            
        result = test_func()
        
        self.assertEqual(result, "success")
        self.assertEqual(mock_func.call_count, 3)
        
    def test_retry_all_attempts_fail(self):
        """Test function fails after all retries"""
        mock_func = MagicMock(side_effect=Exception("always fails"))
        
        @retry_with_exponential_backoff(max_retries=2, initial_delay=0.01)
        def test_func():
            return mock_func()
            
        with self.assertRaises(Exception) as context:
            test_func()
            
        self.assertEqual(str(context.exception), "always fails")
        self.assertEqual(mock_func.call_count, 3)  # initial + 2 retries


class TestCacheManager(unittest.TestCase):
    """Test cases for CacheManager"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.cache = CacheManager(ttl=1, max_size=3, persistent=False)
        
    def test_cache_manager_initialization(self):
        """Test cache manager initialization"""
        self.assertEqual(self.cache.ttl, 1)
        self.assertEqual(self.cache.max_size, 3)
        self.assertFalse(self.cache.persistent)
        
    def test_cache_set_and_get(self):
        """Test basic cache operations"""
        # Test set and get
        self.cache.set('key1', 'value1')
        self.assertEqual(self.cache.get('key1'), 'value1')
        
        # Test cache miss
        self.assertIsNone(self.cache.get('nonexistent'))
        
    def test_cache_expiration(self):
        """Test cache TTL expiration"""
        self.cache.set('key1', 'value1')
        self.assertEqual(self.cache.get('key1'), 'value1')
        
        # Wait for expiration
        time.sleep(1.1)
        self.assertIsNone(self.cache.get('key1'))
        
    def test_cache_lru_eviction(self):
        """Test LRU eviction when cache is full"""
        # Fill cache to capacity
        self.cache.set('key1', 'value1')
        self.cache.set('key2', 'value2')
        self.cache.set('key3', 'value3')
        
        # Access key1 to make it recently used
        self.cache.get('key1')
        
        # Add new item, should evict key2 (oldest non-accessed)
        self.cache.set('key4', 'value4')
        
        # Check that key2 was evicted
        self.assertIsNotNone(self.cache.get('key1'))
        self.assertIsNone(self.cache.get('key2'))
        self.assertIsNotNone(self.cache.get('key3'))
        self.assertIsNotNone(self.cache.get('key4'))
        
    def test_cache_statistics(self):
        """Test cache statistics tracking"""
        # Initial stats
        stats = self.cache.get_stats()
        self.assertEqual(stats['hits'], 0)
        self.assertEqual(stats['misses'], 0)
        
        # Add and retrieve items
        self.cache.set('key1', 'value1')
        self.cache.get('key1')  # Hit
        self.cache.get('key2')  # Miss
        
        stats = self.cache.get_stats()
        self.assertEqual(stats['hits'], 1)
        self.assertEqual(stats['misses'], 1)
        self.assertEqual(stats['hit_rate'], 0.5)
        
    def test_cache_delete(self):
        """Test cache deletion"""
        self.cache.set('key1', 'value1')
        self.assertTrue(self.cache.delete('key1'))
        self.assertIsNone(self.cache.get('key1'))
        self.assertFalse(self.cache.delete('key1'))  # Already deleted
        
    def test_cache_clear(self):
        """Test cache clearing"""
        self.cache.set('key1', 'value1')
        self.cache.set('key2', 'value2')
        
        self.cache.clear()
        
        stats = self.cache.get_stats()
        self.assertEqual(stats['size'], 0)
        self.assertIsNone(self.cache.get('key1'))
        self.assertIsNone(self.cache.get('key2'))
        
    def test_cleanup_expired(self):
        """Test cleanup of expired items"""
        self.cache.set('key1', 'value1')
        self.cache.set('key2', 'value2')
        
        # Wait for partial expiration
        time.sleep(0.5)
        self.cache.set('key3', 'value3')
        
        # Wait for key1 and key2 to expire
        time.sleep(0.6)
        
        removed = self.cache.cleanup_expired()
        self.assertEqual(removed, 2)
        
        # Only key3 should remain
        stats = self.cache.get_stats()
        self.assertEqual(stats['size'], 1)


class TestCachingAndRateLimiting(unittest.TestCase):
    """Test cases for caching and rate limiting integration"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.provider = YahooFinanceDataProvider(
            cache_ttl=1,  # 1 second cache
            rate_limit=2,
            rate_period=1.0,
            max_retries=2
        )
        
    @patch('yfinance.Ticker')
    def test_price_caching(self, mock_ticker):
        """Test that prices are cached"""
        mock_ticker_instance = MagicMock()
        mock_ticker.return_value = mock_ticker_instance
        
        mock_ticker_instance.info = {
            'regularMarketPrice': 150.25,
            'previousClose': 149.80,
            'regularMarketOpen': 149.90,
            'dayHigh': 151.00,
            'dayLow': 149.50,
            'volume': 1000000,
            'marketCap': 2500000000000,
            'symbol': 'AAPL'
        }
        
        with patch.object(self.provider, '_validate_ticker', return_value=True):
            # First call
            result1 = self.provider.get_current_price('AAPL')
            self.assertIsNotNone(result1)
            initial_call_count = mock_ticker.call_count
            
            # Second call should use cache
            result2 = self.provider.get_current_price('AAPL')
            self.assertIsNotNone(result2)
            self.assertEqual(result1.current_price, result2.current_price)
            self.assertEqual(mock_ticker.call_count, initial_call_count)  # Still same call count
            
            # Wait for cache to expire
            time.sleep(1.1)
            
            # Third call should fetch new data
            result3 = self.provider.get_current_price('AAPL')
            self.assertIsNotNone(result3)
            # Should have called ticker at least once more
            self.assertGreater(mock_ticker.call_count, initial_call_count)
        
    @patch('yfinance.Ticker')
    def test_info_caching(self, mock_ticker):
        """Test that company info is cached"""
        mock_ticker_instance = MagicMock()
        mock_ticker.return_value = mock_ticker_instance
        
        mock_ticker_instance.info = {
            'longName': 'Apple Inc.',
            'sector': 'Technology',
            'symbol': 'AAPL'
        }
        
        with patch.object(self.provider, '_validate_ticker', return_value=True):
            # First call
            result1 = self.provider.get_company_info('AAPL')
            self.assertIsNotNone(result1)
            
            # Second call should use cache
            result2 = self.provider.get_company_info('AAPL')
            self.assertEqual(result1.name, result2.name)
            
            # Check that ticker was created only once
            self.assertEqual(len(self.provider._ticker_cache), 1)
        
    def test_clear_cache(self):
        """Test cache clearing functionality"""
        # Add some test data to caches
        test_price = StockPrice(
            symbol='TEST',
            current_price=100,
            previous_close=99,
            open_price=99.5,
            day_high=101,
            day_low=98,
            volume=1000000
        )
        
        test_info = CompanyInfo(
            symbol='TEST',
            name='Test Company'
        )
        
        self.provider._price_cache.set('TEST', test_price)
        self.provider._info_cache.set('TEST', test_info)
        self.provider._valid_tickers_cache['TEST'] = True
        
        # Clear specific symbol
        self.provider.clear_cache('TEST')
        
        self.assertIsNone(self.provider._price_cache.get('TEST'))
        self.assertIsNone(self.provider._info_cache.get('TEST'))
        self.assertNotIn('TEST', self.provider._valid_tickers_cache)
        
        # Add data again
        self.provider._price_cache.set('TEST', test_price)
        self.provider._info_cache.set('TEST', test_info)
        
        # Clear all caches
        self.provider.clear_cache()
        
        cache_stats = self.provider.get_cache_stats()
        self.assertEqual(cache_stats['price_cache']['size'], 0)
        self.assertEqual(cache_stats['info_cache']['size'], 0)
        self.assertEqual(len(self.provider._valid_tickers_cache), 0)
        
    def test_rate_limiter_stats(self):
        """Test rate limiter statistics"""
        stats = self.provider.get_rate_limiter_stats()
        
        self.assertIn('rate', stats)
        self.assertIn('period', stats)
        self.assertIn('current_requests', stats)
        self.assertIn('available_requests', stats)
        
        self.assertEqual(stats['rate'], 2)
        self.assertEqual(stats['period'], 1.0)
        self.assertEqual(stats['current_requests'], 0)
        self.assertEqual(stats['available_requests'], 2)
        
    def test_cache_stats(self):
        """Test comprehensive cache statistics"""
        # Get initial stats
        stats = self.provider.get_cache_stats()
        
        self.assertIn('price_cache', stats)
        self.assertIn('info_cache', stats)
        self.assertIn('historical_cache', stats)
        self.assertIn('ticker_cache_size', stats)
        self.assertIn('valid_tickers_cache_size', stats)
        
        # Each cache should have statistics
        for cache_name in ['price_cache', 'info_cache', 'historical_cache']:
            cache_stats = stats[cache_name]
            self.assertIn('size', cache_stats)
            self.assertIn('max_size', cache_stats)
            self.assertIn('ttl', cache_stats)
            self.assertIn('hits', cache_stats)
            self.assertIn('misses', cache_stats)
            self.assertIn('hit_rate', cache_stats)


class TestErrorHandling(unittest.TestCase):
    """Test cases for error handling and recovery"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.recovery_strategy = DefaultErrorRecoveryStrategy()
        self.provider = YahooFinanceDataProvider(
            error_recovery_strategy=self.recovery_strategy
        )
        
    def test_error_recovery_strategy_initialization(self):
        """Test error recovery strategy initialization"""
        self.assertIsInstance(self.provider.error_recovery_strategy, DefaultErrorRecoveryStrategy)
        self.assertEqual(len(self.recovery_strategy.error_counts), 0)
        
    def test_invalid_ticker_error_handling(self):
        """Test handling of invalid ticker errors"""
        error = InvalidTickerError("Invalid ticker: XYZ")
        context = {'method': 'get_current_price', 'symbol': 'XYZ'}
        
        result = self.recovery_strategy.handle_error(error, context)
        self.assertIsNone(result)
        self.assertEqual(self.recovery_strategy.error_counts['get_current_price:XYZ'], 1)
        
    def test_network_error_handling(self):
        """Test handling of network errors"""
        error = NetworkError("Connection timeout")
        context = {'method': 'get_current_price', 'symbol': 'AAPL'}
        
        result = self.recovery_strategy.handle_error(error, context)
        self.assertIsNone(result)  # No fallback configured
        
    def test_data_validation_error_with_raw_data(self):
        """Test data validation error with raw data fallback"""
        error = DataValidationError("Invalid data format")
        raw_data = {'price': 100}
        context = {
            'method': 'get_current_price',
            'symbol': 'AAPL',
            'raw_data': raw_data
        }
        
        result = self.recovery_strategy.handle_error(error, context)
        self.assertEqual(result, raw_data)
        
    def test_error_statistics(self):
        """Test error statistics tracking"""
        # Generate some errors
        errors = [
            (InvalidTickerError("Invalid"), {'method': 'get_price', 'symbol': 'XYZ'}),
            (NetworkError("Timeout"), {'method': 'get_price', 'symbol': 'AAPL'}),
            (InvalidTickerError("Invalid"), {'method': 'get_price', 'symbol': 'XYZ'})
        ]
        
        for error, context in errors:
            self.recovery_strategy.handle_error(error, context)
            
        stats = self.recovery_strategy.get_error_stats()
        self.assertEqual(stats['total_errors'], 3)
        self.assertEqual(stats['error_counts']['get_price:XYZ'], 2)
        self.assertEqual(stats['error_counts']['get_price:AAPL'], 1)
        
    def test_health_check(self):
        """Test health check functionality"""
        with patch.object(self.provider, 'get_current_price', return_value=StockPrice(
            symbol='AAPL',
            current_price=150,
            previous_close=149,
            open_price=149.5,
            day_high=151,
            day_low=149,
            volume=1000000
        )):
            health = self.provider.health_check()
            
            self.assertEqual(health['status'], 'healthy')
            self.assertIn('timestamp', health)
            self.assertIn('checks', health)
            self.assertIn('rate_limiter', health['checks'])
            self.assertIn('cache', health['checks'])
            self.assertIn('api_connectivity', health['checks'])
            
            # All checks should be ok
            for check in health['checks'].values():
                self.assertEqual(check['status'], 'ok')
                
    def test_health_check_degraded(self):
        """Test health check with degraded status"""
        with patch.object(self.provider, 'get_current_price', return_value=None):
            health = self.provider.health_check()
            
            # API connectivity should be degraded
            self.assertEqual(health['checks']['api_connectivity']['status'], 'degraded')
            self.assertEqual(health['status'], 'degraded')
            
    def test_health_check_unhealthy(self):
        """Test health check with errors"""
        with patch.object(self.provider, 'get_current_price', side_effect=Exception("API Error")):
            health = self.provider.health_check()
            
            self.assertEqual(health['status'], 'unhealthy')
            self.assertGreater(len(health['errors']), 0)
            self.assertEqual(health['checks']['api_connectivity']['status'], 'error')


if __name__ == '__main__':
    unittest.main()