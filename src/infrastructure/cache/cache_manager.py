"""
Caching layer for improved performance
"""

import json
import logging
import time
from dataclasses import asdict
from functools import wraps
from typing import Any, Dict, List, Optional

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
            else:
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


# Global cache manager instance
_cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """Get the global cache manager instance"""
    global _cache_manager
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
        """Warm up products cache with frequently accessed data"""
        try:
            from ..database.database_optimizations import (
                OptimizedQueries,
                get_database_manager,
            )

            db_manager = get_database_manager()
            queries = OptimizedQueries(db_manager)

            # Cache products by category
            categories = ["bread", "spread", "spice", "beverage"]
            for category in categories:
                products = queries.get_active_products_by_category(category)
                self.cache_manager.set_products_by_category(category, products)

                # Cache individual products
                for product in products:
                    self.cache_manager.set_product(product.id, product)

            self._logger.info("Products cache warmed up successfully")

        except Exception as e:
            self._logger.error(f"Failed to warm products cache: {e}")

    def warm_popular_data_cache(self):
        """Warm up cache with popular/frequently accessed data"""
        try:
            from ..database.database_optimizations import (
                OptimizedQueries,
                get_database_manager,
            )

            db_manager = get_database_manager()
            queries = OptimizedQueries(db_manager)

            # Cache popular products
            popular_products = queries.get_popular_products(limit=20)
            self.cache_manager.general_cache.set(
                "popular_products", popular_products, ttl=1800
            )  # 30 minutes

            self._logger.info("Popular data cache warmed up successfully")

        except Exception as e:
            self._logger.error(f"Failed to warm popular data cache: {e}")


# Scheduled cache maintenance
import threading
import time as time_module


class CacheMaintenance:
    """Background cache maintenance tasks"""

    def __init__(self, cache_manager: CacheManager):
        self.cache_manager = cache_manager
        self._logger = logging.getLogger(self.__class__.__name__)
        self._stop_event = threading.Event()
        self._maintenance_thread = None

    def start_maintenance(self):
        """Start background cache maintenance"""
        if self._maintenance_thread is None or not self._maintenance_thread.is_alive():
            self._maintenance_thread = threading.Thread(
                target=self._maintenance_loop, daemon=True
            )
            self._maintenance_thread.start()
            self._logger.info("Cache maintenance started")

    def stop_maintenance(self):
        """Stop background cache maintenance"""
        self._stop_event.set()
        if self._maintenance_thread:
            self._maintenance_thread.join(timeout=5)
        self._logger.info("Cache maintenance stopped")

    def _maintenance_loop(self):
        """Main maintenance loop"""
        while not self._stop_event.is_set():
            try:
                # Cleanup expired entries every 5 minutes
                cleaned = self.cache_manager.cleanup_all_expired()
                total_cleaned = sum(cleaned.values())

                if total_cleaned > 0:
                    self._logger.info(
                        f"Cleaned up {total_cleaned} expired cache entries"
                    )

                # Log cache statistics every hour
                stats = self.cache_manager.get_all_stats()
                self._logger.debug(f"Cache stats: {stats}")

                # Wait 5 minutes before next cleanup
                self._stop_event.wait(300)

            except Exception as e:
                self._logger.error(f"Cache maintenance error: {e}")
                self._stop_event.wait(60)  # Wait 1 minute on error
