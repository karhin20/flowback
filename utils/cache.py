import json
import asyncio
from typing import Any, Optional, Dict, List
from datetime import datetime, timedelta
from functools import wraps
import hashlib

class MemoryCache:
    """Simple in-memory cache with TTL support"""
    
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        async with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                if entry['expires_at'] > datetime.utcnow():
                    return entry['value']
                else:
                    # Expired, remove it
                    del self._cache[key]
            return None
    
    async def set(self, key: str, value: Any, ttl: int = 300) -> None:
        """Set value in cache with TTL in seconds"""
        async with self._lock:
            expires_at = datetime.utcnow() + timedelta(seconds=ttl)
            self._cache[key] = {
                'value': value,
                'expires_at': expires_at,
                'created_at': datetime.utcnow()
            }
    
    async def delete(self, key: str) -> None:
        """Delete key from cache"""
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
    
    async def clear(self) -> None:
        """Clear all cache entries"""
        async with self._lock:
            self._cache.clear()
    
    async def cleanup_expired(self) -> None:
        """Remove expired entries"""
        async with self._lock:
            now = datetime.utcnow()
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry['expires_at'] <= now
            ]
            for key in expired_keys:
                del self._cache[key]

# Global cache instance
cache = MemoryCache()

def cache_key(*args, **kwargs) -> str:
    """Generate cache key from arguments"""
    key_data = {
        'args': args,
        'kwargs': sorted(kwargs.items())
    }
    key_string = json.dumps(key_data, sort_keys=True, default=str)
    return hashlib.md5(key_string.encode()).hexdigest()

def cached(ttl: int = 300, key_prefix: str = ""):
    """Decorator for caching function results"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            key = f"{key_prefix}:{func.__name__}:{cache_key(*args, **kwargs)}"
            
            # Try to get from cache
            cached_result = await cache.get(key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            await cache.set(key, result, ttl)
            return result
        
        return wrapper
    return decorator

class CacheManager:
    """Cache manager for different data types"""
    
    # Cache TTLs in seconds
    CUSTOMER_TTL = 300  # 5 minutes
    DASHBOARD_TTL = 60  # 1 minute
    ACTIONS_TTL = 180   # 3 minutes
    
    @staticmethod
    async def invalidate_customer_cache(customer_id: Optional[str] = None):
        """Invalidate customer-related cache"""
        if customer_id:
            await cache.delete(f"customer:{customer_id}")
        # Invalidate all customer lists
        await cache.delete("customers:list")
        await cache.delete("customers:dashboard")
    
    @staticmethod
    async def invalidate_dashboard_cache():
        """Invalidate dashboard cache"""
        await cache.delete("dashboard:data")
    
    @staticmethod
    async def invalidate_actions_cache(customer_id: Optional[str] = None):
        """Invalidate actions cache"""
        if customer_id:
            await cache.delete(f"actions:customer:{customer_id}")
        await cache.delete("actions:list")
    
    @staticmethod
    async def invalidate_all_cache():
        """Invalidate all cache"""
        await cache.clear()

# Background task for cache cleanup
async def cleanup_cache_task():
    """Background task to clean up expired cache entries"""
    while True:
        try:
            await cache.cleanup_expired()
            await asyncio.sleep(60)  # Run every minute
        except Exception as e:
            print(f"Cache cleanup error: {e}")
            await asyncio.sleep(60)
