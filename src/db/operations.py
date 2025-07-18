"""
Database operations with retry logic and connection management

Enhanced with proper type annotations, constant usage, and performance optimizations.
"""

import logging
# PostgreSQL operations only
import time
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Union, Generator
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
    CoreBusiness,
    AnalyticsDailySales,
    AnalyticsProductPerformance,
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

logger = logging.getLogger(__name__)


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
            # when the table already exists but column is missing.  This keeps
            # Render deploys working without Alembic.
            # ------------------------------------------------------------------

            engine = self.get_engine()
            dialect_name = engine.dialect.name
            
            if dialect_name == "postgresql":
                conn = engine.connect()

                def _column_exists(table: str, column: str) -> bool:
                    query = text("""
                        SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_name = :table AND column_name = :column
                    """)
                    result = conn.execute(query, {"table": table, "column": column}).fetchone()
                    return result is not None

                migrations = [
                    ("carts", "delivery_method", "ALTER TABLE carts ADD COLUMN delivery_method VARCHAR(20) DEFAULT 'pickup'"),
                    ("carts", "delivery_address", "ALTER TABLE carts ADD COLUMN delivery_address VARCHAR(500)"),
                    ("carts", "created_at", "ALTER TABLE carts ADD COLUMN created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP"),
                    ("carts", "updated_at", "ALTER TABLE carts ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE"),
                    ("cart_items", "product_options", "ALTER TABLE cart_items ADD COLUMN product_options JSONB DEFAULT '{}'"),
                    ("cart_items", "created_at", "ALTER TABLE cart_items ADD COLUMN created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP"),
                    ("cart_items", "updated_at", "ALTER TABLE cart_items ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE"),
                ]

                for table, column, ddl in migrations:
                    if not _column_exists(table, column):
                        self.logger.info("Auto-migrating PostgreSQL: %s", ddl)
                        conn.execute(text(ddl))

                conn.close()

            self.logger.info("Database tables created/updated successfully")
        except SQLAlchemyError as e:
            self.logger.error(f"Failed to create database tables: {e}", exc_info=True)
            raise DatabaseOperationError(
                f"Failed to create database tables: {e}", ErrorCodes.DATABASE_ERROR
            ) from e

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


def reinitialize_products_with_categories():
    """Reinitialize products with proper category relationships"""
    session = get_db_session()
    try:
        # First, create categories
        categories_data = [
            {"name": "bread", "description": "Traditional breads", "display_order": 1},
            {"name": "spread", "description": "Traditional spreads and condiments", "display_order": 2},
            {"name": "spice", "description": "Traditional spice blends", "display_order": 3},
            {"name": "beverage", "description": "Traditional beverages", "display_order": 4},
        ]
        
        # Create categories and store them in a dict for easy lookup
        categories = {}
        for cat_data in categories_data:
            existing_cat = session.query(MenuCategory).filter(MenuCategory.name == cat_data["name"]).first()
            if existing_cat:
                categories[cat_data["name"]] = existing_cat
            else:
                category = MenuCategory(**cat_data)
                session.add(category)
                session.flush()  # Get the ID
                categories[cat_data["name"]] = category

        # Update existing products with proper category relationships
        product_updates = [
            ("Kubaneh", "bread"),
            ("Samneh", "spread"),
            ("Red Bisbas", "spice"),
            ("Hawaij soup spice", "spice"),
            ("Hawaij coffee spice", "spice"),
            ("White coffee", "beverage"),
            ("Hilbeh", "spread"),
        ]

        for product_name, category_name in product_updates:
            product = session.query(Product).filter(Product.name == product_name).first()
            if product and category_name in categories:
                product.category_id = categories[category_name].id
                logger.info(f"Updated product '{product_name}' with category '{category_name}'")

        session.commit()
        logger.info("Successfully reinitialized products with proper categories")

    except SQLAlchemyError as e:
        session.rollback()
        logger.error("Failed to reinitialize products: %s", e)
        raise
    finally:
        session.close()


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

            # Initialize default products
            init_default_products()
            
            # Reinitialize products with proper categories (in case they were created without categories)
            reinitialize_products_with_categories()
            
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

        # First, create categories
        categories_data = [
            {"name": "bread", "description": "Traditional breads", "display_order": 1},
            {"name": "spread", "description": "Traditional spreads and condiments", "display_order": 2},
            {"name": "spice", "description": "Traditional spice blends", "display_order": 3},
            {"name": "beverage", "description": "Traditional beverages", "display_order": 4},
        ]
        
        # Create categories and store them in a dict for easy lookup
        categories = {}
        for cat_data in categories_data:
            existing_cat = session.query(MenuCategory).filter(MenuCategory.name == cat_data["name"]).first()
            if existing_cat:
                categories[cat_data["name"]] = existing_cat
            else:
                category = MenuCategory(**cat_data)
                session.add(category)
                session.flush()  # Get the ID
                categories[cat_data["name"]] = category

        # Default products configuration
        products = [
            {
                "name": "Kubaneh",
                "category_id": categories["bread"].id,
                "description": "Traditional Yemenite bread",
                "price": 25.00,
            },
            {
                "name": "Samneh",
                "category_id": categories["spread"].id,
                "description": "Traditional clarified butter",
                "price": 15.00,
            },
            {
                "name": "Red Bisbas",
                "category_id": categories["spice"].id,
                "description": "Traditional Yemenite spice blend",
                "price": 12.00,
            },
            {
                "name": "Hawaij soup spice",
                "category_id": categories["spice"].id,
                "description": "Traditional soup spice blend",
                "price": 8.00,
            },
            {
                "name": "Hawaij coffee spice",
                "category_id": categories["spice"].id,
                "description": "Traditional coffee spice blend",
                "price": 8.00,
            },
            {
                "name": "White coffee",
                "category_id": categories["beverage"].id,
                "description": "Traditional Yemenite white coffee",
                "price": 10.00,
            },
            {
                "name": "Hilbeh",
                "category_id": categories["spread"].id,
                "description": "Traditional fenugreek spread (available Wed-Fri only)",
                "price": 18.00,
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
    telegram_id: int, full_name: str, phone_number: str, language: str = "en"
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
            name=full_name, 
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
    """Get all products (including inactive) for admin management"""
    session = get_db_session()
    try:
        products = session.query(Product, MenuCategory.name.label('category_name')).join(MenuCategory).order_by(MenuCategory.name, Product.name).all()
        
        result = []
        for product, category_name in products:
            result.append({
                "id": product.id,
                "name": product.name,
                "description": product.description,
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
    """Get product by ID as a dictionary with category name resolved"""
    session = get_db_session()
    try:
        product = session.query(Product).options(joinedload(Product.category_rel)).filter(Product.id == product_id).first()
        if not product:
            return None
        
        return {
            "id": product.id,
            "name": product.name,
            "description": product.description,
            "category": product.category_rel.name if product.category_rel else "Uncategorized",
            "price": product.price,
            "is_active": product.is_active,
            "created_at": product.created_at,
            "updated_at": product.updated_at
        }
    finally:
        session.close()


@retry_on_database_error()
def create_product(name: str, description: str, category: str, price: float) -> Optional[Product]:
    """Create a new product"""
    session = get_db_session()
    try:
        # Check if product with same name already exists
        existing_product = session.query(Product).filter(Product.name == name).first()
        if existing_product:
            logger.warning("Product with name '%s' already exists", name)
            return None
        
        # Get category by name
        category_obj = session.query(MenuCategory).filter(MenuCategory.name == category).first()
        if not category_obj:
            logger.warning("Category '%s' not found", category)
            return None
        
        product = Product(
            name=name,
            description=description,
            category_id=category_obj.id,
            price=price,
            is_active=True
        )
        session.add(product)
        session.commit()
        session.refresh(product)
        logger.info("Created new product: %s (ID: %d)", name, product.id)
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
        allowed_fields = ['name', 'description', 'price', 'is_active']
        for field, value in kwargs.items():
            if field in allowed_fields:
                setattr(product, field, value)
            elif field == 'category':
                # Handle category by name
                category_obj = session.query(MenuCategory).filter(MenuCategory.name == value).first()
                if category_obj:
                    product.category_id = category_obj.id
                else:
                    logger.warning("Category '%s' not found", value)
                    return False
        
        product.updated_at = datetime.utcnow()
        session.commit()
        logger.info("Updated product ID %d: %s", product_id, kwargs)
        return True
    except SQLAlchemyError as e:
        session.rollback()
        logger.error("Failed to update product ID %d: %s", product_id, e)
        return False
    finally:
        session.close()


@retry_on_database_error()
def delete_product(product_id: int) -> bool:
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
        logger.info("Soft deleted product ID %d: %s", product_id, product.name)
        return True
    except SQLAlchemyError as e:
        session.rollback()
        logger.error("Failed to delete product ID %d: %s", product_id, e)
        return False
    finally:
        session.close()


@retry_on_database_error()
def get_product_categories() -> list[str]:
    """Get all unique product categories that have active products"""
    session = get_db_session()
    try:
        # Get categories that have active products
        categories = session.query(MenuCategory).join(Product).filter(
            Product.is_active == True
        ).distinct().all()
        return [cat.name for cat in categories]
    finally:
        session.close()


@retry_on_database_error()
def get_products_by_category(category: str) -> list[Product]:
    """Get all active products in a specific category"""
    session = get_db_session()
    try:
        # First get the category by name
        category_obj = session.query(MenuCategory).filter(MenuCategory.name == category).first()
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
        # First get the category by name
        category_obj = session.query(MenuCategory).filter(MenuCategory.name == category).first()
        if not category_obj:
            return []
        
        # Then get products by category_id
        return session.query(Product).filter(
            Product.category_id == category_obj.id
        ).all()
    finally:
        session.close()


@retry_on_database_error()
def search_products(search_term: str) -> list[Product]:
    """Search products by name or description"""
    session = get_db_session()
    try:
        search_pattern = f"%{search_term}%"
        return session.query(Product).filter(
            Product.is_active == True,
            (Product.name.ilike(search_pattern) | Product.description.ilike(search_pattern))
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
    """Add a product to the customer's cart"""
    try:
        with get_db_manager().get_session_context() as session:
            # Get or create customer
            customer = session.query(Customer).filter(Customer.telegram_id == telegram_id).first()
            if not customer:
                logger.error("Customer %s not found for cart operation", telegram_id)
                return False

            # Get or create cart
            cart = session.query(Cart).filter(
                Cart.customer_id == customer.id,
                Cart.is_active == True
            ).first()
            
            if not cart:
                cart = Cart(
                    customer_id=customer.id,
                    is_active=True,
                    delivery_method="pickup"
                )
                session.add(cart)
                session.flush()

            # Get product
            product = session.query(Product).filter(Product.id == product_id).first()
            if not product:
                logger.error("Product %d not found for cart operation", product_id)
                return False

            # Check if item already exists in cart
            existing_item = session.query(CartItem).filter(
                CartItem.cart_id == cart.id,
                CartItem.product_id == product_id
            ).first()

            if existing_item:
                # Update quantity
                existing_item.quantity += quantity
                existing_item.updated_at = datetime.utcnow()
                logger.info("Updated quantity for product %d in cart for customer %s", product_id, telegram_id)
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
                logger.info("Added product %d to cart for customer %s", product_id, telegram_id)

            session.commit()
            return True

    except Exception as e:
        logger.error("Failed to add to cart: %s", e)
        return False


@retry_on_database_error()
def get_cart_items(telegram_id: int) -> list[dict]:
    """Get all items in the customer's cart"""
    try:
        with get_db_manager().get_session_context() as session:
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

            # Get cart items with product information
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
                    "quantity": cart_item.quantity,
                    "unit_price": float(cart_item.unit_price),
                    "total_price": float(cart_item.unit_price * cart_item.quantity),
                    "options": cart_item.product_options or {},
                    "special_instructions": cart_item.special_instructions or "",
                    "product_description": product.description,
                    "product_image_url": product.image_url
                }
                items.append(item_data)

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
    """Clear all items from a cart"""
    session = get_db_session()
    try:
        customer = session.query(Customer).filter(Customer.telegram_id == telegram_id).first()
        if not customer:
            return False
        
        cart = session.query(Cart).filter(Cart.customer_id == customer.id).first()
        if cart:
            # Delete all cart items
            session.query(CartItem).filter(CartItem.cart_id == cart.id).delete()
            # Delete the cart itself
            session.delete(cart)
            session.commit()
        return True
    except SQLAlchemyError as e:
        session.rollback()
        logger.error("Failed to clear cart: %s", e)
        return False
    finally:
        session.close()


@retry_on_database_error()
def remove_from_cart(telegram_id: int, product_id: int) -> bool:
    """Remove item from cart"""
    session = get_db_session()
    try:
        customer = session.query(Customer).filter(Customer.telegram_id == telegram_id).first()
        if not customer:
            return False
        
        cart = session.query(Cart).filter(Cart.customer_id == customer.id).first()
        if not cart:
            return False

        # Remove items with the specified product_id
        session.query(CartItem).filter(
            CartItem.cart_id == cart.id,
            CartItem.product_id == product_id
        ).delete()

        session.commit()
        return True

    except SQLAlchemyError as e:
        session.rollback()
        logger.error("Failed to remove from cart: %s", e)
        return False
    finally:
        session.close()


@retry_on_database_error()
def get_cart_by_telegram_id(telegram_id: int) -> Cart | None:
    """Get cart by telegram ID"""
    session = get_db_session()
    try:
        customer = session.query(Customer).filter(Customer.telegram_id == telegram_id).first()
        if not customer:
            return None
        return session.query(Cart).filter(Cart.customer_id == customer.id).first()
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
                total_amount=total_amount,
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
) -> Optional[Order]:
    """Create a new order with order items from cart items"""
    try:
        with get_db_manager().get_session_context() as session:
            # Calculate subtotal and delivery charge
            subtotal = total_amount
            delivery_charge = 0.0  # For now, no delivery charge
            
            # Create the order
            order = Order(
                customer_id=customer_id,
                order_number=order_number,
                total_amount=total_amount,
                subtotal=subtotal,
                delivery_charge=delivery_charge,
                total=total_amount,
                delivery_method=delivery_method,
                delivery_address=delivery_address or "",
                status="pending"
            )
            session.add(order)
            session.flush()  # Get the order ID
            
            # Create order items
            for item in items:
                product_name = item.get("product_name", "Unknown Product")
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
