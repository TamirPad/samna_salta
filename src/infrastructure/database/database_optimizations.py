"""
Database optimizations for improved performance and scalability
"""

import logging
import time
from contextlib import contextmanager
from typing import Any, Dict, Optional

from sqlalchemy import Index, create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

from ..configuration.config import get_config
from .models import Base, Cart, Customer, Order, OrderItem, Product

logger = logging.getLogger(__name__)


class DatabaseConnectionManager:
    """
    Optimized database connection manager with connection pooling
    and performance monitoring
    """

    def __init__(self):
        self._engine: Optional[Engine] = None
        self._SessionLocal = None
        self._setup_engine()
        self._setup_indexes()
        self._setup_performance_monitoring()

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
            if config.database_url.startswith("postgresql"):
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

        self._SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self._engine
        )

        logger.info(f"Database engine configured for {config.environment}")

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

        except Exception as e:
            logger.warning(f"Error setting up indexes: {e}")

    def _setup_performance_monitoring(self):
        """Setup performance monitoring for database operations"""

        @event.listens_for(Engine, "before_cursor_execute")
        def receive_before_cursor_execute(
            conn, cursor, statement, parameters, context, executemany
        ):
            context._query_start_time = time.time()

        @event.listens_for(Engine, "after_cursor_execute")
        def receive_after_cursor_execute(
            conn, cursor, statement, parameters, context, executemany
        ):
            total = time.time() - context._query_start_time

            # Log slow queries (> 100ms)
            if total > 0.1:
                logger.warning(
                    f"Slow query detected: {total:.3f}s - {statement[:100]}..."
                )

            # Log all queries in debug mode
            logger.debug(f"Query executed in {total:.3f}s: {statement[:50]}...")

    @property
    def engine(self) -> Engine:
        """Get database engine"""
        return self._engine

    @contextmanager
    def get_session(self):
        """Get database session with automatic cleanup"""
        session = self._SessionLocal()
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


# Global database manager instance
_db_manager: Optional[DatabaseConnectionManager] = None


def get_database_manager() -> DatabaseConnectionManager:
    """Get the global database manager instance"""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseConnectionManager()
    return _db_manager


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

            # Get table counts
            customer_count = session.query(Customer).count()
            product_count = session.query(Product).count()
            order_count = session.query(Order).count()

            # Get connection pool info
            pool_info = db_manager.get_connection_info()

            return {
                "status": "healthy",
                "tables": {
                    "customers": customer_count,
                    "products": product_count,
                    "orders": order_count,
                },
                "connection_pool": pool_info,
                "timestamp": time.time(),
            }

    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": time.time(),
        }


# Migration utilities
def run_database_migrations():
    """Run database migrations and optimizations"""
    logger.info("Running database migrations...")

    db_manager = get_database_manager()

    try:
        # Create tables
        db_manager.create_all_tables()

        # Apply indexes
        with db_manager.get_session() as session:
            # Add any custom migrations here
            pass

        logger.info("Database migrations completed successfully")

    except Exception as e:
        logger.error(f"Database migration failed: {e}")
        raise


# Backup utilities
def create_database_backup(backup_path: str) -> bool:
    """Create database backup (SQLite only)"""
    config = get_config()

    if not config.database_url.startswith("sqlite"):
        logger.warning("Backup only supported for SQLite databases")
        return False

    try:
        import shutil
        import sqlite3

        # Extract database path from URL
        db_path = config.database_url.replace("sqlite:///", "")

        # Create backup
        shutil.copy2(db_path, backup_path)

        logger.info(f"Database backup created: {backup_path}")
        return True

    except Exception as e:
        logger.error(f"Database backup failed: {e}")
        return False
