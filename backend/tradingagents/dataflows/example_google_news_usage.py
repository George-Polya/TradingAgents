"""
Example usage of the GoogleNewsProvider

This script demonstrates how to use the new GoogleNewsProvider
for various news scraping tasks.
"""

from datetime import datetime, timedelta
from google_news_provider import GoogleNewsProvider, create_google_news_provider


def main():
    # Create a provider instance with custom configuration
    provider = create_google_news_provider(
        cache_ttl=3600,      # 1 hour cache
        rate_limit=0.5,      # 0.5 requests per second
        max_retries=3,       # Retry failed requests up to 3 times
        proxy_url=None,      # No proxy (set if needed)
        respect_robots=True  # Respect robots.txt
    )
    
    print("=== Google News Provider Example ===\n")
    
    # Example 1: Basic news search
    print("1. Basic News Search")
    print("-" * 50)
    
    articles = provider.search_news(
        query="artificial intelligence",
        start_date="2024-01-01",
        end_date="2024-01-07",
        max_results=5
    )
    
    for i, article in enumerate(articles, 1):
        print(f"\nArticle {i}:")
        print(f"  Title: {article.title}")
        print(f"  Source: {article.source}")
        print(f"  Date: {article.date}")
        print(f"  Snippet: {article.snippet[:100]}...")
        print(f"  URL: {article.url}")
    
    # Example 2: Company-specific news
    print("\n\n2. Company News Search")
    print("-" * 50)
    
    company_news = provider.get_company_news(
        ticker="AAPL",
        days_back=7,
        max_results=3
    )
    
    print(f"\nFound {len(company_news)} articles for AAPL:")
    for article in company_news:
        print(f"  - {article.title} ({article.source}, {article.date})")
    
    # Example 3: Market sentiment by sector
    print("\n\n3. Market Sentiment News")
    print("-" * 50)
    
    sentiment_news = provider.get_market_sentiment_news(
        sectors=["technology", "healthcare"],
        days_back=1,
        max_results=3
    )
    
    for sector, articles in sentiment_news.items():
        print(f"\n{sector.capitalize()} Sector ({len(articles)} articles):")
        for article in articles[:2]:  # Show first 2
            print(f"  - {article.title} ({article.date})")
    
    # Example 4: Breaking news
    print("\n\n4. Breaking News")
    print("-" * 50)
    
    breaking_news = provider.get_breaking_news(
        topics=["stock market crash", "federal reserve"],
        hours_back=24
    )
    
    print(f"\nFound {len(breaking_news)} breaking news articles:")
    for article in breaking_news:
        print(f"  - {article.title}")
        print(f"    {article.snippet[:80]}...")
    
    # Example 5: Cache statistics
    print("\n\n5. Cache Statistics")
    print("-" * 50)
    
    cache_stats = provider.cache.get_stats()
    print(f"\nCache Performance:")
    print(f"  - Size: {cache_stats['size']} entries")
    print(f"  - Hits: {cache_stats['hit_count']}")
    print(f"  - Misses: {cache_stats['miss_count']}")
    print(f"  - Hit Rate: {cache_stats['hit_rate']:.2%}")
    
    # Example 6: Health check
    print("\n\n6. Provider Health Check")
    print("-" * 50)
    
    health = provider.health_check()
    print(f"\nHealth Status: {health['status']}")
    if health['status'] == 'healthy':
        print(f"  - Test results: {health['test_results_count']} articles")
        print(f"  - Rate limit tokens: {health['rate_limit']['tokens']:.1f}/{health['rate_limit']['burst']}")
    else:
        print(f"  - Error: {health.get('error', 'Unknown')}")
    
    # Example 7: Using date ranges
    print("\n\n7. Custom Date Range Search")
    print("-" * 50)
    
    # Search for news in a specific date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    historical_news = provider.search_news(
        query="Tesla stock",
        start_date=start_date,
        end_date=end_date,
        max_results=5,
        use_cache=False  # Don't use cache for this search
    )
    
    print(f"\nNews for 'Tesla stock' from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}:")
    print(f"Found {len(historical_news)} articles")
    
    # Example 8: Error handling
    print("\n\n8. Error Handling Example")
    print("-" * 50)
    
    try:
        # Try to search with invalid dates
        articles = provider.search_news(
            query="test",
            start_date="2024-13-01",  # Invalid month
            end_date="2024-01-01"
        )
    except Exception as e:
        print(f"\nCaught expected error: {type(e).__name__}: {e}")
    
    # Clear cache at the end
    print("\n\nClearing cache...")
    provider.clear_cache()
    print("Cache cleared.")


if __name__ == "__main__":
    main()