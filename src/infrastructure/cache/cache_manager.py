"""
Cache manager for the Samna Salta bot with performance optimization

Uses constants for TTL values and proper type annotations for better maintainability.
"""

import logging
import time
from typing import Any, Dict, Optional, Union, TypeVar, Generic
from threading import Lock

from src.infrastructure.utilities.constants import CacheSettings

logger = logging.getLogger(__name__)

T = TypeVar('T')


class CacheEntry(Generic[T]):
    """Cache entry with timestamp and value"""
    
    def __init__(self, value: T, ttl: int):
        self.value = value
        self.expires_at = time.time() + ttl
        self.created_at = time.time()
    
    def is_expired(self) -> bool:
        """Check if cache entry is expired"""
        return time.time() > self.expires_at
    
    def get_age(self) -> float:
        """Get age of cache entry in seconds"""
        return time.time() - self.created_at


class CacheManager:
    """Simple in-memory cache manager with TTL support"""

    def __init__(self):
        self.cache: Dict[str, CacheEntry[Any]] = {}
        self.lock = Lock()
        self.stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "evictions": 0
        }

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        with self.lock:
            if key in self.cache:
                entry = self.cache[key]
                if entry.is_expired():
                    del self.cache[key]
                    self.stats["evictions"] += 1
                    self.stats["misses"] += 1
                    logger.debug(f"Cache miss (expired): {key}")
                    return None
                else:
                    self.stats["hits"] += 1
                    logger.debug(f"Cache hit: {key}")
                    return entry.value
            else:
                self.stats["misses"] += 1
                logger.debug(f"Cache miss: {key}")
                return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache with TTL"""
        if ttl is None:
            ttl = CacheSettings.GENERAL_CACHE_TTL_SECONDS
            
        with self.lock:
            self.cache[key] = CacheEntry(value, ttl)
            self.stats["sets"] += 1
            logger.debug(f"Cache set: {key} (TTL: {ttl}s)")

    def delete(self, key: str) -> bool:
        """Delete value from cache"""
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                logger.debug(f"Cache delete: {key}")
                return True
            return False

    def clear(self) -> None:
        """Clear all cache entries"""
        with self.lock:
            self.cache.clear()
            self.stats = {
                "hits": 0,
                "misses": 0,
                "sets": 0,
                "evictions": 0
            }
            logger.info("Cache cleared")

    def cleanup_expired(self) -> int:
        """Remove expired entries and return count"""
        with self.lock:
            expired_keys = [
                key for key, entry in self.cache.items()
                if entry.is_expired()
            ]
            
            for key in expired_keys:
                del self.cache[key]
                
            self.stats["evictions"] += len(expired_keys)
            
            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
                
            return len(expired_keys)

    def get_stats(self) -> Dict[str, Union[int, float]]:
        """Get cache statistics"""
        with self.lock:
            total_requests = self.stats["hits"] + self.stats["misses"]
            hit_rate = (self.stats["hits"] / total_requests) if total_requests > 0 else 0.0
            
            return {
                "hits": self.stats["hits"],
                "misses": self.stats["misses"],
                "sets": self.stats["sets"],
                "evictions": self.stats["evictions"],
                "hit_rate": hit_rate,
                "total_entries": len(self.cache),
                "total_requests": total_requests
            }

    def get_cache_info(self) -> Dict[str, Any]:
        """Get detailed cache information"""
        with self.lock:
            entries_info = []
            for key, entry in self.cache.items():
                entries_info.append({
                    "key": key,
                    "age": entry.get_age(),
                    "expires_in": entry.expires_at - time.time(),
                    "is_expired": entry.is_expired()
                })
            
            return {
                "stats": self.get_stats(),
                "entries": entries_info
            }


class ProductCacheManager(CacheManager):
    """Specialized cache manager for products"""

    def get_products(self) -> Optional[Any]:
        """Get cached products"""
        return self.get("products")

    def set_products(self, products: Any) -> None:
        """Cache products with specific TTL"""
        self.set("products", products, CacheSettings.PRODUCTS_CACHE_TTL_SECONDS)

    def get_product_by_id(self, product_id: int) -> Optional[Any]:
        """Get cached product by ID"""
        return self.get(f"product_{product_id}")

    def set_product(self, product_id: int, product: Any) -> None:
        """Cache product with specific TTL"""
        self.set(f"product_{product_id}", product, CacheSettings.PRODUCTS_CACHE_TTL_SECONDS)


class CustomerCacheManager(CacheManager):
    """Specialized cache manager for customers"""

    def get_customer(self, telegram_id: int) -> Optional[Any]:
        """Get cached customer"""
        return self.get(f"customer_{telegram_id}")

    def set_customer(self, telegram_id: int, customer: Any) -> None:
        """Cache customer with specific TTL"""
        self.set(f"customer_{telegram_id}", customer, CacheSettings.CUSTOMERS_CACHE_TTL_SECONDS)

    def get_all_customers(self) -> Optional[Any]:
        """Get cached customer list"""
        return self.get("all_customers")

    def set_all_customers(self, customers: Any) -> None:
        """Cache customer list with specific TTL"""
        self.set("all_customers", customers, CacheSettings.CUSTOMERS_CACHE_TTL_SECONDS)


class OrderCacheManager(CacheManager):
    """Specialized cache manager for orders"""

    def get_order(self, order_id: int) -> Optional[Any]:
        """Get cached order"""
        return self.get(f"order_{order_id}")

    def set_order(self, order_id: int, order: Any) -> None:
        """Cache order with specific TTL"""
        self.set(f"order_{order_id}", order, CacheSettings.ORDERS_CACHE_TTL_SECONDS)

    def get_all_orders(self) -> Optional[Any]:
        """Get cached order list"""
        return self.get("all_orders")

    def set_all_orders(self, orders: Any) -> None:
        """Cache order list with specific TTL"""
        self.set("all_orders", orders, CacheSettings.ORDERS_CACHE_TTL_SECONDS)


# Global cache instances
_product_cache: Optional[ProductCacheManager] = None
_customer_cache: Optional[CustomerCacheManager] = None
_order_cache: Optional[OrderCacheManager] = None
_general_cache: Optional[CacheManager] = None
_cache_manager_lock = Lock()


def get_product_cache() -> ProductCacheManager:
    """Get product cache instance"""
    global _product_cache
    if _product_cache is None:
        _product_cache = ProductCacheManager()
    return _product_cache


def get_customer_cache() -> CustomerCacheManager:
    """Get customer cache instance"""
    global _customer_cache
    if _customer_cache is None:
        _customer_cache = CustomerCacheManager()
    return _customer_cache


def get_order_cache() -> OrderCacheManager:
    """Get order cache instance"""
    global _order_cache
    if _order_cache is None:
        _order_cache = OrderCacheManager()
    return _order_cache


def get_general_cache() -> CacheManager:
    """Get general cache instance"""
    global _general_cache
    if _general_cache is None:
        _general_cache = CacheManager()
    return _general_cache


def cleanup_all_caches() -> Dict[str, int]:
    """Clean up expired entries from all caches"""
    results = {}
    
    if _product_cache:
        results["products"] = _product_cache.cleanup_expired()
    
    if _customer_cache:
        results["customers"] = _customer_cache.cleanup_expired()
    
    if _order_cache:
        results["orders"] = _order_cache.cleanup_expired()
    
    if _general_cache:
        results["general"] = _general_cache.cleanup_expired()
    
    return results


def get_all_cache_stats() -> Dict[str, Any]:
    """Get statistics from all caches"""
    stats = {}
    
    if _product_cache:
        stats["products"] = _product_cache.get_stats()
    
    if _customer_cache:
        stats["customers"] = _customer_cache.get_stats()
    
    if _order_cache:
        stats["orders"] = _order_cache.get_stats()
    
    if _general_cache:
        stats["general"] = _general_cache.get_stats()
    
    return stats


_cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> "CacheManager":
    """Get the global cache manager instance, ensuring thread safety."""
    global _cache_manager
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
            self._logger.info(
                "Warmed up cache with %d popular products", len(popular_products)
            )
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
