"""
Test configuration and fixtures for the Samna Salta bot
"""

import os
import pytest
import asyncio
from unittest.mock import patch, MagicMock
from typing import Generator, Dict, Any
from telegram import Update, User

# Mock environment variables for testing
@pytest.fixture(autouse=True)
def mock_env():
    """Mock environment variables for testing"""
    test_env = {
        'BOT_TOKEN': 'test_bot_token_123456789',
        'DATABASE_URL': 'sqlite:///test.db',
        'ADMIN_CHAT_ID': '123456789',
        'ENVIRONMENT': 'test',
        'LOG_LEVEL': 'DEBUG',
        'WEBHOOK_URL': 'https://test.example.com/webhook',
        'PORT': '8000'
    }
    
    with patch.dict(os.environ, test_env, clear=True):
        yield test_env


@pytest.fixture
def patch_config():
    """Patch configuration for testing"""
    with patch('src.config.get_config') as mock_get_config:
        mock_config = MagicMock()
        mock_config.bot_token = 'test_bot_token_123456789_very_long_string_for_validation'
        mock_config.database_url = 'sqlite:///test.db'
        mock_config.admin_chat_id = 123456789
        mock_config.environment = 'test'
        mock_config.log_level = 'DEBUG'
        mock_config.webhook_url = 'https://test.example.com/webhook'
        mock_config.port = 8000
        mock_config.delivery_charge = 5.0
        mock_config.currency = 'ILS'
        mock_config.supabase_connection_string = None
        mock_get_config.return_value = mock_config
        yield mock_config


@pytest.fixture
def mock_telegram():
    """Mock Telegram objects for testing"""
    with patch('telegram.Update') as mock_update, \
         patch('telegram.CallbackQuery') as mock_callback_query, \
         patch('telegram.Message') as mock_message, \
         patch('telegram.User') as mock_user, \
         patch('telegram.Chat') as mock_chat:
        
        # Setup mock user
        mock_user_instance = MagicMock()
        mock_user_instance.id = 123456789
        mock_user_instance.first_name = "Test"
        mock_user_instance.last_name = "User"
        mock_user_instance.username = "testuser"
        mock_user.return_value = mock_user_instance
        
        # Setup mock chat
        mock_chat_instance = MagicMock()
        mock_chat_instance.id = 123456789
        mock_chat_instance.type = "private"
        mock_chat.return_value = mock_chat_instance
        
        # Setup mock message
        mock_message_instance = MagicMock()
        mock_message_instance.chat = mock_chat_instance
        mock_message_instance.from_user = mock_user_instance
        mock_message_instance.text = "test message"
        mock_message.return_value = mock_message_instance
        
        # Setup mock callback query
        mock_callback_instance = MagicMock()
        mock_callback_instance.from_user = mock_user_instance
        mock_callback_instance.data = "test_callback"
        mock_callback_instance.message = mock_message_instance
        mock_callback_query.return_value = mock_callback_instance
        
        # Setup mock update
        mock_update_instance = MagicMock()
        mock_update_instance.callback_query = mock_callback_instance
        mock_update_instance.message = mock_message_instance
        mock_update_instance.effective_user = mock_user_instance
        mock_update_instance.effective_chat = mock_chat_instance
        mock_update.return_value = mock_update_instance
        
        yield {
            'update': mock_update_instance,
            'callback_query': mock_callback_instance,
            'message': mock_message_instance,
            'user': mock_user_instance,
            'chat': mock_chat_instance
        }


@pytest.fixture
def mock_update_with_user():
    """Create mock update with user"""
    update = MagicMock(spec=Update)
    update.effective_user = MagicMock(spec=User)
    update.effective_user.id = 123456789
    update.effective_user.username = "testuser"
    return update


@pytest.fixture
def mock_update():
    """Create mock update"""
    update = MagicMock(spec=Update)
    update.effective_user = MagicMock(spec=User)
    update.effective_user.id = 123456789
    update.effective_user.username = "testuser"
    return update


@pytest.fixture
def mock_context():
    """Mock context for testing"""
    with patch('telegram.ext.ContextTypes.DEFAULT_TYPE') as mock_context_class:
        mock_context_instance = MagicMock()
        mock_context_instance.user_data = {}
        mock_context_instance.bot_data = {}
        mock_context_instance.chat_data = {}
        mock_context_class.return_value = mock_context_instance
        yield mock_context_instance


@pytest.fixture
def db_session():
    """Create a test database session"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from src.db.models import Base
    
    # Create in-memory SQLite database for testing
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


@pytest.fixture
def sample_customer():
    """Create a sample customer for testing."""
    from src.db.models import Customer
    
    return Customer(
        id=1,
        telegram_id=123456789,
        name="Test Customer",
        phone="+972501234567",
        language="en",
        is_admin=False,
        delivery_address="123 Test St, Test City"
    )


@pytest.fixture
def sample_products():
    """Create sample products for testing."""
    from src.db.models import Product, MenuCategory
    
    # First create categories
    bread_category = MenuCategory(
        id=1,
        name="bread",
        description="Traditional breads",
        display_order=1,
        is_active=True
    )
    
    spread_category = MenuCategory(
        id=2,
        name="spread",
        description="Spreads and condiments",
        display_order=2,
        is_active=True
    )
    
    spice_category = MenuCategory(
        id=3,
        name="spice",
        description="Spices and seasonings",
        display_order=3,
        is_active=True
    )
    
    return [
        Product(
            id=1,
            name="Kubaneh",
            description="Traditional Yemenite bread",
            category_id=1,
            price=25.00,
            is_active=True,
            preparation_time_minutes=15
        ),
        Product(
            id=2,
            name="Hilbeh",
            description="Fenugreek spread",
            category_id=2,
            price=15.00,
            is_active=True,
            preparation_time_minutes=10
        ),
        Product(
            id=3,
            name="Za'atar",
            description="Herb and spice blend",
            category_id=3,
            price=12.00,
            is_active=True,
            preparation_time_minutes=5
        )
    ]


@pytest.fixture
def sample_cart(sample_customer):
    """Create a sample cart for testing."""
    from src.db.models import Cart
    
    return Cart(
        id=1,
        customer_id=sample_customer.id,
        delivery_method="pickup",
        delivery_address=None
    )


@pytest.fixture
def sample_cart_items(sample_cart, sample_products):
    """Create sample cart items for testing."""
    from src.db.models import CartItem
    
    return [
        CartItem(
            id=1,
            cart_id=sample_cart.id,
            product_id=sample_products[0].id,
            quantity=2,
            unit_price=sample_products[0].price,
            product_options={"type": "classic"}
        ),
        CartItem(
            id=2,
            cart_id=sample_cart.id,
            product_id=sample_products[1].id,
            quantity=1,
            unit_price=sample_products[1].price,
            product_options={"type": "smoked"}
        )
    ]


@pytest.fixture
def sample_order(sample_customer):
    """Create a sample order for testing."""
    from src.db.models import Order
    
    return Order(
        id=1,
        customer_id=sample_customer.id,
        order_number="ORD-000001",
        status="pending",
        total=52.00,
        delivery_method="pickup",
        delivery_address=None
    )


@pytest.fixture
def sample_order_items(sample_order, sample_products):
    """Create sample order items for testing."""
    from src.db.models import OrderItem
    
    return [
        OrderItem(
            id=1,
            order_id=sample_order.id,
            product_id=sample_products[0].id,
            product_name=sample_products[0].name,
            quantity=2,
            unit_price=sample_products[0].price,
            total_price=50.00,
            product_options={"type": "classic"}
        ),
        OrderItem(
            id=2,
            order_id=sample_order.id,
            product_id=sample_products[1].id,
            product_name=sample_products[1].name,
            quantity=1,
            unit_price=sample_products[1].price,
            total_price=15.00,
            product_options={"type": "smoked"}
        )
    ]


@pytest.fixture
def mock_container():
    """Mock dependency injection container"""
    with patch('src.container.get_container') as mock_get_container:
        mock_container_instance = MagicMock()
        
        # Mock services
        mock_cart_service = MagicMock()
        mock_order_service = MagicMock()
        mock_admin_service = MagicMock()
        mock_notification_service = MagicMock()
        
        mock_container_instance.get_cart_service.return_value = mock_cart_service
        mock_container_instance.get_order_service.return_value = mock_order_service
        mock_container_instance.get_admin_service.return_value = mock_admin_service
        mock_container_instance.get_notification_service.return_value = mock_notification_service
        
        mock_get_container.return_value = mock_container_instance
        
        yield {
            'container': mock_container_instance,
            'cart_service': mock_cart_service,
            'order_service': mock_order_service,
            'admin_service': mock_admin_service,
            'notification_service': mock_notification_service
        }


@pytest.fixture
def mock_i18n():
    """Mock internationalization"""
    with patch('src.utils.i18n.i18n') as mock_i18n_instance:
        mock_i18n_instance.get_text.return_value = "Test text"
        yield mock_i18n_instance


@pytest.fixture
def patch_i18n():
    """Patch i18n for testing"""
    with patch('src.utils.i18n.i18n') as mock_i18n_instance:
        mock_i18n_instance.get_text.return_value = "Test text"
        yield mock_i18n_instance


@pytest.fixture
def mock_language_manager():
    """Mock language manager"""
    with patch('src.utils.language_manager.language_manager') as mock_lm:
        mock_lm.get_user_language.return_value = "en"
        mock_lm.set_user_language.return_value = True
        yield mock_lm


@pytest.fixture
def mock_db_operations():
    """Mock database operations"""
    with patch('src.db.operations') as mock_ops:
        # Mock customer operations
        mock_ops.get_or_create_customer.return_value = MagicMock(id=1, telegram_id=123456789)
        mock_ops.get_customer_by_telegram_id.return_value = MagicMock(id=1, telegram_id=123456789, language="en")
        mock_ops.update_customer_language.return_value = True
        
        # Mock product operations
        mock_ops.get_all_products.return_value = []
        mock_ops.get_product_by_id.return_value = None
        mock_ops.create_product.return_value = MagicMock(id=1)
        mock_ops.update_product.return_value = True
        mock_ops.delete_product.return_value = True
        
        # Mock cart operations
        mock_ops.add_to_cart.return_value = True
        mock_ops.get_cart_items.return_value = []
        mock_ops.clear_cart.return_value = True
        mock_ops.remove_from_cart.return_value = True
        
        # Mock order operations
        mock_ops.create_order.return_value = MagicMock(id=1, order_number="ORD-000001")
        mock_ops.update_order_status.return_value = True
        mock_ops.get_all_orders.return_value = []
        mock_ops.get_all_customers.return_value = []
        
        # Mock database connection
        mock_ops.check_database_connection.return_value = True
        
        yield mock_ops


@pytest.fixture
def mock_application():
    """Mock Telegram application"""
    with patch('telegram.ext.Application') as mock_app_class:
        mock_app_instance = MagicMock()
        mock_app_instance.add_handler = MagicMock()
        mock_app_instance.run_polling = MagicMock()
        mock_app_instance.run_webhook = MagicMock()
        mock_app_class.return_value = mock_app_instance
        yield mock_app_instance


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close() 


@pytest.fixture
def sample_admin_customer():
    """Create a sample admin customer for testing."""
    from src.db.models import Customer
    
    return Customer(
        id=2,
        telegram_id=987654321,
        name="Admin User",
        phone="+972509876543",
        language="en",
        is_admin=True,
        delivery_address="456 Admin St, Admin City"
    )


@pytest.fixture
def performance_timer():
    """Timer for performance testing."""
    import time
    start_time = time.time()
    yield
    end_time = time.time()
    print(f"Test execution time: {end_time - start_time:.4f} seconds") 


@pytest.fixture
def sample_product_data():
    """Sample product data for testing."""
    return {
        "name": "Test Product",
        "description": "Test Description",
        "category": "Bread",  # Changed from category_id to category
        "price": 10.00
        # Removed is_active and preparation_time_minutes as they're not accepted by create_product
    } 


@pytest.fixture
def patch_container():
    """Patch container for testing"""
    with patch('src.container.get_container') as mock_get_container:
        mock_container = MagicMock()
        mock_get_container.return_value = mock_container
        yield mock_container 