"""
Shared pytest configuration and fixtures for the Samna Salta test suite.
"""

import asyncio
import os
import tempfile
from pathlib import Path
from typing import Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.config import get_config
from src.container import Container, initialize_container
from src.db.models import Base
from src.db.operations import DatabaseManager


# ============================================================================
# Pytest Configuration
# ============================================================================

def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "e2e: mark test as an end-to-end test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )


# ============================================================================
# Database Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def test_database_url() -> str:
    """Provide test database URL"""
    return "sqlite:///:memory:"


@pytest.fixture(scope="session")
def test_engine(test_database_url):
    """Create test database engine"""
    engine = create_engine(test_database_url, echo=False)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def test_session(test_engine):
    """Create test database session"""
    Session = sessionmaker(bind=test_engine)
    session = Session()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def db_manager(test_database_url):
    """Provide test database manager"""
    # Override config for testing
    original_config = get_config()
    original_config.database_url = test_database_url
    
    manager = DatabaseManager(original_config)
    yield manager
    manager.close()


# ============================================================================
# Container Fixtures
# ============================================================================

@pytest.fixture
def container() -> Container:
    """Provide test container"""
    return Container()


@pytest.fixture
def mock_bot():
    """Provide mock bot for testing"""
    bot = MagicMock()
    bot.send_message = AsyncMock()
    bot.edit_message_text = AsyncMock()
    bot.answer_callback_query = AsyncMock()
    return bot


@pytest.fixture
def initialized_container(mock_bot) -> Container:
    """Provide initialized container with mock bot"""
    container = Container()
    initialize_container(mock_bot)
    return container


# ============================================================================
# Service Fixtures
# ============================================================================

@pytest.fixture
def cart_service(container):
    """Provide cart service"""
    return container.get_cart_service()


@pytest.fixture
def order_service(container):
    """Provide order service"""
    return container.get_order_service()


@pytest.fixture
def notification_service(container):
    """Provide notification service"""
    return container.get_notification_service()


# ============================================================================
# Test Data Fixtures
# ============================================================================

@pytest.fixture
def sample_customer_data():
    """Provide sample customer data"""
    return {
        "telegram_id": 123456789,
        "full_name": "Ahmed Al-Yemeni",
        "phone_number": "+972501234567",
        "delivery_address": "Tel Aviv, Israel"
    }


@pytest.fixture
def sample_product_data():
    """Provide sample product data"""
    return {
        "name": "Kubaneh",
        "description": "Traditional sweet bread",
        "category": "bread",
        "price": 25.0,
        "is_active": True
    }


@pytest.fixture
def sample_order_data():
    """Provide sample order data"""
    return {
        "customer_id": 1,
        "total_amount": 50.0,
        "delivery_method": "pickup",
        "delivery_address": None,
        "status": "pending"
    }


# ============================================================================
# Mock Fixtures
# ============================================================================

@pytest.fixture
def mock_telegram_update():
    """Provide mock Telegram update"""
    update = MagicMock()
    update.effective_user.id = 123456789
    update.effective_user.first_name = "Ahmed"
    update.effective_user.last_name = "Al-Yemeni"
    update.message = MagicMock()
    update.callback_query = None
    return update


@pytest.fixture
def mock_telegram_context():
    """Provide mock Telegram context"""
    context = MagicMock()
    context.user_data = {}
    context.bot_data = {}
    return context


@pytest.fixture
def mock_callback_query():
    """Provide mock callback query"""
    query = MagicMock()
    query.data = "test_callback"
    query.from_user.id = 123456789
    return query


# ============================================================================
# Async Fixtures
# ============================================================================

@pytest.fixture
def event_loop():
    """Provide event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Utility Fixtures
# ============================================================================

@pytest.fixture
def temp_file():
    """Provide temporary file"""
    with tempfile.NamedTemporaryFile(delete=False) as f:
        yield f.name
    os.unlink(f.name)


@pytest.fixture
def temp_dir():
    """Provide temporary directory"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


# ============================================================================
# Configuration Fixtures
# ============================================================================

@pytest.fixture
def test_config():
    """Provide test configuration"""
    config = get_config()
    config.environment = "test"
    config.log_level = "ERROR"  # Reduce log noise in tests
    return config


# ============================================================================
# Cleanup Fixtures
# ============================================================================

@pytest.fixture(autouse=True)
def cleanup_after_test():
    """Cleanup after each test"""
    yield
    # Reset any global state if needed
    Container._instance = None
    Container._bot = None


# ============================================================================
# Custom Assertions
# ============================================================================

class CustomAssertions:
    """Custom assertion methods for tests"""
    
    @staticmethod
    def assert_price_format(price_str: str):
        """Assert price is properly formatted"""
        assert isinstance(price_str, str)
        assert "ILS" in price_str
        assert any(c.isdigit() for c in price_str)
    
    @staticmethod
    def assert_phone_format(phone: str):
        """Assert phone number is properly formatted"""
        assert phone.startswith("+972")
        assert len(phone) == 13
        assert phone[4:].isdigit()


@pytest.fixture
def assert_custom():
    """Provide custom assertions"""
    return CustomAssertions() 