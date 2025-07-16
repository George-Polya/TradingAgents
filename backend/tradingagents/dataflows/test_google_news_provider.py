"""
Test file for GoogleNewsProvider
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import requests
from bs4 import BeautifulSoup

from .google_news_provider import (
    GoogleNewsProvider,
    NewsArticle,
    CacheManager,
    RateLimiter,
    UserAgentRotator,
    GoogleNewsError,
    RateLimitError,
    ScrapingError
)


class TestNewsArticle:
    """Test NewsArticle data class"""
    
    def test_news_article_creation(self):
        """Test creating a news article"""
        article = NewsArticle(
            title="Test Title",
            snippet="Test snippet",
            source="Test Source",
            date="2024-01-01",
            url="https://example.com"
        )
        
        assert article.title == "Test Title"
        assert article.snippet == "Test snippet"
        assert article.source == "Test Source"
        assert article.date == "2024-01-01"
        assert article.url == "https://example.com"
        assert isinstance(article.timestamp, datetime)
    
    def test_news_article_to_dict(self):
        """Test converting news article to dictionary"""
        article = NewsArticle(
            title="Test Title",
            snippet="Test snippet",
            source="Test Source",
            date="2024-01-01",
            url="https://example.com"
        )
        
        article_dict = article.to_dict()
        assert article_dict['title'] == "Test Title"
        assert article_dict['snippet'] == "Test snippet"
        assert article_dict['source'] == "Test Source"
        assert article_dict['date'] == "2024-01-01"
        assert article_dict['url'] == "https://example.com"
        assert 'timestamp' in article_dict


class TestCacheManager:
    """Test CacheManager functionality"""
    
    def test_cache_set_and_get(self):
        """Test setting and getting from cache"""
        cache = CacheManager(max_size=10, default_ttl=300)
        
        # Set value
        cache.set("key1", "value1")
        
        # Get value
        assert cache.get("key1") == "value1"
        
        # Non-existent key
        assert cache.get("non_existent") is None
    
    def test_cache_expiry(self):
        """Test cache expiry"""
        cache = CacheManager(max_size=10, default_ttl=0.1)  # 100ms TTL
        
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
        
        # Wait for expiry
        import time
        time.sleep(0.2)
        
        assert cache.get("key1") is None
    
    def test_cache_lru_eviction(self):
        """Test LRU eviction when cache is full"""
        cache = CacheManager(max_size=3, default_ttl=300)
        
        # Fill cache
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        
        # Access key1 to make it most recently used
        cache.get("key1")
        
        # Add new item, should evict key2
        cache.set("key4", "value4")
        
        assert cache.get("key1") == "value1"  # Still present
        assert cache.get("key2") is None      # Evicted
        assert cache.get("key3") == "value3"  # Still present
        assert cache.get("key4") == "value4"  # New item
    
    def test_cache_stats(self):
        """Test cache statistics"""
        cache = CacheManager(max_size=10, default_ttl=300)
        
        # Initial stats
        stats = cache.get_stats()
        assert stats['size'] == 0
        assert stats['hit_count'] == 0
        assert stats['miss_count'] == 0
        
        # Add and access items
        cache.set("key1", "value1")
        cache.get("key1")  # Hit
        cache.get("key2")  # Miss
        
        stats = cache.get_stats()
        assert stats['size'] == 1
        assert stats['hit_count'] == 1
        assert stats['miss_count'] == 1
        assert stats['hit_rate'] == 0.5


class TestRateLimiter:
    """Test RateLimiter functionality"""
    
    def test_rate_limiter_basic(self):
        """Test basic rate limiting"""
        limiter = RateLimiter(rate=10.0, burst=5)  # 10 tokens/sec, burst of 5
        
        # Should not wait for first few requests
        assert limiter.acquire(1) == 0.0
        assert limiter.acquire(1) == 0.0
        
        # Consume all burst tokens
        limiter.acquire(3)
        
        # Next request should wait
        wait_time = limiter.acquire(1)
        assert wait_time > 0
    
    def test_rate_limiter_token_regeneration(self):
        """Test token regeneration over time"""
        limiter = RateLimiter(rate=10.0, burst=5)
        
        # Consume all tokens
        limiter.acquire(5)
        
        # Wait for tokens to regenerate
        import time
        time.sleep(0.2)  # Should regenerate 2 tokens
        
        # Should not wait for 1-2 tokens
        assert limiter.acquire(1) == 0.0


class TestUserAgentRotator:
    """Test UserAgentRotator functionality"""
    
    def test_user_agent_rotation(self):
        """Test that user agents rotate"""
        rotator = UserAgentRotator()
        
        # Get multiple user agents
        agents = [rotator.get_user_agent() for _ in range(10)]
        
        # Should have different agents
        assert len(set(agents)) > 1
        
        # All should be valid strings
        for agent in agents:
            assert isinstance(agent, str)
            assert len(agent) > 0


class TestGoogleNewsProvider:
    """Test GoogleNewsProvider functionality"""
    
    @pytest.fixture
    def provider(self):
        """Create a test provider instance"""
        return GoogleNewsProvider(
            cache_ttl=300,
            rate_limit=1.0,
            max_retries=2,
            respect_robots=False  # Disable for testing
        )
    
    @pytest.fixture
    def mock_html_response(self):
        """Create mock HTML response"""
        html = '''
        <html>
        <body>
            <div class="SoaBEf">
                <a href="https://example.com/article1">
                    <div class="MBeuO">Test Article 1</div>
                </a>
                <div class="GI74Re">This is a test snippet for article 1</div>
                <div class="LfVVr">1 day ago</div>
                <div class="NUnG9d"><span>Test Source</span></div>
            </div>
            <div class="SoaBEf">
                <a href="https://example.com/article2">
                    <div class="MBeuO">Test Article 2</div>
                </a>
                <div class="GI74Re">This is a test snippet for article 2</div>
                <div class="LfVVr">2 days ago</div>
                <div class="NUnG9d"><span>Another Source</span></div>
            </div>
        </body>
        </html>
        '''
        return html
    
    def test_parse_news_item(self, provider, mock_html_response):
        """Test parsing a single news item"""
        soup = BeautifulSoup(mock_html_response, 'html.parser')
        element = soup.select_one("div.SoaBEf")
        
        article = provider._parse_news_item(element)
        
        assert article is not None
        assert article.title == "Test Article 1"
        assert article.snippet == "This is a test snippet for article 1"
        assert article.source == "Test Source"
        assert article.date == "1 day ago"
        assert article.url == "https://example.com/article1"
    
    @patch('requests.Session.get')
    def test_search_news_basic(self, mock_get, provider, mock_html_response):
        """Test basic news search"""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = mock_html_response.encode()
        mock_response.text = mock_html_response
        mock_get.return_value = mock_response
        
        # Search news
        articles = provider.search_news(
            query="test query",
            start_date="2024-01-01",
            end_date="2024-01-07",
            max_results=10
        )
        
        assert len(articles) == 2
        assert articles[0].title == "Test Article 1"
        assert articles[1].title == "Test Article 2"
    
    @patch('requests.Session.get')
    def test_search_news_with_cache(self, mock_get, provider, mock_html_response):
        """Test that cache is used on repeated searches"""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = mock_html_response.encode()
        mock_response.text = mock_html_response
        mock_get.return_value = mock_response
        
        # First search
        articles1 = provider.search_news(
            query="test query",
            start_date="2024-01-01",
            end_date="2024-01-07"
        )
        
        # Second search (should use cache)
        articles2 = provider.search_news(
            query="test query",
            start_date="2024-01-01",
            end_date="2024-01-07"
        )
        
        # Should only call get once
        assert mock_get.call_count == 1
        
        # Results should be the same
        assert len(articles1) == len(articles2)
        assert articles1[0].title == articles2[0].title
    
    @patch('requests.Session.get')
    def test_search_news_rate_limit_error(self, mock_get, provider):
        """Test handling of rate limit errors"""
        # Mock rate limited response
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.text = "Too Many Requests"
        mock_get.return_value = mock_response
        
        # Should raise after retries
        with pytest.raises(ScrapingError):
            provider.search_news(
                query="test query",
                start_date="2024-01-01",
                end_date="2024-01-07"
            )
    
    @patch('requests.Session.get')
    def test_get_company_news(self, mock_get, provider, mock_html_response):
        """Test company-specific news search"""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = mock_html_response.encode()
        mock_response.text = mock_html_response
        mock_get.return_value = mock_response
        
        # Get company news
        articles = provider.get_company_news(
            ticker="AAPL",
            days_back=7,
            max_results=10
        )
        
        assert len(articles) == 2
        # Check that the query was formatted correctly
        call_args = mock_get.call_args[0][0]
        assert "AAPL" in call_args
    
    @patch('requests.Session.get')
    def test_get_market_sentiment_news(self, mock_get, provider, mock_html_response):
        """Test market sentiment news by sector"""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = mock_html_response.encode()
        mock_response.text = mock_html_response
        mock_get.return_value = mock_response
        
        # Get sentiment news
        results = provider.get_market_sentiment_news(
            sectors=["technology", "healthcare"],
            days_back=1,
            max_results=10
        )
        
        assert "technology" in results
        assert "healthcare" in results
        assert len(results["technology"]) == 2
        assert len(results["healthcare"]) == 2
    
    @patch('requests.Session.get')
    def test_get_breaking_news(self, mock_get, provider, mock_html_response):
        """Test breaking news search"""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = mock_html_response.encode()
        mock_response.text = mock_html_response
        mock_get.return_value = mock_response
        
        # Get breaking news
        articles = provider.get_breaking_news(
            topics=["stock market", "economy"],
            hours_back=4
        )
        
        assert len(articles) == 2
        # Should not use cache for breaking news
        assert provider.cache.get_stats()['hit_count'] == 0
    
    @patch('requests.Session.get')
    def test_health_check(self, mock_get, provider, mock_html_response):
        """Test health check functionality"""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = mock_html_response.encode()
        mock_response.text = mock_html_response
        mock_get.return_value = mock_response
        
        # Perform health check
        health = provider.health_check()
        
        assert health['status'] == 'healthy'
        assert 'test_results_count' in health
        assert 'cache_stats' in health
        assert 'rate_limit' in health
    
    def test_clear_cache(self, provider):
        """Test cache clearing"""
        # Add some items to cache
        provider.cache.set("key1", "value1")
        provider.cache.set("key2", "value2")
        
        assert provider.cache.get_stats()['size'] == 2
        
        # Clear cache
        provider.clear_cache()
        
        assert provider.cache.get_stats()['size'] == 0
        assert provider.cache.get("key1") is None
        assert provider.cache.get("key2") is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])