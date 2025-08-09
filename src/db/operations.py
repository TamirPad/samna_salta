"""
Database operations with retry logic and connection management

Enhanced with proper type annotations, constant usage, and performance optimizations.
"""

import logging
# PostgreSQL operations only
import time
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Union, Generator, Tuple
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine, event, text
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.pool import StaticPool, QueuePool
from sqlalchemy.orm import joinedload

from src.config import get_config
from src.db.models import (
    Base,
    Cart,
    CartItem,
    Customer,
    Order,
    OrderItem,
    Product,
    MenuCategory,
    BusinessSettings,
    ProductOption,
    ProductSize,
    OrderStatus,
    DeliveryMethod,
    PaymentMethod,
    DeliveryArea,
)
from src.utils.logger import PerformanceLogger
from src.utils.constants import (
    DatabaseSettings,
    ErrorCodes,
    PerformanceSettings,
    RetrySettings,
)
from src.utils.error_handler import (
    DatabaseConnectionError,
    DatabaseOperationError,
    DatabaseRetryExhaustedError,
    DatabaseTimeoutError,
    retry_on_database_error,
)

import random
import string
from decimal import Decimal
import json

logger = logging.getLogger(__name__)


def get_localized_name(product: Product, language: str = "en") -> str:
    """Get localized name for a product based on user language preference.
    - Prefer explicit multilingual columns (name_he/name_en)
    - For Hebrew fallback, try heuristic translation from the base name to Hebrew labels
    - Finally fallback to the legacy 'name' field
    """
    if language == "he":
        if getattr(product, "name_he", None):
            return product.name_he
        # Heuristic fallback: translate known product names to Hebrew using helper
        try:
            from src.utils.helpers import translate_product_name
            base_name = product.name_en or product.name or ""
            translated = translate_product_name(base_name, options=None, user_id=None)
            if translated:
                return translated
        except Exception:
            pass
        # Last resort
        return product.name or product.name_en or ""
    else:
        if getattr(product, "name_en", None):
            return product.name_en
        return product.name or product.name_he or ""


def get_localized_description(product: Product, language: str = "en") -> str:
    """Get localized description for a product based on user language preference"""
    if language == "he" and product.description_he:
        return product.description_he
    elif language == "en" and product.description_en:
        return product.description_en
    else:
        # Fallback to original description field
        return product.description or ""


def get_localized_category_name(category: MenuCategory, language: str = "en") -> str:
    """Get localized name for a category based on user language preference"""
    if language == "he" and category.name_he:
        return category.name_he
    elif language == "en" and category.name_en:
        return category.name_en
    else:
        # Fallback to English name
        return category.name_en or "Uncategorized"


def get_localized_category_description(category: MenuCategory, language: str = "en") -> str:
    """Get localized description for a category based on user language preference"""
    if language == "he" and category.description_he:
        return category.description_he
    elif language == "en" and category.description_en:
        return category.description_en
    else:
        # Fallback to original description field
        return category.description or ""


class ACIDTransactionManager:
    """Manages ACID-compliant transactions with configurable isolation levels"""
    
    @staticmethod
    @contextmanager
    def atomic_transaction(
        isolation_level: str = "READ_COMMITTED",
        timeout: int = 30
    ) -> Generator[Session, None, None]:
        """
        Atomic transaction with configurable isolation level
        
        Args:
            isolation_level: Database isolation level (READ_COMMITTED, SERIALIZABLE, etc.)
            timeout: Transaction timeout in seconds
            
        Yields:
            Database session for transaction operations
        """
        session = get_db_session()
        try:
            # Check if we're using PostgreSQL (Supabase) or SQLite
            engine = session.bind
            if engine and hasattr(engine, 'url') and 'postgresql' in str(engine.url):
                # PostgreSQL/Supabase: Set transaction isolation level
                if isolation_level == "READ_COMMITTED":
                    session.execute(text("SET TRANSACTION ISOLATION LEVEL READ COMMITTED"))
                elif isolation_level == "SERIALIZABLE":
                    session.execute(text("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE"))
                elif isolation_level == "REPEATABLE_READ":
                    session.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"))
                elif isolation_level == "READ_UNCOMMITTED":
                    session.execute(text("SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED"))
                
                session.execute(text(f"SET LOCAL lock_timeout = '{timeout}s'"))
            else:
                # SQLite: Use default isolation level (SERIALIZABLE)
                logger.debug("Using SQLite with default SERIALIZABLE isolation level")
            
            yield session
            session.commit()
            logger.debug("Transaction committed successfully")
            
        except Exception as e:
            session.rollback()
            logger.error("Transaction failed and rolled back: %s", e)
            raise
        finally:
            session.close()


class OrderValidator:
    """Business logic validation for orders"""
    
    VALID_STATUS_TRANSITIONS = {
        'pending': ['confirmed', 'cancelled'],
        'confirmed': ['preparing', 'missing', 'cancelled'],
        'preparing': ['missing', 'ready', 'cancelled'],
        'missing': ['preparing', 'cancelled'],
        'ready': ['delivered'],
        'delivered': [],  # Terminal state
        'cancelled': []   # Terminal state
    }
    
    @staticmethod
    def validate_order_status_transition(current_status: str, new_status: str) -> bool:
        """Validate order status transitions"""
        return new_status in OrderValidator.VALID_STATUS_TRANSITIONS.get(current_status, [])
    
    @staticmethod
    def validate_order_totals(order: Order, items: List[OrderItem]) -> bool:
        """Validate order totals match items"""
        calculated_subtotal = sum(item.total_price for item in items)
        calculated_total = calculated_subtotal + order.delivery_charge
        return abs(calculated_total - order.total) < 0.01
    
    @staticmethod
    def validate_cart_consistency(cart_items: List[Dict]) -> bool:
        """Validate cart item consistency"""
        for item in cart_items:
            if item.get('quantity', 0) <= 0:
                return False
            if item.get('unit_price', 0) < 0:
                return False
            calculated_total = item.get('unit_price', 0) * item.get('quantity', 0)
            if abs(calculated_total - item.get('total_price', 0)) > 0.01:
                return False
        return True


class AuditLogger:
    """Audit trail for critical operations"""
    
    @staticmethod
    def log_order_creation(order: Order, user_id: int):
        """Log order creation"""
        logger.info(
            "ORDER_CREATED: order_id=%d, customer_id=%d, total=%.2f, user_id=%d, order_number=%s",
            order.id, order.customer_id, order.total, user_id, order.order_number
        )
    
    @staticmethod
    def log_status_change(order_id: int, old_status: str, new_status: str, user_id: int):
        """Log order status change"""
        logger.info(
            "STATUS_CHANGED: order_id=%d, %s->%s, user_id=%d",
            order_id, old_status, new_status, user_id
        )
    
    @staticmethod
    def log_cart_operation(operation: str, telegram_id: int, product_id: int, quantity: int):
        """Log cart operations"""
        logger.info(
            "CART_OPERATION: %s, telegram_id=%d, product_id=%d, quantity=%d",
            operation, telegram_id, product_id, quantity
        )


class DatabaseOptimizer:
    """Optimizes database operations for better performance"""

    def __init__(self, db_manager=None):
        self._logger = logging.getLogger(self.__class__.__name__)
        self._db_manager = db_manager

    def optimize_query(self, query: Any) -> Any:
        """Apply query optimizations"""
        return query

    def get_optimization_stats(self) -> Dict[str, Any]:
        """Get optimization statistics"""
        if self._db_manager is None:
            return {"pool_status": {"status": "not_initialized"}}
        engine = self._db_manager.get_engine()
        return {
            "pool_status": {
                "status": "active",
                "pool_size": engine.pool.size(),
                "checkedin": engine.pool.checkedin(),
                "checkedout": engine.pool.checkedout(),
                "overflow": engine.pool.overflow() if hasattr(engine.pool, "overflow") else 0,
            }
        }

# Update DatabaseManager to include optimization features
class DatabaseManager:
    """Enhanced database manager with retry logic and performance monitoring"""

    def __init__(self, config: Optional[Any] = None):
        """Initialize database manager with configuration"""
        self.config = config or get_config()
        self._engine: Optional[Engine] = None
        self._session_factory: Optional[sessionmaker] = None
        self.logger = logging.getLogger(__name__)
        self.optimizer = DatabaseOptimizer(self)

    def get_engine(self) -> Engine:
        """Get database engine with proper configuration"""
        if self._engine is None:
            self._engine = self._create_engine()
        return self._engine

    def _create_engine(self) -> Engine:
        """Create database engine with environment-specific settings"""
        # Prioritize Supabase connection string if available
        if self.config.supabase_connection_string:
            database_url = self.config.supabase_connection_string
        else:
            database_url = self.config.database_url

        # Base engine configuration
        engine_kwargs: dict[str, Any] = {
            "pool_recycle": DatabaseSettings.POOL_RECYCLE_SECONDS,
            "pool_pre_ping": True,
            "echo": self.config.environment == "development",
        }

        # PostgreSQL/Supabase: configure pool sizing
        if self.config.environment == "production":
            pool_size = DatabaseSettings.PRODUCTION_POOL_SIZE
            max_overflow = DatabaseSettings.PRODUCTION_MAX_OVERFLOW
        else:
            pool_size = DatabaseSettings.DEVELOPMENT_POOL_SIZE
            max_overflow = DatabaseSettings.DEVELOPMENT_MAX_OVERFLOW

        engine_kwargs.update({"pool_size": pool_size, "max_overflow": max_overflow})

        engine = create_engine(database_url, **engine_kwargs)

        # Add performance monitoring
        self._setup_engine_events(engine)

        return engine

    def _setup_engine_events(self, engine: Engine) -> None:
        """Setup SQLAlchemy events for performance monitoring"""

        # During tests, create_engine() may be patched with a MagicMock. Those mocks
        # do not support SQLAlchemy event registration and would raise
        # InvalidRequestError. Silently skip in that scenario.
        try:
            from unittest.mock import Mock

            if isinstance(engine, Mock):  # pragma: no cover
                return

            @event.listens_for(engine, "before_cursor_execute")
            def before_cursor_execute(
                conn, cursor, statement, parameters, context, execmany
            ):  # noqa: D401,E501
                conn.info.setdefault("query_start_time", time.time())
                logger.debug("Start Query: %s", statement)

            @event.listens_for(engine, "after_cursor_execute")
            def after_cursor_execute(
                conn, cursor, statement, parameters, context, execmany
            ):  # noqa: D401,E501
                total = time.time() - conn.info["query_start_time"]
                logger.debug("Query Complete! Total Time: %.2fms", total * 1000)

        except Exception:  # pylint: disable=broad-except
            # If registration fails (e.g., invalid event on mock), ignore – the
            # actual performance logging is non-critical for unit tests.
            logger.debug("Skipped engine event hooks for non-SQLAlchemy engine.")

    def get_session_factory(self) -> sessionmaker:
        """Get session factory"""
        if self._session_factory is None:
            self._session_factory = sessionmaker(
                bind=self.get_engine(), expire_on_commit=False
            )
        return self._session_factory

    def get_session(self) -> Session:
        """Get database session"""
        return self.get_session_factory()()

    @contextmanager
    def get_session_context(self) -> Generator[Session, None, None]:
        """Get a database session with automatic commit/rollback"""
        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def get_pool_status(self) -> Dict[str, Any]:
        """Get current connection pool status"""
        return self.optimizer.get_optimization_stats()["pool_status"]

    def create_tables(self) -> None:
        """Create all database tables"""
        try:
            # Create all tables
            Base.metadata.create_all(self.get_engine())

            # ------------------------------------------------------------------
            # Lightweight auto-migration for SQLite and PostgreSQL: add newly introduced columns
            # This ensures backward compatibility when new columns are added to models
            # ------------------------------------------------------------------
            
            def _column_exists(table: str, column: str) -> bool:
                """Check if a column exists in a table"""
                try:
                    with self.get_session_context() as session:
                        if self.config.database_url.startswith('sqlite'):
                            # SQLite
                            result = session.execute(text(f"PRAGMA table_info({table})"))
                            columns = [row[1] for row in result.fetchall()]
                            return column in columns
                        else:
                            # PostgreSQL
                            result = session.execute(text(f"""
                                SELECT column_name 
                                FROM information_schema.columns 
                                WHERE table_name = '{table}' AND column_name = '{column}'
                            """))
                            return result.fetchone() is not None
                except Exception:
                    return False

            # Add any missing columns that might be needed
            # This is a safety net for schema evolution
            try:
                with self.get_session_context() as session:
                    # Add missing column: business_settings.app_images (TEXT)
                    if not _column_exists("business_settings", "app_images"):
                        try:
                            # PostgreSQL and SQLite both support simple ADD COLUMN
                            session.execute(text("ALTER TABLE business_settings ADD COLUMN app_images TEXT"))
                            session.commit()
                            self.logger.info("Added missing column business_settings.app_images")
                        except Exception as add_err:
                            session.rollback()
                            self.logger.warning(f"Failed to add column app_images: {add_err}")
            except Exception as e:
                self.logger.warning(f"Auto-migration check failed: {e}")

            self.logger.info("Database tables created successfully")
        except Exception as e:
            self.logger.error(f"Failed to create database tables: {e}")
            raise

    def drop_tables(self) -> None:
        """Drop all database tables"""
        try:
            with PerformanceLogger("drop_tables", self.logger):
                Base.metadata.drop_all(self.get_engine())
                self.logger.info("Database tables dropped successfully")
        except SQLAlchemyError as e:
            self.logger.error(f"Failed to drop database tables: {e}", exc_info=True)
            raise DatabaseOperationError(
                f"Failed to drop database tables: {e}", ErrorCodes.DATABASE_ERROR
            ) from e

    def health_check(self) -> Dict[str, Any]:
        """Perform database health check"""
        try:
            with PerformanceLogger("db_health_check", self.logger):
                with self.get_session() as session:
                    # Simple query to test connection
                    result = session.execute("SELECT 1").fetchone()

                    # Check if result is as expected
                    if result and result[0] == 1:
                        return {
                            "status": "healthy",
                            "database_url": self.config.database_url,
                            "environment": self.config.environment,
                        }
                    else:
                        return {
                            "status": "unhealthy",
                            "error": "Health check query returned unexpected result",
                        }
        except Exception as e:
            self.logger.error(f"Database health check failed: {e}", exc_info=True)
            return {
                "status": "unhealthy",
                "error": str(e),
            }

    def close(self) -> None:
        """Close database connections"""
        if self._engine:
            self._engine.dispose()
            self._engine = None
        if self._session_factory:
            self._session_factory = None
        self.logger.info("Database connections closed")


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


def get_db_manager() -> DatabaseManager:
    """Get global database manager instance"""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


def get_db_session() -> Session:
    """Get database session - convenience function"""
    return get_db_manager().get_session()


def retry_on_database_error(
    max_retries: int = RetrySettings.MAX_RETRIES,
    delay: int = RetrySettings.RETRY_DELAY_SECONDS,
) -> Callable:
    """Decorator for database operations with retry logic"""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception: Optional[Exception] = None
            logger = logging.getLogger(func.__module__)

            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except (OperationalError, DatabaseConnectionError) as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        logger.warning(
                            f"Database operation {func.__name__} failed (attempt {attempt + 1}/{max_retries}): {e}",
                            extra={"attempt": attempt + 1, "function": func.__name__},
                        )
                        time.sleep(delay)
                    else:
                        logger.error(
                            f"Database operation {func.__name__} failed after {max_retries} attempts: {e}",
                            extra={"function": func.__name__},
                            exc_info=True,
                        )
                except SQLAlchemyError as e:
                    last_exception = e
                    logger.error(
                        f"Database operation {func.__name__} failed with non-retryable error: {e}",
                        extra={"function": func.__name__},
                        exc_info=True,
                    )
                    break

            # All retries failed
            if isinstance(last_exception, (OperationalError, DatabaseConnectionError)):
                raise DatabaseRetryExhaustedError(
                    f"Database operation {func.__name__} failed after {max_retries} attempts: {last_exception}",
                    ErrorCodes.DATABASE_ERROR,
                ) from last_exception
            else:
                raise DatabaseOperationError(
                    f"Database operation {func.__name__} failed: {last_exception}",
                    ErrorCodes.DATABASE_ERROR,
                ) from last_exception

        return wrapper

    return decorator





def init_db():
    """Initialize database tables with connection retry logic"""
    max_retries = 3
    retry_delay = 5  # seconds
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Database initialization attempt {attempt + 1}/{max_retries}")
            
            # Test connection first
            engine = get_db_manager().get_engine()
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                logger.info("Database connection test successful")
            
            # Create tables
            get_db_manager().create_tables()
            logger.info("Database tables created successfully")

            # Initialize default products (only if none exist)
            init_default_products()
            
            logger.info("Database initialization completed successfully")
            return
            
        except SQLAlchemyError as e:
            logger.error(f"Database initialization attempt {attempt + 1} failed: {e}")
            
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                logger.error("All database initialization attempts failed")
                # Don't raise the exception - let the application continue
                # This allows the bot to start even if database is temporarily unavailable
                logger.warning("Continuing without database initialization - some features may be limited")
                return


def init_default_products():
    """Initialize default products in the database"""
    session = get_db_session()
    try:
        # Check if products already exist
        if session.query(Product).count() > 0:
            logger.info("Products already exist, skipping initialization")
            return

        # First, create categories with image URLs and Hebrew names
        categories_data = [
            {
                "name": "bread", 
                "name_he": "מאפים",
                "name_en": "Bread",
                "description": "Traditional breads", 
                "description_he": "לחמים מסורתיים",
                "description_en": "Traditional breads",
                "display_order": 1, 
                "image_url": "https://images.unsplash.com/photo-1509440159596-0249088772ff?w=800&h=600&fit=crop"
            },
            {
                "name": "spread", 
                "name_he": "ממרח",
                "name_en": "Spread",
                "description": "Traditional spreads and condiments", 
                "description_he": "ממרחים ותבלינים מסורתיים",
                "description_en": "Traditional spreads and condiments",
                "display_order": 2, 
                "image_url": "https://images.unsplash.com/photo-1586444248902-2f64eddc13df?w=800&h=600&fit=crop"
            },
            {
                "name": "spice", 
                "name_he": "תבלין",
                "name_en": "Spice",
                "description": "Traditional spice blends", 
                "description_he": "תערובות תבלינים מסורתיות",
                "description_en": "Traditional spice blends",
                "display_order": 3, 
                "image_url": "https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=800&h=600&fit=crop"
            },
            {
                "name": "beverage", 
                "name_he": "משקה",
                "name_en": "Beverage",
                "description": "Traditional beverages", 
                "description_he": "משקאות מסורתיים",
                "description_en": "Traditional beverages",
                "display_order": 4, 
                "image_url": "https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?w=800&h=600&fit=crop"
            },
        ]
        
        # Create categories and store them in a dict for easy lookup
        categories = {}
        for cat_data in categories_data:
            existing_cat = session.query(MenuCategory).filter(MenuCategory.name_en == cat_data["name_en"]).first()
            if existing_cat:
                categories[cat_data["name_en"]] = existing_cat
            else:
                category = MenuCategory(**cat_data)
                session.add(category)
                session.flush()  # Get the ID
                categories[cat_data["name_en"]] = category

        # Default products configuration with image URLs and Hebrew names
        products = [
            {
                "name": "Kubaneh",
                "name_he": "קובנה",
                "name_en": "Kubaneh",
                "category_id": categories["bread"].id,
                "description": "Traditional Yemenite bread",
                "description_he": "לחם תימני מסורתי",
                "description_en": "Traditional Yemenite bread",
                "price": 25.00,
                "image_url": "https://images.unsplash.com/photo-1509440159596-0249088772ff?w=800&h=600&fit=crop",
            },
            {
                "name": "Samneh",
                "name_he": "סמנה",
                "name_en": "Samneh",
                "category_id": categories["spread"].id,
                "description": "Traditional clarified butter",
                "description_he": "חמאה מזוקקת מסורתית",
                "description_en": "Traditional clarified butter",
                "price": 15.00,
                "image_url": "https://images.unsplash.com/photo-1586444248902-2f64eddc13df?w=800&h=600&fit=crop",
            },
            {
                "name": "Red Bisbas",
                "name_he": "בסבס אדום",
                "name_en": "Red Bisbas",
                "category_id": categories["spice"].id,
                "description": "Traditional Yemenite spice blend",
                "description_he": "תערובת תבלינים תימנית מסורתית",
                "description_en": "Traditional Yemenite spice blend",
                "price": 12.00,
                "image_url": "https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=800&h=600&fit=crop",
            },
            {
                "name": "Hawaij soup spice",
                "name_he": "חוואיג' למרק",
                "name_en": "Hawaij for Soup",
                "category_id": categories["spice"].id,
                "description": "Traditional soup spice blend",
                "description_he": "תערובת תבלינים למרק",
                "description_en": "Traditional soup spice blend",
                "price": 8.00,
                "image_url": "https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=800&h=600&fit=crop",
            },
            {
                "name": "Hawaij coffee spice",
                "name_he": "חוואיג' לקפה",
                "name_en": "Hawaij for Coffee",
                "category_id": categories["spice"].id,
                "description": "Traditional coffee spice blend",
                "description_he": "תערובת תבלינים לקפה",
                "description_en": "Traditional coffee spice blend",
                "price": 8.00,
                "image_url": "https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=800&h=600&fit=crop",
            },
            {
                "name": "White coffee",
                "name_he": "קפה לבן",
                "name_en": "White Coffee",
                "category_id": categories["beverage"].id,
                "description": "Traditional Yemenite white coffee",
                "description_he": "קפה לבן תימני מסורתי",
                "description_en": "Traditional Yemenite white coffee",
                "price": 10.00,
                "image_url": "https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?w=800&h=600&fit=crop",
            },
            {
                "name": "Hilbeh",
                "name_he": "חילבה",
                "name_en": "Hilbeh",
                "category_id": categories["spread"].id,
                "description": "Traditional fenugreek spread (available Wed-Fri only)",
                "description_he": "ממרח חילבה מסורתי (זמין בימים רביעי-שישי בלבד)",
                "description_en": "Traditional fenugreek spread (available Wed-Fri only)",
                "price": 18.00,
                "image_url": "https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=800&h=600&fit=crop",
            },
        ]

        for product_data in products:
            # Check if product already exists
            existing_product = session.query(Product).filter(Product.name == product_data["name"]).first()
            if not existing_product:
                product = Product(**product_data)
                session.add(product)

        session.commit()
        logger.info("Initialized %d default products", len(products))

    except SQLAlchemyError as e:
        session.rollback()
        logger.error("Failed to initialize products: %s", e)
        raise
    finally:
        session.close()


# Customer operations
@retry_on_database_error()
def get_or_create_customer(
    telegram_id: int, full_name: str, phone_number: str | None, language: str = "he"
) -> Customer:
    """Get existing customer or create new one"""
    session = get_db_session()
    try:
        # First check if customer exists with this telegram_id
        customer = (
            session.query(Customer)
            .filter(Customer.telegram_id == telegram_id)
            .first()
        )

        if customer:
            # Update existing customer's information
            customer.name = full_name
            customer.phone = phone_number
            customer.language = language
            customer.updated_at = datetime.utcnow()
            session.commit()
            session.refresh(customer)
            logger.info("Updated existing customer %s with new information: name='%s', phone='%s', language='%s'", 
                       telegram_id, full_name, phone_number, language)
            return customer

        # Check if customer exists with this phone number (but different telegram_id)
        existing_customer = None
        if phone_number:
            existing_customer = (
                session.query(Customer)
                .filter(Customer.phone == phone_number)
                .first()
            )

        if existing_customer:
            # Update telegram_id if it changed
            existing_customer.telegram_id = telegram_id
            existing_customer.name = full_name
            existing_customer.language = language
            existing_customer.updated_at = datetime.utcnow()
            session.commit()
            session.refresh(existing_customer)
            logger.info("Updated customer with phone %s to telegram_id %s", phone_number, telegram_id)
            return existing_customer

        # Create new customer
        customer = Customer(
            telegram_id=telegram_id,
            name=full_name or "",
            phone=phone_number,
            language=language,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        session.add(customer)
        session.commit()
        session.refresh(customer)
        logger.info("Created new customer %s", telegram_id)
        return customer

    except SQLAlchemyError as e:
        session.rollback()
        logger.error("Failed to get/create customer: %s", e)
        raise
    finally:
        session.close()


def get_customer_by_telegram_id(telegram_id: int) -> Customer | None:
    """Get customer by telegram ID"""
    session = get_db_session()
    try:
        return (
            session.query(Customer).filter(Customer.telegram_id == telegram_id).first()
        )
    except Exception as e:
        logger.error(f"Database operation get_customer_by_telegram_id failed with non-retryable error: {e}")
        raise
    finally:
        session.close()


# Product operations
@retry_on_database_error()
def get_all_products() -> list[Product]:
    """Get all active products"""
    session = get_db_session()
    try:
        return session.query(Product).filter(Product.is_active).all()
    finally:
        session.close()


@retry_on_database_error()
def get_all_products_admin() -> list[dict]:
    """Get all products (including inactive) for admin management with multilingual support"""
    session = get_db_session()
    try:
        products = session.query(Product, MenuCategory.name_en.label('category_name')).join(MenuCategory).order_by(MenuCategory.name_en, Product.name).all()
        
        result = []
        for product, category_name in products:
            result.append({
                "id": product.id,
                "name": product.name,
                "description": product.description,
                "name_en": product.name_en,
                "name_he": product.name_he,
                "description_en": product.description_en,
                "description_he": product.description_he,
                "category": category_name,
                "price": product.price,
                "is_active": product.is_active,
                "created_at": product.created_at,
                "updated_at": product.updated_at
            })
        
        return result
    finally:
        session.close()


@retry_on_database_error()
def get_product_by_name(name: str) -> Optional[Product]:
    """Get product by name"""
    session = get_db_session()
    try:
        return session.query(Product).filter(Product.name == name).first()
    finally:
        session.close()


@retry_on_database_error()
def get_product_by_id(product_id: int) -> Optional[Product]:
    """Get product by ID with category relationship loaded"""
    session = get_db_session()
    try:
        return session.query(Product).options(joinedload(Product.category_rel)).filter(Product.id == product_id).first()
    finally:
        session.close()


@retry_on_database_error()
def get_product_dict_by_id(product_id: int) -> Optional[Dict]:
    """Get product by ID as a dictionary with category name resolved and multilingual support"""
    session = get_db_session()
    try:
        product = session.query(Product).options(joinedload(Product.category_rel)).filter(Product.id == product_id).first()
        if not product:
            return None
        
        return {
            "id": product.id,
            "name": product.name,
            "description": product.description,
            "name_en": product.name_en,
            "name_he": product.name_he,
            "description_en": product.description_en,
            "description_he": product.description_he,
            "category": product.category_rel.name_en if product.category_rel else "Uncategorized",
            "price": product.price,
            "is_active": product.is_active,
            "created_at": product.created_at,
            "updated_at": product.updated_at
        }
    finally:
        session.close()


@retry_on_database_error()
def create_product(
    name: str, 
    description: str, 
    category: str, 
    price: float, 
    image_url: Optional[str] = None,
    name_en: Optional[str] = None,
    name_he: Optional[str] = None,
    description_en: Optional[str] = None,
    description_he: Optional[str] = None
) -> Optional[Product]:
    """Create a new product"""
    session = get_db_session()
    try:
        # Check if product with same name already exists
        existing_product = session.query(Product).filter(Product.name == name).first()
        if existing_product:
            # If it exists but is inactive, reactivate and update it instead of failing
            if getattr(existing_product, "is_active", True) is False:
                # Get category by name
                category_obj = session.query(MenuCategory).filter(MenuCategory.name_en == category).first()
                if not category_obj:
                    logger.warning("Category '%s' not found", category)
                    return None

                existing_product.description = description
                existing_product.category_id = category_obj.id
                existing_product.price = price
                existing_product.image_url = image_url
                existing_product.is_active = True
                # Update multilingual fields if provided
                if name_en is not None:
                    existing_product.name_en = name_en
                if name_he is not None:
                    existing_product.name_he = name_he
                if description_en is not None:
                    existing_product.description_en = description_en
                if description_he is not None:
                    existing_product.description_he = description_he
                existing_product.updated_at = datetime.utcnow()
                session.commit()
                session.refresh(existing_product)
                # Clear cache after changing products
                try:
                    from src.utils.helpers import SimpleCache
                    cache = SimpleCache()
                    cache.clear()
                    logger.info("Cleared cache after reactivating product '%s'", name)
                except Exception as cache_error:
                    logger.warning("Failed to clear cache after reactivating product '%s': %s", name, cache_error)
                logger.info("Reactivated and updated product: %s (ID: %d)", name, existing_product.id)
                return existing_product
            logger.warning("Product with name '%s' already exists and is active", name)
            return None
        
        # Get category by name
        category_obj = session.query(MenuCategory).filter(MenuCategory.name_en == category).first()
        if not category_obj:
            logger.warning("Category '%s' not found", category)
            return None
        
        product = Product(
            name=name,
            description=description,
            category_id=category_obj.id,
            price=price,
            is_active=True,
            image_url=image_url,
            name_en=name_en,
            name_he=name_he,
            description_en=description_en,
            description_he=description_he
        )
        session.add(product)
        session.commit()
        session.refresh(product)
        logger.info("Created new product: %s (ID: %d)", name, product.id)
        # Clear cache after creating product
        try:
            from src.utils.helpers import SimpleCache
            cache = SimpleCache()
            cache.clear()
            logger.info("Cleared cache after creating product ID %d", product.id)
        except Exception as cache_error:
            logger.warning("Failed to clear cache after creating product ID %d: %s", product.id, cache_error)
        return product
    except SQLAlchemyError as e:
        session.rollback()
        logger.error("Failed to create product '%s': %s", name, e)
        return None
    finally:
        session.close()


@retry_on_database_error()
def update_product(product_id: int, **kwargs) -> bool:
    """Update product by ID with provided fields"""
    session = get_db_session()
    try:
        product = session.query(Product).filter(Product.id == product_id).first()
        if not product:
            logger.warning("Product with ID %d not found", product_id)
            return False
        
        # Update allowed fields
        allowed_fields = ['name', 'description', 'price', 'is_active', 'image_url', 'name_en', 'name_he', 'description_en', 'description_he']
        for field, value in kwargs.items():
            if field in allowed_fields:
                setattr(product, field, value)
            elif field == 'category':
                # Handle category by name
                category_obj = session.query(MenuCategory).filter(MenuCategory.name_en == value).first()
                if category_obj:
                    product.category_id = category_obj.id
                else:
                    logger.warning("Category '%s' not found", value)
                    return False
        
        product.updated_at = datetime.utcnow()
        session.commit()
        
        # Clear any cached data related to this product
        try:
            from src.utils.helpers import SimpleCache
            cache = SimpleCache()
            cache.clear()  # Clear all cache entries to ensure fresh data
            logger.info("Cleared cache after updating product ID %d", product_id)
        except Exception as cache_error:
            logger.warning("Failed to clear cache after updating product ID %d: %s", product_id, cache_error)
        
        logger.info("Updated product ID %d: %s", product_id, kwargs)
        return True
    except SQLAlchemyError as e:
        session.rollback()
        logger.error("Failed to update product ID %d: %s", product_id, e)
        return False
    finally:
        session.close()


@retry_on_database_error()
def deactivate_product(product_id: int) -> bool:
    """Soft delete product by setting is_active to False"""
    session = get_db_session()
    try:
        product = session.query(Product).filter(Product.id == product_id).first()
        if not product:
            logger.warning("Product with ID %d not found", product_id)
            return False
        
        product.is_active = False
        product.updated_at = datetime.utcnow()
        session.commit()
        logger.info("Deactivated product ID %d: %s", product_id, product.name)
        # Clear cache after product status change
        try:
            from src.utils.helpers import SimpleCache
            cache = SimpleCache()
            cache.clear()
            logger.info("Cleared cache after deactivating product ID %d", product_id)
        except Exception as cache_error:
            logger.warning("Failed to clear cache after deactivating product ID %d: %s", product_id, cache_error)
        return True
    except SQLAlchemyError as e:
        session.rollback()
        logger.error("Failed to deactivate product ID %d: %s", product_id, e)
        return False
    finally:
        session.close()


@retry_on_database_error()
def hard_delete_product(product_id: int) -> bool:
    """Hard delete product by removing it from the database"""
    session = get_db_session()
    try:
        product = session.query(Product).filter(Product.id == product_id).first()
        if not product:
            logger.warning("Product with ID %d not found", product_id)
            return False
        
        # Check if product is referenced in any orders
        from src.db.models import OrderItem
        order_items = session.query(OrderItem).filter(OrderItem.product_id == product_id).first()
        if order_items:
            logger.warning("Cannot delete product ID %d: referenced in orders", product_id)
            return False
        
        # Check if product is in any active carts
        from src.db.models import CartItem
        cart_items = session.query(CartItem).filter(CartItem.product_id == product_id).first()
        if cart_items:
            logger.warning("Cannot delete product ID %d: referenced in carts", product_id)
            return False
        
        product_name = product.name
        session.delete(product)
        session.commit()
        logger.info("Hard deleted product ID %d: %s", product_id, product_name)
        # Clear cache after deleting product
        try:
            from src.utils.helpers import SimpleCache
            cache = SimpleCache()
            cache.clear()
            logger.info("Cleared cache after hard deleting product ID %d", product_id)
        except Exception as cache_error:
            logger.warning("Failed to clear cache after hard deleting product ID %d: %s", product_id, cache_error)
        return True
    except SQLAlchemyError as e:
        session.rollback()
        logger.error("Failed to hard delete product ID %d: %s", product_id, e)
        return False
    finally:
        session.close()


# Keep the old function name for backward compatibility
@retry_on_database_error()
def delete_product(product_id: int) -> bool:
    """Soft delete product by setting is_active to False (deprecated, use deactivate_product)"""
    return deactivate_product(product_id)


@retry_on_database_error()
def get_product_categories() -> list[str]:
    """Get all unique product categories that have active products (returns English names)"""
    session = get_db_session()
    try:
        # Get categories that have active products
        categories = session.query(MenuCategory).join(Product).filter(
            Product.is_active == True
        ).distinct().all()
        return [cat.name_en for cat in categories]  # Return English names
    finally:
        session.close()


@retry_on_database_error()
def get_all_categories() -> list[str]:
    """Get all categories (including those without products) - for admin use (returns English names)"""
    session = get_db_session()
    try:
        # Get all categories
        categories = session.query(MenuCategory).filter(
            MenuCategory.is_active == True
        ).order_by(MenuCategory.display_order, MenuCategory.name_en).all()
        return [cat.name_en for cat in categories]  # Return English names
    finally:
        session.close()


@retry_on_database_error()
def get_category_by_name(name: str) -> Optional[MenuCategory]:
    """Get category by name (searches in both name_en and name_he fields)"""
    session = get_db_session()
    try:
        # Search in both English and Hebrew name fields
        return session.query(MenuCategory).filter(
            (MenuCategory.name_en == name) | (MenuCategory.name_he == name)
        ).first()
    finally:
        session.close()


@retry_on_database_error()
def get_products_by_category(category: str) -> list[Product]:
    """Get all active products in a specific category"""
    session = get_db_session()
    try:
        # First get the category by name (searches in both name_en and name_he)
        category_obj = session.query(MenuCategory).filter(
            (MenuCategory.name_en == category) | (MenuCategory.name_he == category)
        ).first()
        if not category_obj:
            return []
        
        # Then get products by category_id
        return session.query(Product).filter(
            Product.category_id == category_obj.id,
            Product.is_active == True
        ).all()
    finally:
        session.close()


@retry_on_database_error()
def get_all_products_by_category(category: str) -> list[Product]:
    """Get all products in a specific category (including inactive ones)"""
    session = get_db_session()
    try:
        # First get the category by name (searches in both name_en and name_he)
        category_obj = session.query(MenuCategory).filter(
            (MenuCategory.name_en == category) | (MenuCategory.name_he == category)
        ).first()
        if not category_obj:
            return []
        
        # Then get products by category_id
        return session.query(Product).filter(
            Product.category_id == category_obj.id
        ).all()
    finally:
        session.close()



# Cart operations
@retry_on_database_error()
def get_or_create_cart(telegram_id: int) -> Cart:
    """Get existing cart or create new one"""
    session = get_db_session()
    try:
        # First get the customer by telegram_id
        customer = session.query(Customer).filter(Customer.telegram_id == telegram_id).first()
        if not customer:
            raise ValueError(f"Customer with telegram_id {telegram_id} not found")
        
        # Then get or create cart using customer_id
        cart = session.query(Cart).filter(Cart.customer_id == customer.id).first()

        if not cart:
            cart = Cart(customer_id=customer.id)
            session.add(cart)
            session.flush()

        return cart

    except SQLAlchemyError as e:
        session.rollback()
        logger.error("Failed to get/create cart: %s", e)
        raise
    finally:
        session.close()


@retry_on_database_error()
def add_to_cart(
    telegram_id: int, product_id: int, quantity: int = 1, options: dict | None = None
) -> bool:
    """
    Atomic cart addition with proper locking and validation (ACID compliant)
    
    Args:
        telegram_id: Customer's Telegram ID
        product_id: Product ID to add
        quantity: Quantity to add
        options: Product options
        
    Returns:
        True if successful, False otherwise
    """
    try:
        with ACIDTransactionManager.atomic_transaction("SERIALIZABLE") as session:
            # Lock customer record
            customer = session.query(Customer).filter(
                Customer.telegram_id == telegram_id
            ).with_for_update().first()
            
            if not customer:
                # Create customer if not exists
                customer = Customer(
                    telegram_id=telegram_id,
                    name="",  # Use 'name' not 'full_name'
                    phone="",  # Use 'phone' not 'phone_number'
                    language="en"
                )
                session.add(customer)
                session.flush()
            
            # Lock cart record
            cart = session.query(Cart).filter(
                Cart.customer_id == customer.id,
                Cart.is_active == True
            ).with_for_update().first()
            
            if not cart:
                cart = Cart(
                    customer_id=customer.id,
                    is_active=True,
                    delivery_method="pickup"
                )
                session.add(cart)
                session.flush()
            
            # Lock product record
            product = session.query(Product).filter(
                Product.id == product_id,
                Product.is_active == True
            ).with_for_update().first()
            
            if not product:
                raise ValueError(f"Product {product_id} not found or inactive")
            
            # Check if item already exists in cart
            existing_item = session.query(CartItem).filter(
                CartItem.cart_id == cart.id,
                CartItem.product_id == product_id
            ).with_for_update().first()
            
            if existing_item:
                # Update quantity
                existing_item.quantity += quantity
                existing_item.updated_at = datetime.utcnow()
                AuditLogger.log_cart_operation("UPDATE", telegram_id, product_id, quantity)
            else:
                # Create new cart item
                cart_item = CartItem(
                    cart_id=cart.id,
                    product_id=product_id,
                    quantity=quantity,
                    unit_price=product.price,
                    product_options=options or {},
                    special_instructions=""
                )
                session.add(cart_item)
                AuditLogger.log_cart_operation("ADD", telegram_id, product_id, quantity)
            
            return True
            
    except Exception as e:
        logger.error("Atomic cart operation failed: %s", e)
        return False


@retry_on_database_error()
def get_cart_items(telegram_id: int) -> list[dict]:
    """
    Get all items in the customer's cart with ACID compliance
    
    Args:
        telegram_id: Customer's Telegram ID
        
    Returns:
        List of cart items with product information including multilingual names
    """
    try:
        with ACIDTransactionManager.atomic_transaction("READ_COMMITTED") as session:
            # Get customer by telegram_id
            customer = session.query(Customer).filter(Customer.telegram_id == telegram_id).first()
            if not customer:
                logger.warning("Customer with telegram_id %d not found", telegram_id)
                return []

            # Get cart within this session
            cart = session.query(Cart).filter(
                Cart.customer_id == customer.id,
                Cart.is_active == True
            ).first()
            
            if not cart:
                logger.info("No active cart found for customer %d", telegram_id)
                return []

            # Get cart items with product information including multilingual fields
            cart_items = (
                session.query(CartItem, Product)
                .join(Product, CartItem.product_id == Product.id)
                .filter(CartItem.cart_id == cart.id)
                .all()
            )

            items = []
            for cart_item, product in cart_items:
                item_data = {
                    "id": cart_item.id,
                    "product_id": cart_item.product_id,
                    "product_name": product.name,
                    "name_en": product.name_en,  # Add English name
                    "name_he": product.name_he,  # Add Hebrew name
                    "quantity": cart_item.quantity,
                    "unit_price": float(cart_item.unit_price),
                    "total_price": float(cart_item.unit_price * cart_item.quantity),
                    "options": cart_item.product_options or {},
                    "special_instructions": cart_item.special_instructions or "",
                    "product_description": product.description,
                    "description_en": product.description_en,  # Add English description
                    "description_he": product.description_he,  # Add Hebrew description
                    "product_image_url": product.image_url
                }
                items.append(item_data)

            # Validate cart consistency
            if not OrderValidator.validate_cart_consistency(items):
                logger.warning("Cart consistency validation failed for customer %d", telegram_id)

            logger.info("Retrieved %d items from cart for customer %d", len(items), telegram_id)
            return items

    except Exception as e:
        logger.error("Failed to get cart items: %s", e)
        return []


@retry_on_database_error()
def update_cart(
    telegram_id: int,
    items: list[dict],
    delivery_method: str | None = None,
    delivery_address: str | None = None,
    delivery_area_id: int | None = None,
) -> bool:
    """Update cart with new items and delivery info"""
    session = get_db_session()
    try:
        customer = session.query(Customer).filter(Customer.telegram_id == telegram_id).first()
        if not customer:
            return False
        
        # Get or create cart within this session
        cart = session.query(Cart).filter(Cart.customer_id == customer.id).first()
        if not cart:
            cart = Cart(customer_id=customer.id)
            session.add(cart)
            session.flush()

        # Clear existing cart items
        session.query(CartItem).filter(CartItem.cart_id == cart.id).delete()

        # Add new items
        for item_data in items:
            product = session.query(Product).filter(Product.id == item_data["product_id"]).first()
            if product:
                new_item = CartItem(
                    cart_id=cart.id,
                    product_id=item_data["product_id"],
                    quantity=item_data["quantity"],
                    unit_price=item_data.get("unit_price", product.price),
                    product_options=item_data.get("options", {})
                )
                session.add(new_item)

        # Update delivery info
        if delivery_method:
            cart.delivery_method = delivery_method
        if delivery_address:
            cart.delivery_address = delivery_address
        if delivery_area_id is not None:
            cart.delivery_area_id = delivery_area_id

        session.commit()
        return True

    except SQLAlchemyError as e:
        session.rollback()
        logger.error("Failed to update cart: %s", e)
        return False
    finally:
        session.close()


@retry_on_database_error()
def clear_cart(telegram_id: int) -> bool:
    """
    Atomic cart clearing with proper locking (ACID compliant)
    
    Args:
        telegram_id: Customer's Telegram ID
        
    Returns:
        True if successful, False otherwise
    """
    try:
        with ACIDTransactionManager.atomic_transaction("SERIALIZABLE") as session:
            # Lock customer record
            customer = session.query(Customer).filter(
                Customer.telegram_id == telegram_id
            ).with_for_update().first()
            
            if not customer:
                logger.warning("Customer %d not found for cart clearing", telegram_id)
                return False
            
            # Lock cart record
            cart = session.query(Cart).filter(
                Cart.customer_id == customer.id,
                Cart.is_active == True
            ).with_for_update().first()
            
            if cart:
                # Delete all cart items
                deleted_items = session.query(CartItem).filter(
                    CartItem.cart_id == cart.id
                ).delete()
                
                # Delete the cart itself
                session.delete(cart)
                
                AuditLogger.log_cart_operation("CLEAR", telegram_id, 0, deleted_items)
                logger.info("Cleared cart for customer %d (deleted %d items)", telegram_id, deleted_items)
            else:
                logger.info("No active cart found for customer %d", telegram_id)
            
            return True
            
    except Exception as e:
        logger.error("Atomic cart clearing failed: %s", e)
        return False


@retry_on_database_error()
def remove_from_cart(telegram_id: int, product_id: int) -> bool:
    """
    Atomic cart item removal with proper locking (ACID compliant)
    
    Args:
        telegram_id: Customer's Telegram ID
        product_id: Product ID to remove
        
    Returns:
        True if successful, False otherwise
    """
    try:
        with ACIDTransactionManager.atomic_transaction("SERIALIZABLE") as session:
            # Lock customer record
            customer = session.query(Customer).filter(
                Customer.telegram_id == telegram_id
            ).with_for_update().first()
            
            if not customer:
                logger.warning("Customer %d not found for cart removal", telegram_id)
                return False
            
            # Lock cart record
            cart = session.query(Cart).filter(
                Cart.customer_id == customer.id,
                Cart.is_active == True
            ).with_for_update().first()
            
            if not cart:
                logger.warning("No active cart found for customer %d", telegram_id)
                return False

            # Remove items with the specified product_id
            deleted_items = session.query(CartItem).filter(
                CartItem.cart_id == cart.id,
                CartItem.product_id == product_id
            ).delete()

            if deleted_items > 0:
                AuditLogger.log_cart_operation("REMOVE", telegram_id, product_id, deleted_items)
                logger.info("Removed %d items of product %d from cart for customer %d", 
                           deleted_items, product_id, telegram_id)
            else:
                logger.info("No items of product %d found in cart for customer %d", 
                           product_id, telegram_id)

            return True

    except Exception as e:
        logger.error("Atomic cart removal failed: %s", e)
        return False


class ACIDComplianceChecker:
    """ACID compliance checking utilities"""
    
    @staticmethod
    def check_order_consistency(order_id: int) -> Tuple[bool, List[str]]:
        """
        Check order consistency
        
        Args:
            order_id: Order ID to check
            
        Returns:
            Tuple of (is_consistent, list_of_issues)
        """
        try:
            with ACIDTransactionManager.atomic_transaction("READ_COMMITTED") as session:
                order = session.query(Order).filter(Order.id == order_id).first()
                if not order:
                    return False, [f"Order {order_id} not found"]
                
                items = session.query(OrderItem).filter(OrderItem.order_id == order_id).all()
                
                issues = []
                
                # Check order totals
                if not OrderValidator.validate_order_totals(order, items):
                    issues.append("Order totals don't match items")
                
                # Check item consistency
                for item in items:
                    if item.quantity <= 0:
                        issues.append(f"Item {item.id} has invalid quantity: {item.quantity}")
                    if item.unit_price < 0:
                        issues.append(f"Item {item.id} has invalid price: {item.unit_price}")
                    calculated_total = item.unit_price * item.quantity
                    if abs(calculated_total - item.total_price) > 0.01:
                        issues.append(f"Item {item.id} total price mismatch: expected {calculated_total}, got {item.total_price}")
                
                return len(issues) == 0, issues
                
        except Exception as e:
            logger.error("Error checking order consistency: %s", e)
            return False, [f"Error checking consistency: {e}"]
    
    @staticmethod
    def check_cart_consistency(telegram_id: int) -> Tuple[bool, List[str]]:
        """
        Check cart consistency
        
        Args:
            telegram_id: Customer's Telegram ID
            
        Returns:
            Tuple of (is_consistent, list_of_issues)
        """
        try:
            with ACIDTransactionManager.atomic_transaction("READ_COMMITTED") as session:
                customer = session.query(Customer).filter(Customer.telegram_id == telegram_id).first()
                if not customer:
                    return False, [f"Customer {telegram_id} not found"]
                
                cart = session.query(Cart).filter(
                    Cart.customer_id == customer.id,
                    Cart.is_active == True
                ).first()
                
                if not cart:
                    return True, []  # Empty cart is consistent
                
                items = session.query(CartItem).filter(CartItem.cart_id == cart.id).all()
                
                issues = []
                
                # Check item consistency
                for item in items:
                    if item.quantity <= 0:
                        issues.append(f"Cart item {item.id} has invalid quantity: {item.quantity}")
                    if item.unit_price < 0:
                        issues.append(f"Cart item {item.id} has invalid price: {item.unit_price}")
                    calculated_total = item.unit_price * item.quantity
                    if abs(calculated_total - item.total_price) > 0.01:
                        issues.append(f"Cart item {item.id} total price mismatch: expected {calculated_total}, got {item.total_price}")
                
                return len(issues) == 0, issues
                
        except Exception as e:
            logger.error("Error checking cart consistency: %s", e)
            return False, [f"Error checking consistency: {e}"]


@retry_on_database_error()
def get_cart_by_telegram_id(telegram_id: int) -> Cart | None:
    """Get cart by telegram ID"""
    session = get_db_session()
    try:
        customer = session.query(Customer).filter(Customer.telegram_id == telegram_id).first()
        if not customer:
            return None
        return (
            session.query(Cart)
            .options(joinedload(Cart.delivery_area))
            .filter(Cart.customer_id == customer.id)
            .first()
        )
    finally:
        session.close()


@retry_on_database_error()
def update_customer_delivery_address(telegram_id: int, delivery_address: str) -> bool:
    """Update customer's delivery address"""
    session = get_db_session()
    try:
        customer = session.query(Customer).filter(Customer.telegram_id == telegram_id).first()
        if customer:
            customer.delivery_address = delivery_address
            customer.updated_at = datetime.utcnow()
            session.commit()
            logger.info("Updated delivery address for customer %s", telegram_id)
            return True
        else:
            logger.error("Customer %s not found for address update", telegram_id)
            return False
    except SQLAlchemyError as e:
        session.rollback()
        logger.error("Failed to update customer delivery address: %s", e)
        return False
    finally:
        session.close()


@retry_on_database_error()
def update_customer_language(telegram_id: int, language: str) -> bool:
    """Update customer's language preference"""
    session = get_db_session()
    try:
        customer = session.query(Customer).filter(Customer.telegram_id == telegram_id).first()
        if customer:
            customer.language = language
            customer.updated_at = datetime.utcnow()
            session.commit()
            logger.info("Updated language preference for customer %s to %s", telegram_id, language)
            return True
        else:
            logger.error("Customer %s not found for language update", telegram_id)
            return False
    except SQLAlchemyError as e:
        session.rollback()
        logger.error("Failed to update customer language: %s", e)
        return False
    finally:
        session.close()


# Order operations
@retry_on_database_error()
def create_order(
    customer_id: int,
    total_amount: float,
    delivery_method: str = "pickup",
    delivery_address: Optional[str] = None,
) -> Optional[Order]:
    """Create a new order"""
    try:
        with get_db_manager().get_session_context() as session:
            # Calculate subtotal and delivery charge
            subtotal = total_amount
            delivery_charge = 0.0  # For now, no delivery charge
            
            order = Order(
                customer_id=customer_id,
                subtotal=subtotal,
                delivery_charge=delivery_charge,
                total=total_amount,
                delivery_method=delivery_method,
                delivery_address=delivery_address or "",
                status="pending",
            )
            session.add(order)
            session.commit()
            session.refresh(order)
            logger.info("Created order #%s for customer %s", order.order_number, customer_id)
            return order
    except Exception as e:
        logger.error("Failed to create order: %s", e)
        return None

@retry_on_database_error()
def create_order_with_items(
    customer_id: int,
    order_number: str,
    total_amount: float,
    items: list[dict],
    delivery_method: str = "pickup",
    delivery_address: Optional[str] = None,
    delivery_charge: float = 0.0,
    delivery_instructions: Optional[str] = None,
    delivery_area_id: Optional[int] = None,
) -> Optional[Order]:
    """Create a new order with order items from cart items"""
    try:
        with get_db_manager().get_session_context() as session:
            # Calculate subtotal and total with delivery charge
            subtotal = total_amount
            
            # Create the order
            order = Order(
                customer_id=customer_id,
                order_number=order_number,
                subtotal=subtotal,
                delivery_charge=delivery_charge,
                total=subtotal + (delivery_charge or 0.0),
                delivery_method=delivery_method,
                delivery_address=delivery_address or "",
                delivery_instructions=(delivery_instructions or None),
                delivery_area_id=delivery_area_id,
                status="pending"
            )
            session.add(order)
            session.flush()  # Get the order ID
            
            # Create order items
            for item in items:
                product_name = item.get("product_name", "Unknown Product")  # This is stored in DB, not displayed
                quantity = item.get("quantity", 1)
                unit_price = item.get("unit_price", 0)  # Use unit_price from cart item
                total_price = item.get("total_price", unit_price * quantity)  # Use total_price from cart item
                
                order_item = OrderItem(
                    order_id=order.id,
                    product_id=item.get("product_id"),
                    product_name=product_name,
                    product_options=item.get("options", {}),
                    quantity=quantity,
                    unit_price=unit_price,
                    total_price=total_price
                )
                session.add(order_item)
            session.commit()
            session.refresh(order)
            logger.info("Created order #%s with %d items for customer %s", 
                       order_number, len(items), customer_id)
            return order
    except Exception as e:
        logger.error("Failed to create order with items: %s", e)
        return None


@retry_on_database_error()
def update_order_status(order_id: int, new_status: str) -> bool:
    """Update order status"""
    try:
        with get_db_manager().get_session_context() as session:
            order = session.query(Order).filter(Order.id == order_id).first()
            if order:
                order.status = new_status
                order.updated_at = datetime.utcnow()
                session.commit()
                logger.info("Updated order %d status to %s", order_id, new_status)
                return True
            else:
                logger.error("Order %d not found for status update", order_id)
                return False
    except Exception as e:
        logger.error("Failed to update order status: %s", e)
        return False


@retry_on_database_error()
def delete_order(order_id: int) -> bool:
    """Delete an order and its associated items"""
    try:
        with get_db_manager().get_session_context() as session:
            # First, get the order to log it before deletion
            order = session.query(Order).filter(Order.id == order_id).first()
            if not order:
                logger.warning("Order %d not found for deletion", order_id)
                return False
            
            # Log the deletion for audit purposes
            logger.info(
                "ORDER_DELETED: order_id=%d, customer_id=%d, total=%.2f, order_number=%s, status=%s",
                order.id, order.customer_id, order.total, order.order_number, order.status
            )
            
            # Delete order items first (foreign key constraint)
            session.query(OrderItem).filter(OrderItem.order_id == order_id).delete()
            
            # Delete the order
            session.query(Order).filter(Order.id == order_id).delete()
            
            session.commit()
            
            logger.info("Order %d and its items deleted successfully", order_id)
            return True
            
    except Exception as e:
        logger.error("Error deleting order %d: %s", order_id, e)
        return False

def generate_order_number() -> str:
    """Generate unique order number with timestamp and random component"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    # Add 4 random characters to ensure uniqueness
    random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"SS{timestamp}{random_suffix}"


def get_all_customers() -> list[Customer]:
    """Get all customers"""
    session = get_db_session()
    try:
        return session.query(Customer).all()
    finally:
        session.close()


def get_all_orders() -> list[Order]:
    """Get all orders with customer and order_items information"""
    session = get_db_session()
    try:
        from sqlalchemy.orm import joinedload
        return (
            session.query(Order)
            .options(joinedload(Order.customer), joinedload(Order.order_items))
            .order_by(Order.created_at.desc())
            .all()
        )
    finally:
        session.close()


def check_database_connection() -> bool:
    """Check if database connection is available"""
    try:
        engine = get_db_manager().get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False


def get_database_status() -> dict:
    """Get comprehensive database status information"""
    status = {
        "connected": False,
        "error": None,
        "connection_string": None,
        "database_type": None
    }
    
    try:
        config = get_config()
        
        # Determine which connection string is being used
        if config.supabase_connection_string:
            status["connection_string"] = "supabase"
            status["database_type"] = "postgresql"
        else:
            status["connection_string"] = "local"
            status["database_type"] = "postgresql" if "postgresql" in config.database_url else "other"
        
        # Test connection
        status["connected"] = check_database_connection()
        
    except Exception as e:
        status["error"] = str(e)
        logger.error(f"Error getting database status: {e}")
    
    return status

@retry_on_database_error()
def create_category(
    name_en: str, 
    name_he: str,
    description: str = None, 
    display_order: int = None, 
    image_url: str = None,
    description_en: Optional[str] = None,
    description_he: Optional[str] = None
) -> Optional[MenuCategory]:
    """Create a new category with multilingual support"""
    session = get_db_session()
    try:
        # Check if category already exists (check both English and Hebrew names)
        existing_cat = session.query(MenuCategory).filter(
            (MenuCategory.name_en == name_en) | (MenuCategory.name_he == name_he)
        ).first()
        
        if existing_cat:
            logger.warning("Category already exists")
            return None
        
        # Create new category
        category = MenuCategory(
            name_en=name_en,
            name_he=name_he,
            description=description,
            display_order=display_order,
            image_url=image_url,
            description_en=description_en,
            description_he=description_he
        )
        
        session.add(category)
        session.commit()
        # Clear cache so category lists refresh everywhere
        try:
            from src.utils.helpers import SimpleCache
            cache = SimpleCache()
            cache.clear()
            logger.info("Cleared cache after creating category '%s'", name_en)
        except Exception as cache_error:
            logger.warning("Failed to clear cache after creating category '%s': %s", name_en, cache_error)
        
        logger.info("Successfully created category: %s (EN) / %s (HE)", name_en, name_he)
        return category
        
    except Exception as e:
        session.rollback()
        logger.error("Failed to create category '%s'/'%s': %s", name_en, name_he, e)
        return None
    finally:
        session.close()


@retry_on_database_error()
def delete_category(name_en: str, name_he: str = None) -> bool:
    """Delete a category by English name (and optionally Hebrew name)"""
    session = get_db_session()
    try:
        # Find category by English name, or by both if Hebrew name provided
        if name_he:
            category = session.query(MenuCategory).filter(
                (MenuCategory.name_en == name_en) & (MenuCategory.name_he == name_he)
            ).first()
        else:
            category = session.query(MenuCategory).filter(MenuCategory.name_en == name_en).first()
        
        if not category:
            logger.warning("Category not found")
            return False
        
        # Count products in this category
        product_count = session.query(Product).filter(Product.category_id == category.id).count()
        
        # Delete the category (products will be orphaned)
        session.delete(category)
        session.commit()
        # Clear cache after deleting category
        try:
            from src.utils.helpers import SimpleCache
            cache = SimpleCache()
            cache.clear()
            logger.info("Cleared cache after deleting category '%s'", name_en)
        except Exception as cache_error:
            logger.warning("Failed to clear cache after deleting category '%s': %s", name_en, cache_error)
        
        logger.info("Successfully deleted category '%s' with %d products", name_en, product_count)
        return True
        
    except Exception as e:
        session.rollback()
        logger.error("Failed to delete category '%s': %s", name_en, e)
        return False
    finally:
        session.close()


@retry_on_database_error()
def get_business_settings() -> Optional[BusinessSettings]:
    """Get business settings (creates default if none exist)"""
    session = get_db_session()
    try:
        settings = session.query(BusinessSettings).first()
        if not settings:
            # Create default settings
            from src.config import get_config
            config = get_config()
            
            settings = BusinessSettings(
                business_name="Samna Salta",
                business_description="Traditional Yemeni restaurant serving authentic dishes",
                delivery_charge=config.delivery_charge,
                currency=config.currency,
                hilbeh_available_days=json.dumps(config.hilbeh_available_days),
                hilbeh_available_hours=config.hilbeh_available_hours,
                app_images=None
            )
            session.add(settings)
            session.commit()
            session.refresh(settings)
            logger.info("Created default business settings")
        
        return settings
    except SQLAlchemyError as e:
        session.rollback()
        logger.error("Failed to get business settings: %s", e)
        return None
    finally:
        session.close()


@retry_on_database_error()
def update_business_settings(**kwargs) -> bool:
    """Update business settings"""
    session = get_db_session()
    try:
        settings = session.query(BusinessSettings).first()
        if not settings:
            logger.warning("No business settings found to update")
            return False
        
        # Update allowed fields
        allowed_fields = [
            'business_name', 'business_description', 'business_address',
            'business_phone', 'business_email', 'business_website',
            'business_hours', 'delivery_charge', 'currency',
            'hilbeh_available_days', 'hilbeh_available_hours',
            'welcome_message', 'about_us', 'contact_info', 'app_images'
        ]
        
        for field, value in kwargs.items():
            if field in allowed_fields:
                if field == 'hilbeh_available_days' and isinstance(value, list):
                    setattr(settings, field, json.dumps(value))
                elif field == 'app_images' and isinstance(value, dict):
                    # Store as JSON
                    setattr(settings, field, json.dumps(value))
                else:
                    setattr(settings, field, value)
        
        settings.updated_at = datetime.utcnow()
        session.commit()
        logger.info("Updated business settings: %s", list(kwargs.keys()))
        # Clear in-memory caches so changes reflect immediately (e.g., step images)
        try:
            from src.utils.helpers import SimpleCache
            cache = SimpleCache()
            cache.clear()
            logger.info("Cleared cache after updating business settings")
        except Exception as _e:
            logger.debug("Failed to clear cache after settings update: %s", _e)
        return True
    except SQLAlchemyError as e:
        session.rollback()
        logger.error("Failed to update business settings: %s", e)
        return False
    finally:
        session.close()


@retry_on_database_error()
def get_business_settings_dict() -> dict:
    """Get business settings as dictionary"""
    db_manager = get_db_manager()
    
    with db_manager.get_session_context() as session:
        settings = session.query(BusinessSettings).first()
        
        if settings:
            return settings.to_dict()
        else:
            # Return default settings if none exist
            return {
                "business_name": "Samna Salta",
                "business_description": None,
                "business_address": None,
                "business_phone": None,
                "business_email": None,
                "business_website": None,
                "business_hours": None,
                "delivery_charge": 5.00,
                "currency": "ILS",
                "hilbeh_available_days": None,
                "hilbeh_available_hours": None,
                "welcome_message": None,
                "about_us": None,
                "contact_info": None
            }


# ============================================================================
# CONSTANT MODELS OPERATIONS
# ============================================================================

@retry_on_database_error()
def get_product_options(option_type: Optional[str] = None, language: str = "en") -> List[Dict]:
    """Get product options with optional filtering by type"""
    db_manager = get_db_manager()
    
    with db_manager.get_session_context() as session:
        query = session.query(ProductOption).filter(ProductOption.is_active == True)
        
        if option_type:
            query = query.filter(ProductOption.option_type == option_type)
        
        query = query.order_by(ProductOption.display_order)
        options = query.all()
        
        result = []
        for option in options:
            result.append({
                "id": option.id,
                "name": option.name,
                "display_name": option.get_localized_display_name(language),
                "description": option.get_localized_description(language),
                "option_type": option.option_type,
                "price_modifier": option.price_modifier,
                "display_order": option.display_order
            })
        
        return result


@retry_on_database_error()
def get_product_option_by_name(name: str, option_type: str, language: str = "en") -> Optional[Dict]:
    """Get a specific product option by name and type"""
    db_manager = get_db_manager()
    
    with db_manager.get_session_context() as session:
        option = session.query(ProductOption).filter(
            ProductOption.name == name,
            ProductOption.option_type == option_type,
            ProductOption.is_active == True
        ).first()
        
        if option:
            return {
                "id": option.id,
                "name": option.name,
                "display_name": option.get_localized_display_name(language),
                "description": option.get_localized_description(language),
                "option_type": option.option_type,
                "price_modifier": option.price_modifier,
                "display_order": option.display_order
            }
        return None


@retry_on_database_error()
def get_product_sizes(language: str = "en") -> List[Dict]:
    """Get all product sizes"""
    db_manager = get_db_manager()
    
    with db_manager.get_session_context() as session:
        sizes = session.query(ProductSize).filter(
            ProductSize.is_active == True
        ).order_by(ProductSize.display_order).all()
        
        result = []
        for size in sizes:
            result.append({
                "id": size.id,
                "name": size.name,
                "display_name": size.get_localized_display_name(language),
                "price_modifier": size.price_modifier,
                "display_order": size.display_order
            })
        
        return result


@retry_on_database_error()
def get_product_size_by_name(name: str, language: str = "en") -> Optional[Dict]:
    """Get a specific product size by name"""
    db_manager = get_db_manager()
    
    with db_manager.get_session_context() as session:
        size = session.query(ProductSize).filter(
            ProductSize.name == name,
            ProductSize.is_active == True
        ).first()
        
        if size:
            return {
                "id": size.id,
                "name": size.name,
                "display_name": size.get_localized_display_name(language),
                "price_modifier": size.price_modifier,
                "display_order": size.display_order
            }
        return None


@retry_on_database_error()
def get_order_statuses(language: str = "en") -> List[Dict]:
    """Get all order statuses"""
    db_manager = get_db_manager()
    
    with db_manager.get_session_context() as session:
        statuses = session.query(OrderStatus).filter(
            OrderStatus.is_active == True
        ).order_by(OrderStatus.display_order).all()
        
        result = []
        for status in statuses:
            result.append({
                "id": status.id,
                "name": status.name,
                "display_name": status.get_localized_display_name(language),
                "description": status.get_localized_description(language),
                "color": status.color,
                "icon": status.icon,
                "display_order": status.display_order
            })
        
        return result


@retry_on_database_error()
def get_order_status_by_name(name: str, language: str = "en") -> Optional[Dict]:
    """Get a specific order status by name"""
    db_manager = get_db_manager()
    
    with db_manager.get_session_context() as session:
        status = session.query(OrderStatus).filter(
            OrderStatus.name == name,
            OrderStatus.is_active == True
        ).first()
        
        if status:
            return {
                "id": status.id,
                "name": status.name,
                "display_name": status.get_localized_display_name(language),
                "description": status.get_localized_description(language),
                "color": status.color,
                "icon": status.icon,
                "display_order": status.display_order
            }
        return None


@retry_on_database_error()
def get_delivery_methods(language: str = "en") -> List[Dict]:
    """Get all delivery methods"""
    db_manager = get_db_manager()
    
    with db_manager.get_session_context() as session:
        methods = session.query(DeliveryMethod).filter(
            DeliveryMethod.is_active == True
        ).order_by(DeliveryMethod.display_order).all()
        
        result = []
        for method in methods:
            result.append({
                "id": method.id,
                "name": method.name,
                "display_name": method.get_localized_display_name(language),
                "description": method.get_localized_description(language),
                "charge": method.charge,
                "display_order": method.display_order
            })
        
        return result


@retry_on_database_error()
def get_delivery_method_by_name(name: str, language: str = "en") -> Optional[Dict]:
    """Get a specific delivery method by name"""
    db_manager = get_db_manager()
    
    with db_manager.get_session_context() as session:
        method = session.query(DeliveryMethod).filter(
            DeliveryMethod.name == name,
            DeliveryMethod.is_active == True
        ).first()
        
        if method:
            return {
                "id": method.id,
                "name": method.name,
                "display_name": method.get_localized_display_name(language),
                "description": method.get_localized_description(language),
                "charge": method.charge,
                "display_order": method.display_order
            }
        return None


@retry_on_database_error()
def get_payment_methods(language: str = "en") -> List[Dict]:
    """Get all payment methods"""
    db_manager = get_db_manager()
    
    with db_manager.get_session_context() as session:
        methods = session.query(PaymentMethod).filter(
            PaymentMethod.is_active == True
        ).order_by(PaymentMethod.display_order).all()
        
        result = []
        for method in methods:
            result.append({
                "id": method.id,
                "name": method.name,
                "display_name": method.get_localized_display_name(language),
                "description": method.get_localized_description(language),
                "display_order": method.display_order
            })
        
        return result


@retry_on_database_error()
def get_payment_method_by_name(name: str, language: str = "en") -> Optional[Dict]:
    """Get a specific payment method by name"""
    db_manager = get_db_manager()
    
    with db_manager.get_session_context() as session:
        method = session.query(PaymentMethod).filter(
            PaymentMethod.name == name,
            PaymentMethod.is_active == True
        ).first()
        
        if method:
            return {
                "id": method.id,
                "name": method.name,
                "display_name": method.get_localized_display_name(language),
                "description": method.get_localized_description(language),
                "display_order": method.display_order
            }
        return None


@retry_on_database_error()
def get_localized_constant(constant_type: str, name: str, language: str = "en") -> Optional[str]:
    """Get localized display name for any constant type"""
    db_manager = get_db_manager()
    
    with db_manager.get_session_context() as session:
        if constant_type == "product_option":
            item = session.query(ProductOption).filter(
                ProductOption.name == name,
                ProductOption.is_active == True
            ).first()
            if item:
                return item.get_localized_display_name(language)
        
        elif constant_type == "product_size":
            item = session.query(ProductSize).filter(
                ProductSize.name == name,
                ProductSize.is_active == True
            ).first()
            if item:
                return item.get_localized_display_name(language)
        
        elif constant_type == "order_status":
            item = session.query(OrderStatus).filter(
                OrderStatus.name == name,
                OrderStatus.is_active == True
            ).first()
            if item:
                return item.get_localized_display_name(language)
        
        elif constant_type == "delivery_method":
            item = session.query(DeliveryMethod).filter(
                DeliveryMethod.name == name,
                DeliveryMethod.is_active == True
            ).first()
            if item:
                return item.get_localized_display_name(language)
        
        elif constant_type == "payment_method":
            item = session.query(PaymentMethod).filter(
                PaymentMethod.name == name,
                PaymentMethod.is_active == True
            ).first()
            if item:
                return item.get_localized_display_name(language)
        
        return None


@retry_on_database_error()
def get_delivery_charge(method_name: str) -> float:
    """Get delivery charge for a specific method"""
    db_manager = get_db_manager()
    
    with db_manager.get_session_context() as session:
        method = session.query(DeliveryMethod).filter(
            DeliveryMethod.name == method_name,
            DeliveryMethod.is_active == True
        ).first()
        
        if method:
            return method.charge
        return 0.0


@retry_on_database_error()
def get_current_delivery_charge() -> float:
    """Get the business-configured delivery charge from BusinessSettings.
    Falls back to delivery_methods('delivery') if settings not present.
    """
    try:
        settings = get_business_settings_dict()
        if settings and settings.get("delivery_charge") is not None:
            return float(settings["delivery_charge"]) or 0.0
    except Exception:
        pass
    # Fallback to delivery_methods table
    return get_delivery_charge("delivery")


@retry_on_database_error()
def get_active_delivery_areas() -> list[DeliveryArea]:
    """Return all active delivery areas ordered for display"""
    db_manager = get_db_manager()
    with db_manager.get_session_context() as session:
        return (
            session.query(DeliveryArea)
            .filter(DeliveryArea.is_active == True)  # noqa: E712
            .order_by(DeliveryArea.display_order, DeliveryArea.name_en)
            .all()
        )


@retry_on_database_error()
def get_delivery_area_by_id(area_id: int) -> Optional[DeliveryArea]:
    db_manager = get_db_manager()
    with db_manager.get_session_context() as session:
        return session.query(DeliveryArea).filter(DeliveryArea.id == area_id).first()


@retry_on_database_error()
def create_delivery_area(name_en: str, name_he: str, charge: Optional[float]) -> bool:
    """Create a new delivery area"""
    db_manager = get_db_manager()
    try:
        with db_manager.get_session_context() as session:
            area = DeliveryArea(name_en=name_en.strip(), name_he=name_he.strip(), charge=charge, is_active=True)
            session.add(area)
            session.commit()
            logger.info("Created delivery area: %s / %s (charge=%s)", name_en, name_he, charge)
            return True
    except Exception as e:
        logger.error("Failed to create delivery area: %s", e)
        return False
