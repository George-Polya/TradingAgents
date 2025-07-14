"""
Integration tests for Yahoo Finance Data Provider

These tests interact with the real Yahoo Finance API.
They should be run sparingly to avoid rate limiting.
"""

import unittest
import time
from datetime import datetime, timedelta
import pandas as pd

from tradingagents.dataflows.yahoo_finance_provider import (
    YahooFinanceDataProvider,
    DataPeriod,
    DataInterval
)


class TestYahooFinanceIntegration(unittest.TestCase):
    """Integration tests for YahooFinanceDataProvider with real API"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures once for all tests"""
        cls.provider = YahooFinanceDataProvider(cache_ttl=60, validate_data=True)
        cls.test_symbols = ['AAPL', 'MSFT', 'GOOGL']
        cls.invalid_symbol = 'XXXINVALIDXXX'
        
    def setUp(self):
        """Add delay between tests to avoid rate limiting"""
        time.sleep(1)  # 1 second delay between tests
        
    def test_real_current_price(self):
        """Test fetching real current price data"""
        for symbol in self.test_symbols:
            with self.subTest(symbol=symbol):
                result = self.provider.get_current_price(symbol)
                
                self.assertIsNotNone(result)
                self.assertEqual(result.symbol, symbol)
                self.assertGreater(result.current_price, 0)
                self.assertGreater(result.volume, 0)
                self.assertIsNotNone(result.timestamp)
                
                # Verify price relationships
                self.assertLessEqual(result.day_low, result.current_price)
                self.assertGreaterEqual(result.day_high, result.current_price)
                self.assertLessEqual(result.day_low, result.day_high)
                
    def test_invalid_ticker(self):
        """Test handling of invalid ticker symbols"""
        result = self.provider.get_current_price(self.invalid_symbol)
        self.assertIsNone(result)
        
    def test_ticker_validation(self):
        """Test ticker validation functionality"""
        # Valid tickers
        for symbol in self.test_symbols:
            self.assertTrue(self.provider._validate_ticker(symbol))
            
        # Invalid ticker
        self.assertFalse(self.provider._validate_ticker(self.invalid_symbol))
        
        # Test caching - second call should be faster
        start = time.time()
        self.provider._validate_ticker('AAPL')
        cached_time = time.time() - start
        
        self.assertLess(cached_time, 0.01)  # Should be very fast from cache
        
    def test_real_historical_data(self):
        """Test fetching real historical data"""
        symbol = 'AAPL'
        
        # Test with period
        data = self.provider.get_historical_data(
            symbol,
            period=DataPeriod.ONE_MONTH,
            interval=DataInterval.ONE_DAY
        )
        
        self.assertIsNotNone(data)
        self.assertIsInstance(data, pd.DataFrame)
        self.assertGreater(len(data), 15)  # At least 15 trading days in a month
        self.assertIn('Close', data.columns)
        self.assertIn('Volume', data.columns)
        
        # Test with date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        data_range = self.provider.get_historical_data(
            symbol,
            start=start_date.strftime('%Y-%m-%d'),
            end=end_date.strftime('%Y-%m-%d'),
            interval=DataInterval.ONE_DAY
        )
        
        self.assertIsNotNone(data_range)
        self.assertGreater(len(data_range), 0)
        
    def test_real_company_info(self):
        """Test fetching real company information"""
        for symbol in self.test_symbols:
            with self.subTest(symbol=symbol):
                result = self.provider.get_company_info(symbol)
                
                self.assertIsNotNone(result)
                self.assertEqual(result.symbol, symbol)
                self.assertIsNotNone(result.name)
                self.assertNotEqual(result.name, symbol)  # Should have full name
                
                # Most tech companies should have these fields
                if symbol in ['AAPL', 'MSFT', 'GOOGL']:
                    self.assertIsNotNone(result.sector)
                    self.assertIsNotNone(result.country)
                    self.assertIsNotNone(result.website)
                    
    def test_real_financial_statements(self):
        """Test fetching real financial statements"""
        symbol = 'AAPL'
        
        # Test all statements
        all_statements = self.provider.get_financial_statements(symbol, 'all')
        
        self.assertIsNotNone(all_statements)
        self.assertIsInstance(all_statements, dict)
        
        # Should have at least some statements
        self.assertGreater(len(all_statements), 0)
        
        # Check for expected statement types
        possible_keys = [
            'income', 'balance', 'cashflow',
            'quarterly_income', 'quarterly_balance', 'quarterly_cashflow'
        ]
        
        # At least one should be present
        has_statement = any(key in all_statements for key in possible_keys)
        self.assertTrue(has_statement)
        
        # Test specific statement type
        income_statements = self.provider.get_financial_statements(symbol, 'income')
        
        if income_statements:
            self.assertIn('income', income_statements)
            income_df = income_statements['income']
            self.assertIsInstance(income_df, pd.DataFrame)
            self.assertGreater(len(income_df.columns), 0)
            
    def test_data_normalization(self):
        """Test data normalization with different response formats"""
        symbol = 'AAPL'
        
        # Test normalization by checking consistent output
        result1 = self.provider.get_current_price(symbol)
        time.sleep(1)
        result2 = self.provider.get_current_price(symbol)
        
        # Both should have valid data
        self.assertIsNotNone(result1)
        self.assertIsNotNone(result2)
        
        # Structure should be consistent
        self.assertEqual(type(result1), type(result2))
        self.assertEqual(result1.symbol, result2.symbol)
        
    def test_case_insensitive_symbols(self):
        """Test that symbols are case-insensitive"""
        result_upper = self.provider.get_current_price('AAPL')
        result_lower = self.provider.get_current_price('aapl')
        result_mixed = self.provider.get_current_price('AaPl')
        
        self.assertIsNotNone(result_upper)
        self.assertIsNotNone(result_lower)
        self.assertIsNotNone(result_mixed)
        
        # All should return uppercase symbol
        self.assertEqual(result_upper.symbol, 'AAPL')
        self.assertEqual(result_lower.symbol, 'AAPL')
        self.assertEqual(result_mixed.symbol, 'AAPL')
        
    def test_weekend_holiday_handling(self):
        """Test handling of weekend/holiday data requests"""
        symbol = 'AAPL'
        
        # Try to get data for a weekend (adjust date as needed)
        weekend_date = '2024-01-06'  # Saturday
        
        # Historical data should still work but might not have data for that exact day
        data = self.provider.get_historical_data(
            symbol,
            start=weekend_date,
            end=weekend_date,
            interval=DataInterval.ONE_DAY
        )
        
        # Should either be None or empty, not error
        if data is not None:
            self.assertIsInstance(data, pd.DataFrame)


if __name__ == '__main__':
    # Run with verbose output
    unittest.main(verbosity=2)