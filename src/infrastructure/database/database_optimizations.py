"""
Database optimizations for improved performance and scalability
"""

import logging
import shutil
import threading
import time
from contextlib import contextmanager
from typing import Any, Dict, Optional

from sqlalchemy import Index, create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

from src.infrastructure.configuration.config import get_config
from src.infrastructure.database.models import (
    Base,
    Cart,
    Customer,
    Order,
    OrderItem,
    Product,
)

logger = logging.getLogger(__name__)


class DatabaseConnectionManager:
    """
    Optimized database connection manager with connection pooling
    and performance monitoring
    """

    _instance: Optional["DatabaseConnectionManager"] = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "_initialized"):
            with self._lock:
                if not hasattr(self, "_initialized"):
                    self._engine: Optional[Engine] = None
                    self._session_local = None
                    self._setup_engine()
                    self._setup_indexes()
                    self._setup_performance_monitoring()
                    self._initialized = True

    def _setup_engine(self):
        """Setup database engine with connection pooling"""
        config = get_config()

        # Connection pool configuration
        pool_settings = {
            "poolclass": QueuePool,
            "pool_size": 10,  # Number of connections to maintain
            "max_overflow": 20,  # Additional connections when pool is full
            "pool_recycle": 3600,  # Recycle connections after 1 hour
            "pool_pre_ping": True,  # Verify connections before use
        }

        # Production vs Development settings
        if config.environment == "production":
            # PostgreSQL settings for production
            if config.database_url.startswith(
                "postgresql"
            ):  # pylint: disable=no-member
                pool_settings.update(
                    {
                        "pool_size": 20,
                        "max_overflow": 30,
                        "echo": False,
                    }
                )
        else:
            # SQLite settings for development
            pool_settings.update(
                {
                    "pool_size": 5,
                    "max_overflow": 10,
                    "echo": True,  # Log SQL queries in development
                }
            )

        self._engine = create_engine(config.database_url, **pool_settings)

        self._session_local = sessionmaker(
            autocommit=False, autoflush=False, bind=self._engine
        )

        logger.info("Database engine configured for %s", config.environment)

    def _setup_indexes(self):
        """Setup database indexes for improved query performance"""
        try:
            # Customer indexes
            Index("idx_customer_telegram_id", Customer.telegram_id, unique=True)
            Index("idx_customer_phone", Customer.phone_number, unique=True)

            # Product indexes
            Index("idx_product_category", Product.category)
            Index("idx_product_active", Product.is_active)
            Index("idx_product_name", Product.name)

            # Order indexes
            Index("idx_order_customer", Order.customer_id)
            Index("idx_order_status", Order.status)
            Index("idx_order_created", Order.created_at)
            Index("idx_order_number", Order.order_number, unique=True)

            # Order item indexes
            Index("idx_orderitem_order", OrderItem.order_id)

            # Cart indexes
            Index("idx_cart_telegram_id", Cart.telegram_id, unique=True)

            logger.info("Database indexes configured")

        except RuntimeError as e:
            logger.warning("Error setting up indexes: %s", e)

    def _setup_performance_monitoring(self):
        """Setup performance monitoring for database operations"""

        @event.listens_for(Engine, "before_cursor_execute")
        def receive_before_cursor_execute(
            _conn, _cursor, _statement, _parameters, context, _executemany
        ):
            setattr(context, "query_start_time", time.time())

        @event.listens_for(Engine, "after_cursor_execute")
        def receive_after_cursor_execute(
            _conn, _cursor, statement, _parameters, context, _executemany
        ):
            total = time.time() - getattr(context, "query_start_time", 0)

            # Log slow queries (> 100ms)
            if total > 0.1:
                logger.warning(
                    "Slow query detected: %.3fs - %s...", total, statement[:100]
                )

            # Log all queries in debug mode
            logger.debug("Query executed in %.3fs: %s...", total, statement[:50])

    @property
    def engine(self) -> Engine:
        """Get database engine"""
        return self._engine

    @contextmanager
    def get_session(self):
        """Get database session with automatic cleanup"""
        session = self._session_local()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def create_all_tables(self):
        """Create all database tables"""
        Base.metadata.create_all(bind=self._engine)
        logger.info("All database tables created")

    def get_connection_info(self) -> Dict[str, Any]:
        """Get connection pool information"""
        pool = self._engine.pool
        return {
            "pool_size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
        }


def get_database_manager() -> "DatabaseConnectionManager":
    """Get the global database manager instance"""
    return DatabaseConnectionManager()


# Optimized query functions
class OptimizedQueries:
    """Optimized database queries for common operations"""

    def __init__(self, db_manager: DatabaseConnectionManager):
        self.db_manager = db_manager

    def get_active_products_by_category(self, category: str):
        """Optimized query for active products by category"""
        with self.db_manager.get_session() as session:
            return (
                session.query(Product)
                .filter(Product.category == category, Product.is_active.is_(True))
                .all()
            )

    def get_all_active_products(self):
        """Optimized query for all active products"""
        with self.db_manager.get_session() as session:
            return session.query(Product).filter(Product.is_active.is_(True)).all()

    def get_customer_order_history(self, customer_id: int, limit: int = 10):
        """Optimized query for customer order history"""
        with self.db_manager.get_session() as session:
            return (
                session.query(Order)
                .filter(Order.customer_id == customer_id)
                .order_by(Order.created_at.desc())
                .limit(limit)
                .all()
            )

    def get_popular_products(self, limit: int = 10):
        """Get most popular products based on order frequency"""
        with self.db_manager.get_session() as session:
            return (
                session.query(
                    Product.name,
                    session.query(OrderItem.product_name)
                    .filter(OrderItem.product_name == Product.name)
                    .count()
                    .label("order_count"),
                )
                .group_by(Product.name)
                .order_by("order_count DESC")
                .limit(limit)
                .all()
            )


# Database health check
def check_database_health() -> Dict[str, Any]:
    """Check database health and performance metrics"""
    db_manager = get_database_manager()

    try:
        with db_manager.get_session() as session:
            # Basic connectivity test
            session.execute("SELECT 1")

        # Connection pool status
        pool_info = db_manager.get_connection_info()

        return {
            "status": "ok",
            "database": db_manager.engine.url.database,
            "pool_info": pool_info,
        }
    except OperationalError as e:
        logger.error("Database health check failed: %s", e)
        return {"status": "error", "error": str(e)}
    except Exception as e:
        logger.critical("An unexpected error occurred during health check: %s", e)
        return {"status": "error", "error": "An unexpected error occurred"}


# Migration utilities
def run_database_migrations():
    """Run database migrations using Alembic"""
    # This is a placeholder for a more robust migration script
    # For a real application, use Alembic or a similar tool
    logger.info("Running database migrations...")
    try:
        # Placeholder for migration logic
        pass
    except Exception as e:
        logger.error("Error running migrations: %s", e)
        raise


def create_database_backup(backup_path: str) -> bool:
    """Create a backup of the database file."""
    db_manager = get_database_manager()
    db_url = db_manager.engine.url

    if db_url.drivername != "sqlite":
        logger.warning("Database backup is only supported for SQLite.")
        return False

    db_path = db_url.database
    if not db_path:
        logger.error("Database path not found in configuration.")
        return False

    try:
        shutil.copyfile(db_path, backup_path)
        logger.info("Database backup created at %s", backup_path)
        return True
    except IOError as e:
        logger.error("Failed to create database backup: %s", e)
        return False
    except Exception as e:
        logger.critical("An unexpected error occurred during backup: %s", e)
        return False
