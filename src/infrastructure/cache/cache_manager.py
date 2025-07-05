"""
Caching layer for improved performance
"""

import logging
import threading
import time
from functools import wraps
from typing import Any, Dict, List, Optional

from src.infrastructure.database.database_optimizations import (
    OptimizedQueries,
    get_database_manager,
)

logger = logging.getLogger(__name__)


class InMemoryCache:
    """Simple in-memory cache with TTL support"""

    def __init__(self, default_ttl: int = 300):  # 5 minutes default
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._default_ttl = default_ttl
        self._stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
        }

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if key in self._cache:
            entry = self._cache[key]

            # Check if expired
            if entry["expires_at"] > time.time():
                self._stats["hits"] += 1
                return entry["value"]
            # Remove expired entry
            del self._cache[key]

        self._stats["misses"] += 1
        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache"""
        if ttl is None:
            ttl = self._default_ttl

        self._cache[key] = {
            "value": value,
            "expires_at": time.time() + ttl,
            "created_at": time.time(),
        }
        self._stats["sets"] += 1

    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if key in self._cache:
            del self._cache[key]
            self._stats["deletes"] += 1
            return True
        return False

    def clear(self) -> None:
        """Clear all cache entries"""
        self._cache.clear()
        self._stats = {k: 0 for k in self._stats}

    def cleanup_expired(self) -> int:
        """Remove expired entries and return count removed"""
        current_time = time.time()
        expired_keys = [
            key
            for key, entry in self._cache.items()
            if entry["expires_at"] <= current_time
        ]

        for key in expired_keys:
            del self._cache[key]

        return len(expired_keys)

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self._stats["hits"] + self._stats["misses"]
        hit_rate = (
            (self._stats["hits"] / total_requests * 100) if total_requests > 0 else 0
        )

        return {
            **self._stats,
            "total_requests": total_requests,
            "hit_rate": round(hit_rate, 2),
            "cache_size": len(self._cache),
        }


class CacheManager:
    """Central cache manager for the application"""

    def __init__(self):
        # Different caches for different data types
        self.products_cache = InMemoryCache(default_ttl=600)  # 10 minutes
        self.customers_cache = InMemoryCache(default_ttl=300)  # 5 minutes
        self.orders_cache = InMemoryCache(default_ttl=180)  # 3 minutes
        self.general_cache = InMemoryCache(default_ttl=300)  # 5 minutes

        self._logger = logging.getLogger(self.__class__.__name__)

    def get_product(self, product_id: int) -> Optional[Any]:
        """Get product from cache"""
        return self.products_cache.get(f"product:{product_id}")

    def set_product(self, product_id: int, product_data: Any) -> None:
        """Set product in cache"""
        self.products_cache.set(f"product:{product_id}", product_data)

    def get_products_by_category(self, category: str) -> Optional[List[Any]]:
        """Get products by category from cache"""
        return self.products_cache.get(f"category:{category}")

    def set_products_by_category(self, category: str, products: List[Any]) -> None:
        """Set products by category in cache"""
        self.products_cache.set(f"category:{category}", products)

    def get_customer(self, telegram_id: int) -> Optional[Any]:
        """Get customer from cache"""
        return self.customers_cache.get(f"customer:{telegram_id}")

    def set_customer(self, telegram_id: int, customer_data: Any) -> None:
        """Set customer in cache"""
        self.customers_cache.set(f"customer:{telegram_id}", customer_data)

    def get_order(self, order_id: int) -> Optional[Any]:
        """Get order from cache"""
        return self.orders_cache.get(f"order:{order_id}")

    def set_order(self, order_id: int, order_data: Any) -> None:
        """Set order in cache"""
        self.orders_cache.set(f"order:{order_id}", order_data)

    def invalidate_customer_cache(self, telegram_id: int) -> None:
        """Invalidate customer cache"""
        self.customers_cache.delete(f"customer:{telegram_id}")

    def invalidate_product_cache(
        self, product_id: int = None, category: str = None
    ) -> None:
        """Invalidate product cache"""
        if product_id:
            self.products_cache.delete(f"product:{product_id}")
        if category:
            self.products_cache.delete(f"category:{category}")

    def cleanup_all_expired(self) -> Dict[str, int]:
        """Cleanup expired entries from all caches"""
        return {
            "products": self.products_cache.cleanup_expired(),
            "customers": self.customers_cache.cleanup_expired(),
            "orders": self.orders_cache.cleanup_expired(),
            "general": self.general_cache.cleanup_expired(),
        }

    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all caches"""
        return {
            "products": self.products_cache.get_stats(),
            "customers": self.customers_cache.get_stats(),
            "orders": self.orders_cache.get_stats(),
            "general": self.general_cache.get_stats(),
        }


_cache_manager: Optional[CacheManager] = None
_cache_manager_lock = threading.Lock()


def get_cache_manager() -> "CacheManager":
    """Get the global cache manager instance, ensuring thread safety."""
    if _cache_manager is None:
        with _cache_manager_lock:
            # Check again inside the lock to ensure thread safety
            if _cache_manager is None:
                _cache_manager = CacheManager()
    return _cache_manager


def cached(cache_key_func=None, ttl: int = 300):
    """
    Decorator for caching function results

    Args:
        cache_key_func: Function to generate cache key from function args
        ttl: Time to live in seconds
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_manager = get_cache_manager()

            # Generate cache key
            if cache_key_func:
                cache_key = cache_key_func(*args, **kwargs)
            else:
                # Default key generation
                key_parts = [func.__name__]
                key_parts.extend(str(arg) for arg in args)
                key_parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
                cache_key = ":".join(key_parts)

            # Try to get from cache
            cached_result = cache_manager.general_cache.get(cache_key)
            if cached_result is not None:
                return cached_result

            # Execute function and cache result
            result = func(*args, **kwargs)
            cache_manager.general_cache.set(cache_key, result, ttl)

            return result

        return wrapper

    return decorator


def cache_key_for_product(product_id: int) -> str:
    """Generate cache key for product"""
    return f"product:{product_id}"


def cache_key_for_category(category: str) -> str:
    """Generate cache key for product category"""
    return f"category:{category}"


def cache_key_for_customer(telegram_id: int) -> str:
    """Generate cache key for customer"""
    return f"customer:{telegram_id}"


# Cache warming functions
class CacheWarmer:
    """Utility class for warming up caches"""

    def __init__(self, cache_manager: CacheManager):
        self.cache_manager = cache_manager
        self._logger = logging.getLogger(self.__class__.__name__)

    def warm_products_cache(self):
        """Warm the cache with all active products"""
        self._logger.info("Warming up products cache...")
        try:
            db_manager = get_database_manager()
            optimized_queries = OptimizedQueries(db_manager)
            products = optimized_queries.get_all_active_products()
            for product in products:
                self.cache_manager.set_product(product.id, product)
            self._logger.info("Warmed up cache with %d products", len(products))
        except (IOError, OSError) as e:
            self._logger.error("Error warming products cache: %s", e)

    def warm_popular_data_cache(self):
        """Warm the cache with popular data (e.g., popular products)"""
        self._logger.info("Warming up popular data cache...")
        try:
            db_manager = get_database_manager()
            optimized_queries = OptimizedQueries(db_manager)
            popular_products = optimized_queries.get_popular_products(limit=20)
            self.cache_manager.general_cache.set(
                "popular_products", popular_products, ttl=3600
            )
            self._logger.info("Warmed up cache with %d popular products", len(popular_products))
        except (IOError, OSError) as e:
            self._logger.error("Error warming popular data cache: %s", e)


# Scheduled cache maintenance
class CacheMaintenance:
    """Background task for cache maintenance"""

    def __init__(self, cache_manager: CacheManager, interval: int = 60):
        self._cache_manager = cache_manager
        self._interval = interval
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._logger = logging.getLogger(self.__class__.__name__)

    def start_maintenance(self):
        """Start the background maintenance task"""
        if self._thread and self._thread.is_alive():
            self._logger.warning("Maintenance task already running")
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._maintenance_loop, daemon=True)
        self._thread.start()
        self._logger.info("Cache maintenance task started")

    def stop_maintenance(self):
        """Stop the background maintenance task"""
        self._stop_event.set()
        if self._thread:
            self._thread.join()
        self._logger.info("Cache maintenance task stopped")

    def _maintenance_loop(self):
        """The main loop for cache maintenance"""
        while not self._stop_event.is_set():
            self._logger.info("Running cache maintenance...")
            try:
                stats = self._cache_manager.cleanup_all_expired()
                self._logger.info("Cache cleanup stats: %s", stats)
            except (IOError, OSError) as e:
                self._logger.error("Error during cache maintenance: %s", e)
            time.sleep(self._interval)

    def schedule_maintenance(self):
        """Schedule periodic cache maintenance"""
        # This can be integrated with a task scheduler like APScheduler
        self._logger.info("Cache maintenance scheduler started")
