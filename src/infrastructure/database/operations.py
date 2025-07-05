"""
Database operations with retry logic and connection management

Enhanced with proper type annotations and constant usage for better maintainability.
"""

import logging
import sqlite3
import time
from datetime import datetime
from typing import Optional, Any, Dict, List, Union, Callable
from functools import wraps

from sqlalchemy import create_engine, Engine, event, text
from sqlalchemy.exc import SQLAlchemyError, OperationalError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.pool import StaticPool

from src.infrastructure.configuration.config import get_config
from src.infrastructure.database.models import (
    Base,
    Cart,
    Customer,
    Order,
    OrderItem,
    Product,
)
from src.infrastructure.utilities.constants import (
    DatabaseSettings,
    RetrySettings,
    ErrorCodes,
    PerformanceSettings
)
from src.infrastructure.utilities.exceptions import (
    DatabaseOperationError,
    DatabaseConnectionError,
    DatabaseTimeoutError,
    DatabaseRetryExhaustedError,
)
from src.infrastructure.logging.logging_config import PerformanceLogger

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Enhanced database manager with retry logic and performance monitoring"""

    def __init__(self, config: Optional[Any] = None):
        """Initialize database manager with configuration"""
        self.config = config or get_config()
        self._engine: Optional[Engine] = None
        self._session_factory: Optional[sessionmaker] = None
        self.logger = logging.getLogger(__name__)

    def get_engine(self) -> Engine:
        """Get database engine with proper configuration"""
        if self._engine is None:
            self._engine = self._create_engine()
        return self._engine

    def _create_engine(self) -> Engine:
        """Create database engine with environment-specific settings"""
        database_url = self.config.database_url
        
        # Configure engine parameters based on environment
        if self.config.environment == "production":
            pool_size = DatabaseSettings.PRODUCTION_POOL_SIZE
            max_overflow = DatabaseSettings.PRODUCTION_MAX_OVERFLOW
        else:
            pool_size = DatabaseSettings.DEVELOPMENT_POOL_SIZE
            max_overflow = DatabaseSettings.DEVELOPMENT_MAX_OVERFLOW

        # Engine configuration
        engine_kwargs = {
            "pool_size": pool_size,
            "max_overflow": max_overflow,
            "pool_recycle": DatabaseSettings.POOL_RECYCLE_SECONDS,
            "pool_pre_ping": True,
            "echo": self.config.environment == "development",
        }

        # SQLite-specific configurations
        if database_url.startswith("sqlite"):
            engine_kwargs.update({
                "poolclass": StaticPool,
                "connect_args": {
                    "check_same_thread": False,
                    "timeout": RetrySettings.CONNECTION_TIMEOUT_SECONDS
                },
            })

        engine = create_engine(database_url, **engine_kwargs)

        # Add performance monitoring
        self._setup_engine_events(engine)

        return engine

    def _setup_engine_events(self, engine: Engine) -> None:
        """Setup SQLAlchemy events for performance monitoring"""
        
        @event.listens_for(engine, "before_cursor_execute")
        def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            context._query_start_time = time.time()

        @event.listens_for(engine, "after_cursor_execute")
        def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            total_time = time.time() - context._query_start_time
            total_time_ms = total_time * 1000
            
            if total_time_ms > PerformanceSettings.SLOW_QUERY_THRESHOLD_MS:
                self.logger.warning(
                    "Slow query detected",
                    extra={
                        "query_time_ms": total_time_ms,
                        "statement": statement[:200] + "..." if len(statement) > 200 else statement,
                        "parameters": str(parameters)[:100] if parameters else None,
                    }
                )

    def get_session_factory(self) -> sessionmaker:
        """Get session factory"""
        if self._session_factory is None:
            self._session_factory = sessionmaker(
                bind=self.get_engine(),
                expire_on_commit=False
            )
        return self._session_factory

    def get_session(self) -> Session:
        """Get database session"""
        return self.get_session_factory()()

    def create_tables(self) -> None:
        """Create all database tables"""
        try:
            with PerformanceLogger("create_tables", self.logger):
                Base.metadata.create_all(self.get_engine())
                self.logger.info("Database tables created successfully")
        except SQLAlchemyError as e:
            self.logger.error(f"Failed to create database tables: {e}", exc_info=True)
            raise DatabaseOperationError(
                f"Failed to create database tables: {e}",
                ErrorCodes.DATABASE_ERROR
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
                f"Failed to drop database tables: {e}",
                ErrorCodes.DATABASE_ERROR
            ) from e

    def execute_with_retry(
        self,
        operation: Callable[..., Any],
        *args,
        **kwargs
    ) -> Any:
        """Execute database operation with retry logic"""
        last_exception: Optional[Exception] = None
        
        for attempt in range(RetrySettings.MAX_RETRIES):
            try:
                with PerformanceLogger(f"db_operation_attempt_{attempt + 1}", self.logger):
                    return operation(*args, **kwargs)
            except OperationalError as e:
                last_exception = e
                if attempt < RetrySettings.MAX_RETRIES - 1:
                    self.logger.warning(
                        f"Database operation failed (attempt {attempt + 1}/{RetrySettings.MAX_RETRIES}): {e}",
                        extra={"attempt": attempt + 1, "operation": operation.__name__}
                    )
                    time.sleep(RetrySettings.RETRY_DELAY_SECONDS)
                else:
                    self.logger.error(
                        f"Database operation failed after {RetrySettings.MAX_RETRIES} attempts: {e}",
                        extra={"operation": operation.__name__},
                        exc_info=True
                    )
            except SQLAlchemyError as e:
                last_exception = e
                self.logger.error(
                    f"Database operation failed with non-retryable error: {e}",
                    extra={"operation": operation.__name__},
                    exc_info=True
                )
                break

        # If we get here, all retries failed
        if isinstance(last_exception, OperationalError):
            raise DatabaseRetryExhaustedError(
                f"Database operation failed after {RetrySettings.MAX_RETRIES} attempts: {last_exception}",
                ErrorCodes.DATABASE_ERROR
            ) from last_exception
        else:
            raise DatabaseOperationError(
                f"Database operation failed: {last_exception}",
                ErrorCodes.DATABASE_ERROR
            ) from last_exception

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
    delay: int = RetrySettings.RETRY_DELAY_SECONDS
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
                            extra={"attempt": attempt + 1, "function": func.__name__}
                        )
                        time.sleep(delay)
                    else:
                        logger.error(
                            f"Database operation {func.__name__} failed after {max_retries} attempts: {e}",
                            extra={"function": func.__name__},
                            exc_info=True
                        )
                except SQLAlchemyError as e:
                    last_exception = e
                    logger.error(
                        f"Database operation {func.__name__} failed with non-retryable error: {e}",
                        extra={"function": func.__name__},
                        exc_info=True
                    )
                    break
            
            # All retries failed
            if isinstance(last_exception, (OperationalError, DatabaseConnectionError)):
                raise DatabaseRetryExhaustedError(
                    f"Database operation {func.__name__} failed after {max_retries} attempts: {last_exception}",
                    ErrorCodes.DATABASE_ERROR
                ) from last_exception
            else:
                raise DatabaseOperationError(
                    f"Database operation {func.__name__} failed: {last_exception}",
                    ErrorCodes.DATABASE_ERROR
                ) from last_exception
        
        return wrapper
    return decorator


def init_db():
    """Initialize database tables"""
    try:
        engine = get_db_manager().get_engine()
        get_db_manager().create_tables()
        logger.info("Database tables created successfully")

        # Initialize default products
        init_default_products()

    except SQLAlchemyError as e:
        logger.error("Failed to initialize database: %s", e)
        raise


def init_default_products():
    """Initialize default products in the database"""
    session = get_db_session()
    try:
        # Check if products already exist
        if session.query(Product).count() > 0:
            logger.info("Products already exist, skipping initialization")
            return

        # Default products configuration
        products = [
            {
                "name": "Kubaneh",
                "category": "bread",
                "description": "Traditional Yemenite bread",
                "base_price": 25.00,
                "options": {
                    "type": ["Classic", "Seeded", "Herb", "Aromatic"],
                    "oil": ["Olive oil", "Samneh"],
                },
            },
            {
                "name": "Samneh",
                "category": "spread",
                "description": "Traditional clarified butter",
                "base_price": 15.00,
                "options": {
                    "smoking": ["Smoked", "Not smoked"],
                    "size": ["Small", "Large"],
                },
            },
            {
                "name": "Red Bisbas",
                "category": "spice",
                "description": "Traditional Yemenite spice blend",
                "base_price": 12.00,
                "options": {"size": ["Small", "Large"]},
            },
            {
                "name": "Hawaij soup spice",
                "category": "spice",
                "description": "Traditional soup spice blend",
                "base_price": 8.00,
                "options": {},
            },
            {
                "name": "Hawaij coffee spice",
                "category": "spice",
                "description": "Traditional coffee spice blend",
                "base_price": 8.00,
                "options": {},
            },
            {
                "name": "White coffee",
                "category": "beverage",
                "description": "Traditional Yemenite white coffee",
                "base_price": 10.00,
                "options": {},
            },
            {
                "name": "Hilbeh",
                "category": "spread",
                "description": "Traditional fenugreek spread (available Wed-Fri only)",
                "base_price": 18.00,
                "options": {},
            },
        ]

        for product_data in products:
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
def get_or_create_customer(
    telegram_id: int, full_name: str, phone_number: str
) -> Customer:
    """Get existing customer or create new one"""
    session = get_db_session()
    try:
        customer = (
            session.query(Customer)
            .filter(Customer.phone_number == phone_number)
            .first()
        )

        if customer:
            # Update telegram_id if it changed
            if customer.telegram_id != telegram_id:
                customer.telegram_id = telegram_id
                customer.updated_at = datetime.utcnow()
                session.commit()
            return customer

        # Create new customer
        customer = Customer(
            telegram_id=telegram_id, full_name=full_name, phone_number=phone_number
        )
        session.add(customer)
        session.commit()
        session.refresh(customer)
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
def get_all_products() -> list[Product]:
    """Get all active products"""
    session = get_db_session()
    try:
        return session.query(Product).filter(Product.is_active).all()
    finally:
        session.close()


def get_product_by_name(name: str) -> Product | None:
    """Get product by name"""
    session = get_db_session()
    try:
        return session.query(Product).filter(Product.name == name).first()
    finally:
        session.close()


def get_product_by_id(product_id: int) -> Product | None:
    """Get product by ID"""
    session = get_db_session()
    try:
        return session.query(Product).filter(Product.id == product_id).first()
    finally:
        session.close()


# Cart operations
def get_or_create_cart(telegram_id: int) -> Cart:
    """Get existing cart or create new one"""
    session = get_db_session()
    try:
        cart = session.query(Cart).filter(Cart.telegram_id == telegram_id).first()

        if not cart:
            cart = Cart(telegram_id=telegram_id, items=[])
            session.add(cart)
            session.commit()
            session.refresh(cart)

        return cart

    except SQLAlchemyError as e:
        session.rollback()
        logger.error("Failed to get/create cart: %s", e)
        raise
    finally:
        session.close()


def add_to_cart(
    telegram_id: int, product_id: int, quantity: int = 1, options: dict | None = None
) -> bool:
    """Add item to cart or update quantity if it exists"""
    session = get_db_session()
    try:
        cart = get_or_create_cart(telegram_id)
        product = get_product_by_id(product_id)

        if not product:
            logger.warning("Product with ID %d not found", product_id)
            return False

        # Create a unique key for the item based on product_id and options
        options_key = tuple(sorted(options.items())) if options else ()

        # Check if item with the same product_id and options already exists
        existing_item = next(
            (
                item
                for item in cart.items
                if item.get("product_id") == product_id
                and tuple(sorted(item.get("options", {}).items())) == options_key
            ),
            None,
        )

        if existing_item:
            # Update quantity if item exists
            existing_item["quantity"] += quantity
        else:
            # Add new item to cart
            new_item = {
                "product_id": product_id,
                "quantity": quantity,
                "options": options,
                "price": product.base_price,  # Store price at time of adding
            }
            cart.items.append(new_item)

        # Mark 'items' field as modified for JSON mutation tracking
        flag_modified(cart, "items")

        session.commit()
        return True

    except SQLAlchemyError as e:
        session.rollback()
        logger.error("Failed to add to cart: %s", e)
        return False
    finally:
        session.close()


def get_cart_items(telegram_id: int) -> list[dict]:
    """Get cart items for user"""
    session = get_db_session()
    try:
        cart = session.query(Cart).filter(Cart.telegram_id == telegram_id).first()
        if cart and cart.items:
            # Convert to cart item objects for compatibility
            cart_items = []
            for item in cart.items:
                cart_item = type(
                    "CartItem",
                    (),
                    {"product_id": item["product_id"], "quantity": item["quantity"]},
                )()
                cart_items.append(cart_item)
            return cart_items
        return []
    finally:
        session.close()


def update_cart(
    telegram_id: int,
    items: list[dict],
    delivery_method: str | None = None,
    delivery_address: str | None = None,
) -> bool:
    """Update cart with new items and delivery info"""
    session = get_db_session()
    try:
        cart = get_or_create_cart(telegram_id)

        # Update cart items
        cart.items = items

        # Update delivery info
        if delivery_method:
            cart.delivery_method = delivery_method
        if delivery_address:
            cart.delivery_address = delivery_address

        # Mark 'items' field as modified for JSON mutation tracking
        flag_modified(cart, "items")

        session.commit()
        return True

    except SQLAlchemyError as e:
        session.rollback()
        logger.error("Failed to update cart: %s", e)
        return False
    finally:
        session.close()


def clear_cart(telegram_id: int) -> bool:
    """Clear all items from a cart"""
    session = get_db_session()
    try:
        cart = session.query(Cart).filter(Cart.telegram_id == telegram_id).first()
        if cart:
            session.delete(cart)
            session.commit()
        return True
    except SQLAlchemyError as e:
        session.rollback()
        logger.error("Failed to clear cart: %s", e)
        return False
    finally:
        session.close()


def remove_from_cart(telegram_id: int, product_id: int) -> bool:
    """Remove item from cart"""
    session = get_db_session()
    try:
        cart = session.query(Cart).filter(Cart.telegram_id == telegram_id).first()
        if not cart:
            return False

        # Find and remove item from cart
        cart.items = [
            item for item in cart.items if item.get("product_id") != product_id
        ]

        # Mark 'items' field as modified for JSON mutation tracking
        flag_modified(cart, "items")

        session.commit()
        return True

    except SQLAlchemyError as e:
        session.rollback()
        logger.error("Failed to remove from cart: %s", e)
        raise
    finally:
        session.close()


# Order operations
def create_order(
    customer_id: int,
    total_amount: float,
    delivery_method: str = "pickup",
    delivery_address: str | None = None,
) -> Order | None:
    """Create new order with items"""
    session = get_db_session()
    try:
        # Generate order number
        order_number = generate_order_number()

        # Calculate delivery charge
        delivery_charge = 5.0 if delivery_method == "delivery" else 0.0
        subtotal = total_amount - delivery_charge

        # Create order
        order = Order(
            customer_id=customer_id,
            order_number=order_number,
            delivery_method=delivery_method,
            delivery_address=delivery_address,
            delivery_charge=delivery_charge,
            subtotal=subtotal,
            total=total_amount,
        )
        session.add(order)
        session.flush()  # Get the order ID

        # Get customer's cart to create order items
        customer = session.query(Customer).filter(Customer.id == customer_id).first()
        if customer:
            cart = (
                session.query(Cart)
                .filter(Cart.telegram_id == customer.telegram_id)
                .first()
            )
            if cart and cart.items:
                for item_data in cart.items:
                    order_item = OrderItem(
                        order_id=order.id,
                        product_name=item_data["product_name"],
                        product_options=item_data.get("options"),
                        quantity=item_data["quantity"],
                        unit_price=item_data["unit_price"],
                        total_price=item_data["unit_price"] * item_data["quantity"],
                    )
                    session.add(order_item)

        session.commit()
        session.refresh(order)
        return order

    except SQLAlchemyError as e:
        session.rollback()
        logger.error("Failed to create order: %s", e)
        return None
    finally:
        session.close()


def generate_order_number() -> str:
    """Generate unique order number"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"SS{timestamp}"


def get_all_customers() -> list[Customer]:
    """Get all customers"""
    session = get_db_session()
    try:
        return session.query(Customer).all()
    finally:
        session.close()


def get_all_orders() -> list[Order]:
    """Get all orders"""
    session = get_db_session()
    try:
        return session.query(Order).order_by(Order.created_at.desc()).all()
    finally:
        session.close()
