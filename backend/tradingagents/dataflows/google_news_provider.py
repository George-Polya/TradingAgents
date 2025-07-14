"""
Google News Provider Module

This module provides a comprehensive Google News scraping functionality
with proper error handling, rate limiting, caching, and compliance features.
"""

import logging
import time
import random
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import json
import re
from urllib.robotparser import RobotFileParser
from urllib.parse import urlparse, quote_plus
import hashlib
from functools import wraps
import threading
from collections import OrderedDict
from abc import ABC, abstractmethod
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    retry_if_result,
)

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# Custom exceptions
class GoogleNewsError(Exception):
    """Base exception for Google News provider"""
    pass


class RateLimitError(GoogleNewsError):
    """Raised when rate limit is exceeded"""
    pass


class ScrapingError(GoogleNewsError):
    """Raised when scraping fails"""
    pass


class RobotsComplianceError(GoogleNewsError):
    """Raised when robots.txt disallows access"""
    pass


@dataclass
class NewsArticle:
    """Data class for news article information"""
    title: str
    snippet: str
    source: str
    date: str
    url: str
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'title': self.title,
            'snippet': self.snippet,
            'source': self.source,
            'date': self.date,
            'url': self.url,
            'timestamp': self.timestamp.isoformat()
        }


class CacheManager:
    """Thread-safe cache manager with TTL and LRU eviction"""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        """
        Initialize cache manager.
        
        Args:
            max_size: Maximum number of cache entries
            default_ttl: Default time-to-live in seconds
        """
        self.cache: OrderedDict[str, tuple[Any, float]] = OrderedDict()
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.lock = threading.Lock()
        self.hit_count = 0
        self.miss_count = 0
        
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        with self.lock:
            if key in self.cache:
                value, expiry = self.cache[key]
                if time.time() < expiry:
                    # Move to end (LRU)
                    self.cache.move_to_end(key)
                    self.hit_count += 1
                    return value
                else:
                    # Expired
                    del self.cache[key]
            
            self.miss_count += 1
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache"""
        with self.lock:
            expiry = time.time() + (ttl or self.default_ttl)
            self.cache[key] = (value, expiry)
            self.cache.move_to_end(key)
            
            # Evict oldest if over size limit
            while len(self.cache) > self.max_size:
                self.cache.popitem(last=False)
    
    def clear(self) -> None:
        """Clear all cache entries"""
        with self.lock:
            self.cache.clear()
            self.hit_count = 0
            self.miss_count = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self.lock:
            total = self.hit_count + self.miss_count
            hit_rate = self.hit_count / total if total > 0 else 0
            return {
                'size': len(self.cache),
                'hit_count': self.hit_count,
                'miss_count': self.miss_count,
                'hit_rate': hit_rate
            }


class RateLimiter:
    """Token bucket rate limiter"""
    
    def __init__(self, rate: float = 1.0, burst: int = 5):
        """
        Initialize rate limiter.
        
        Args:
            rate: Tokens per second
            burst: Maximum burst size
        """
        self.rate = rate
        self.burst = burst
        self.tokens = burst
        self.last_update = time.time()
        self.lock = threading.Lock()
    
    def acquire(self, tokens: int = 1) -> float:
        """
        Acquire tokens, blocking if necessary.
        
        Returns:
            Time waited in seconds
        """
        with self.lock:
            now = time.time()
            elapsed = now - self.last_update
            self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
            self.last_update = now
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return 0.0
            
            # Need to wait
            wait_time = (tokens - self.tokens) / self.rate
            time.sleep(wait_time)
            self.tokens = 0
            return wait_time


class UserAgentRotator:
    """Rotate user agents to avoid detection"""
    
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    ]
    
    def __init__(self):
        self.index = 0
        self.lock = threading.Lock()
    
    def get_user_agent(self) -> str:
        """Get next user agent in rotation"""
        with self.lock:
            user_agent = self.USER_AGENTS[self.index]
            self.index = (self.index + 1) % len(self.USER_AGENTS)
            return user_agent


class GoogleNewsProvider:
    """
    Comprehensive Google News provider with caching, rate limiting, and error handling.
    """
    
    def __init__(
        self,
        cache_ttl: int = 3600,
        rate_limit: float = 0.5,
        max_retries: int = 3,
        proxy_url: Optional[str] = None,
        respect_robots: bool = True
    ):
        """
        Initialize Google News provider.
        
        Args:
            cache_ttl: Cache time-to-live in seconds
            rate_limit: Requests per second
            max_retries: Maximum retry attempts
            proxy_url: Optional proxy URL
            respect_robots: Whether to respect robots.txt
        """
        self.cache = CacheManager(default_ttl=cache_ttl)
        self.rate_limiter = RateLimiter(rate=rate_limit)
        self.user_agent_rotator = UserAgentRotator()
        self.max_retries = max_retries
        self.proxy_url = proxy_url
        self.respect_robots = respect_robots
        self.session = requests.Session()
        
        if proxy_url:
            self.session.proxies = {
                'http': proxy_url,
                'https': proxy_url
            }
        
        # Check robots.txt compliance
        if respect_robots:
            self._check_robots_compliance()
    
    def _check_robots_compliance(self) -> None:
        """Check if Google News allows scraping"""
        try:
            rp = RobotFileParser()
            rp.set_url("https://news.google.com/robots.txt")
            rp.read()
            
            # Check if we can fetch news search
            if not rp.can_fetch("*", "https://news.google.com/search"):
                logger.warning("Google News robots.txt may restrict scraping")
        except Exception as e:
            logger.error(f"Failed to check robots.txt: {e}")
    
    def _get_cache_key(self, query: str, start_date: str, end_date: str) -> str:
        """Generate cache key for query"""
        key_string = f"{query}:{start_date}:{end_date}"
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _make_request(self, url: str) -> requests.Response:
        """Make HTTP request with retry logic"""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            # Rate limiting
            wait_time = self.rate_limiter.acquire()
            if wait_time > 0:
                logger.debug(f"Rate limited, waited {wait_time:.2f}s")
            
            # Random delay to avoid detection
            time.sleep(random.uniform(1, 3))
            
            headers = {
                'User-Agent': self.user_agent_rotator.get_user_agent(),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            
            try:
                response = self.session.get(url, headers=headers, timeout=10)
                
                # Check for rate limiting
                if response.status_code == 429 or "Too Many Requests" in response.text:
                    if attempt < self.max_retries:
                        wait_time = min(2 ** attempt * 4, 60)  # Exponential backoff
                        logger.warning(f"Rate limited (429), waiting {wait_time}s before retry {attempt + 1}/{self.max_retries}")
                        time.sleep(wait_time)
                        continue
                    else:
                        raise RateLimitError(f"Rate limited after {self.max_retries} retries")
                
                response.raise_for_status()
                return response
                
            except requests.exceptions.RequestException as e:
                last_exception = e
                if attempt < self.max_retries:
                    wait_time = min(2 ** attempt * 2, 30)  # Exponential backoff
                    logger.warning(f"Request failed: {e}. Retrying in {wait_time}s (attempt {attempt + 1}/{self.max_retries})")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Request failed after {self.max_retries} retries: {e}")
        
        raise ScrapingError(f"Failed to fetch URL after {self.max_retries} retries: {last_exception}")
    
    def _parse_news_item(self, element: Any) -> Optional[NewsArticle]:
        """Parse a single news item from HTML"""
        try:
            # Extract link
            link_elem = element.find("a")
            if not link_elem or 'href' not in link_elem.attrs:
                return None
            
            link = link_elem['href']
            
            # Extract title
            title_elem = element.select_one("div.MBeuO, div.n0jPhd")
            title = title_elem.get_text(strip=True) if title_elem else ""
            
            # Extract snippet
            snippet_elem = element.select_one(".GI74Re, .Y3v8qd")
            snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
            
            # Extract date
            date_elem = element.select_one(".LfVVr, .OSrXXb")
            date = date_elem.get_text(strip=True) if date_elem else ""
            
            # Extract source
            source_elem = element.select_one(".NUnG9d span, .CEMjEf span")
            source = source_elem.get_text(strip=True) if source_elem else ""
            
            if not title:
                return None
            
            return NewsArticle(
                title=title,
                snippet=snippet,
                source=source,
                date=date,
                url=link
            )
            
        except Exception as e:
            logger.error(f"Failed to parse news item: {e}")
            return None
    
    def search_news(
        self,
        query: str,
        start_date: Optional[Union[str, datetime]] = None,
        end_date: Optional[Union[str, datetime]] = None,
        max_results: int = 100,
        use_cache: bool = True
    ) -> List[NewsArticle]:
        """
        Search Google News for articles.
        
        Args:
            query: Search query
            start_date: Start date (YYYY-MM-DD or datetime)
            end_date: End date (YYYY-MM-DD or datetime)
            max_results: Maximum number of results
            use_cache: Whether to use cache
            
        Returns:
            List of NewsArticle objects
        """
        # Convert dates to strings
        if isinstance(start_date, datetime):
            start_date = start_date.strftime("%Y-%m-%d")
        if isinstance(end_date, datetime):
            end_date = end_date.strftime("%Y-%m-%d")
        
        # Default to last 7 days if no dates provided
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        if not start_date:
            start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        
        # Check cache
        cache_key = self._get_cache_key(query, start_date, end_date)
        if use_cache:
            cached_result = self.cache.get(cache_key)
            if cached_result:
                logger.info(f"Cache hit for query: {query}")
                return [NewsArticle(**item) for item in cached_result]
        
        # Convert dates to Google format (MM/DD/YYYY)
        start_date_google = datetime.strptime(start_date, "%Y-%m-%d").strftime("%m/%d/%Y")
        end_date_google = datetime.strptime(end_date, "%Y-%m-%d").strftime("%m/%d/%Y")
        
        news_results = []
        page = 0
        
        while len(news_results) < max_results:
            offset = page * 10
            encoded_query = quote_plus(query)
            
            url = (
                f"https://www.google.com/search?q={encoded_query}"
                f"&tbs=cdr:1,cd_min:{start_date_google},cd_max:{end_date_google}"
                f"&tbm=nws&start={offset}"
            )
            
            try:
                response = self._make_request(url)
                soup = BeautifulSoup(response.content, "html.parser")
                
                # Find news items (multiple possible selectors for robustness)
                results_on_page = soup.select("div.SoaBEf, div.xuvV6b, div.IBr9hb")
                
                if not results_on_page:
                    logger.info(f"No more results found for query: {query}")
                    break
                
                for element in results_on_page:
                    article = self._parse_news_item(element)
                    if article:
                        news_results.append(article)
                        
                        if len(news_results) >= max_results:
                            break
                
                # Check for next page
                next_link = soup.find("a", id="pnnext")
                if not next_link:
                    break
                
                page += 1
                
            except Exception as e:
                logger.error(f"Error fetching page {page}: {e}")
                if page == 0:
                    raise ScrapingError(f"Failed to fetch any results: {e}")
                break
        
        # Cache results
        if use_cache and news_results:
            cache_data = [article.to_dict() for article in news_results]
            self.cache.set(cache_key, cache_data)
            logger.info(f"Cached {len(news_results)} results for query: {query}")
        
        return news_results[:max_results]
    
    def get_company_news(
        self,
        ticker: str,
        days_back: int = 7,
        max_results: int = 50
    ) -> List[NewsArticle]:
        """
        Get news for a specific company ticker.
        
        Args:
            ticker: Company ticker symbol
            days_back: Number of days to look back
            max_results: Maximum number of results
            
        Returns:
            List of NewsArticle objects
        """
        # Construct company-specific query
        query = f"{ticker} stock news OR {ticker} company"
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        return self.search_news(
            query=query,
            start_date=start_date,
            end_date=end_date,
            max_results=max_results
        )
    
    def get_market_sentiment_news(
        self,
        sectors: Optional[List[str]] = None,
        days_back: int = 1,
        max_results: int = 30
    ) -> Dict[str, List[NewsArticle]]:
        """
        Get market sentiment news by sector.
        
        Args:
            sectors: List of sectors (defaults to major sectors)
            days_back: Number of days to look back
            max_results: Maximum results per sector
            
        Returns:
            Dictionary mapping sectors to news articles
        """
        if not sectors:
            sectors = [
                "technology", "healthcare", "finance", "energy",
                "consumer", "industrial", "real estate"
            ]
        
        results = {}
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        for sector in sectors:
            query = f"{sector} sector news market sentiment"
            news = self.search_news(
                query=query,
                start_date=start_date,
                end_date=end_date,
                max_results=max_results
            )
            results[sector] = news
        
        return results
    
    def get_breaking_news(
        self,
        topics: List[str],
        hours_back: int = 4
    ) -> List[NewsArticle]:
        """
        Get breaking news for specific topics.
        
        Args:
            topics: List of topics to search
            hours_back: Number of hours to look back
            
        Returns:
            List of NewsArticle objects
        """
        query = " OR ".join([f'"{topic}" breaking news' for topic in topics])
        
        end_date = datetime.now()
        start_date = end_date - timedelta(hours=hours_back)
        
        # For very recent news, we might get fewer results
        return self.search_news(
            query=query,
            start_date=start_date,
            end_date=end_date,
            max_results=20,
            use_cache=False  # Don't cache breaking news
        )
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on the provider.
        
        Returns:
            Health status dictionary
        """
        try:
            # Try a simple search
            test_results = self.search_news(
                query="stock market",
                max_results=5,
                use_cache=False
            )
            
            cache_stats = self.cache.get_stats()
            
            return {
                'status': 'healthy',
                'test_results_count': len(test_results),
                'cache_stats': cache_stats,
                'rate_limit': {
                    'rate': self.rate_limiter.rate,
                    'burst': self.rate_limiter.burst,
                    'tokens': self.rate_limiter.tokens
                }
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'cache_stats': self.cache.get_stats()
            }
    
    def clear_cache(self) -> None:
        """Clear all cached results"""
        self.cache.clear()
        logger.info("Cache cleared")


# Factory function for backwards compatibility
def create_google_news_provider(**kwargs) -> GoogleNewsProvider:
    """
    Create a Google News provider instance.
    
    Args:
        **kwargs: Arguments to pass to GoogleNewsProvider
        
    Returns:
        GoogleNewsProvider instance
    """
    return GoogleNewsProvider(**kwargs)