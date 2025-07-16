"""
Simple in-memory cache for FinnHub data
"""

import time
from typing import Any, Optional, Dict, Tuple
from datetime import datetime, timedelta


class InMemoryCache:
    """Simple thread-safe in-memory cache with TTL support"""
    
    def __init__(self):
        self._cache: Dict[str, Tuple[Any, float]] = {}
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache if not expired.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        if key in self._cache:
            value, expiry = self._cache[key]
            if time.time() < expiry:
                return value
            else:
                # Remove expired entry
                del self._cache[key]
        return None
    
    def set(self, key: str, value: Any, ttl: int = 300):
        """
        Set value in cache with TTL.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (default: 5 minutes)
        """
        expiry = time.time() + ttl
        self._cache[key] = (value, expiry)
    
    def clear(self):
        """Clear all cache entries"""
        self._cache.clear()
    
    def delete(self, key: str):
        """Delete specific cache entry"""
        if key in self._cache:
            del self._cache[key]