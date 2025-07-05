"""
Tests for Infrastructure Components - Dependency Injection, Health Checks, Config Validator, etc.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import tempfile
import os
from pathlib import Path

from src.infrastructure.container.dependency_injection import DependencyContainer, get_container, initialize_container, reset_container

# Import only modules that are available
try:
    from src.infrastructure.deployment.health_checks import HealthCheckService, SystemHealthChecker, DatabaseHealthChecker, ServiceHealthChecker
    HEALTH_CHECKS_AVAILABLE = True
except ImportError:
    HEALTH_CHECKS_AVAILABLE = False

try:
    from src.infrastructure.utilities.config_validator import ConfigValidator, validate_telegram_config, validate_database_config, validate_security_config
    CONFIG_VALIDATOR_AVAILABLE = True
except ImportError:
    CONFIG_VALIDATOR_AVAILABLE = False

try:
    from src.infrastructure.logging.logging_config import setup_logging, get_logger, configure_json_logging, configure_file_logging
    LOGGING_CONFIG_AVAILABLE = True
except ImportError:
    LOGGING_CONFIG_AVAILABLE = False

try:
    from src.infrastructure.utilities.security import SecurityUtils, hash_password, verify_password, generate_secure_token
    SECURITY_UTILS_AVAILABLE = True
except ImportError:
    SECURITY_UTILS_AVAILABLE = False


class TestDependencyContainer:
    """Test dependency injection container"""

    @pytest.fixture
    def mock_bot(self):
        """Create mock telegram bot"""
        bot = MagicMock()
        bot.token = "test_token"
        return bot

    def test_dependency_container_creation(self):
        """Test basic dependency container creation"""
        container = DependencyContainer()
        
        assert container is not None
        assert hasattr(container, '_instances')
        assert hasattr(container, '_logger')

    def test_dependency_container_with_bot(self, mock_bot):
        """Test dependency container creation with bot"""
        container = DependencyContainer(bot=mock_bot)
        
        assert container is not None
        assert container._bot == mock_bot

    def test_repository_registration(self):
        """Test repository registration"""
        container = DependencyContainer()
        
        customer_repo = container.get_customer_repository()
        product_repo = container.get_product_repository()
        cart_repo = container.get_cart_repository()
        order_repo = container.get_order_repository()
        
        assert customer_repo is not None
        assert product_repo is not None
        assert cart_repo is not None
        assert order_repo is not None

    def test_use_case_registration(self):
        """Test use case registration"""
        container = DependencyContainer()
        
        customer_use_case = container.get_customer_registration_use_case()
        product_use_case = container.get_product_catalog_use_case()
        cart_use_case = container.get_cart_management_use_case()
        order_use_case = container.get_order_creation_use_case()
        analytics_use_case = container.get_order_analytics_use_case()
        
        assert customer_use_case is not None
        assert product_use_case is not None
        assert cart_use_case is not None
        assert order_use_case is not None
        assert analytics_use_case is not None

    def test_service_registration_with_bot(self, mock_bot):
        """Test service registration with bot"""
        container = DependencyContainer(bot=mock_bot)
        
        admin_service = container.get_admin_notification_service()
        customer_service = container.get_customer_notification_service()
        
        assert admin_service is not None
        assert customer_service is not None

    def test_service_registration_without_bot(self):
        """Test service registration without bot"""
        container = DependencyContainer()
        
        admin_service = container.get_admin_notification_service()
        customer_service = container.get_customer_notification_service()
        
        assert admin_service is None
        assert customer_service is None

    def test_container_cleanup(self):
        """Test container cleanup"""
        container = DependencyContainer()
        container.cleanup()
        
        # Should not raise any errors
        assert True

    def test_get_container_singleton(self):
        """Test get_container singleton behavior"""
        reset_container()  # Clear any existing instance
        
        container1 = get_container()
        container2 = get_container()
        
        assert container1 is container2

    def test_initialize_container(self, mock_bot):
        """Test container initialization"""
        reset_container()
        
        container = initialize_container(bot=mock_bot)
        
        assert container is not None
        assert container._bot == mock_bot

    def test_reset_container(self):
        """Test container reset"""
        # Create a container first
        get_container()
        
        # Reset it
        reset_container()
        
        # Should get a new instance
        new_container = get_container()
        assert new_container is not None


@pytest.mark.skipif(not HEALTH_CHECKS_AVAILABLE, reason="Health checks module not available")
class TestHealthCheckService:
    """Test health check service"""

    @pytest.fixture
    def health_service(self):
        """Create health check service"""
        return HealthCheckService()

    @pytest.mark.asyncio
    async def test_health_check_creation(self, health_service):
        """Test health check service creation"""
        assert health_service is not None
        assert hasattr(health_service, 'checkers')

    @pytest.mark.asyncio
    async def test_add_checker(self, health_service):
        """Test adding health checker"""
        checker = MagicMock()
        checker.name = "test_checker"
        
        health_service.add_checker(checker)
        
        assert "test_checker" in health_service.checkers

    @pytest.mark.asyncio
    async def test_run_health_checks_empty(self, health_service):
        """Test running health checks with no checkers"""
        result = await health_service.run_all_checks()
        
        assert result is not None
        assert isinstance(result, dict)
        assert 'status' in result
        assert 'checks' in result

    @pytest.mark.asyncio
    async def test_run_health_checks_with_checkers(self, health_service):
        """Test running health checks with checkers"""
        # Mock checker
        checker = MagicMock()
        checker.name = "test_checker"
        checker.check = AsyncMock(return_value={
            "status": "healthy",
            "details": "All good"
        })
        
        health_service.add_checker(checker)
        
        result = await health_service.run_all_checks()
        
        assert result['status'] in ['healthy', 'unhealthy']
        assert 'test_checker' in result['checks']

    @pytest.mark.asyncio
    async def test_system_health_checker(self):
        """Test system health checker"""
        checker = SystemHealthChecker()
        
        result = await checker.check()
        
        assert isinstance(result, dict)
        assert 'status' in result
        assert 'details' in result

    @pytest.mark.asyncio
    async def test_database_health_checker(self):
        """Test database health checker"""
        with patch('src.infrastructure.deployment.health_checks.get_session') as mock_get_session:
            mock_session = MagicMock()
            mock_get_session.return_value = mock_session
            mock_session.execute.return_value = MagicMock()
            
            checker = DatabaseHealthChecker()
            result = await checker.check()
            
            assert isinstance(result, dict)
            assert 'status' in result

    @pytest.mark.asyncio
    async def test_service_health_checker(self):
        """Test service health checker"""
        checker = ServiceHealthChecker("test_service", "http://localhost:8080/health")
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={"status": "ok"})
            mock_get.return_value.__aenter__.return_value = mock_response
            
            result = await checker.check()
            
            assert isinstance(result, dict)
            assert 'status' in result


@pytest.mark.skipif(not CONFIG_VALIDATOR_AVAILABLE, reason="Config validator module not available")
class TestConfigValidator:
    """Test configuration validator"""

    def test_config_validator_creation(self):
        """Test config validator creation"""
        validator = ConfigValidator()
        
        assert validator is not None

    def test_validate_telegram_config_valid(self):
        """Test telegram config validation with valid config"""
        config = {
            "BOT_TOKEN": "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
            "WEBHOOK_URL": "https://example.com/webhook",
            "WEBHOOK_PORT": 8080
        }
        
        result = validate_telegram_config(config)
        
        assert result is True

    def test_validate_telegram_config_invalid_token(self):
        """Test telegram config validation with invalid token"""
        config = {
            "BOT_TOKEN": "invalid_token",
            "WEBHOOK_URL": "https://example.com/webhook"
        }
        
        result = validate_telegram_config(config)
        
        assert result is False

    def test_validate_telegram_config_missing_required(self):
        """Test telegram config validation with missing required fields"""
        config = {
            "WEBHOOK_URL": "https://example.com/webhook"
        }
        
        result = validate_telegram_config(config)
        
        assert result is False

    def test_validate_database_config_valid(self):
        """Test database config validation with valid config"""
        config = {
            "DATABASE_URL": "postgresql://user:pass@localhost:5432/db",
            "DB_POOL_SIZE": 10,
            "DB_POOL_MAX_OVERFLOW": 20
        }
        
        result = validate_database_config(config)
        
        assert result is True

    def test_validate_database_config_invalid_url(self):
        """Test database config validation with invalid URL"""
        config = {
            "DATABASE_URL": "invalid_url",
        }
        
        result = validate_database_config(config)
        
        assert result is False

    def test_validate_database_config_missing_url(self):
        """Test database config validation with missing URL"""
        config = {
            "DB_POOL_SIZE": 10
        }
        
        result = validate_database_config(config)
        
        assert result is False

    def test_validate_security_config_valid(self):
        """Test security config validation with valid config"""
        config = {
            "SECRET_KEY": "a" * 32,  # 32 character secret key
            "RATE_LIMIT_PER_MINUTE": 60,
            "SESSION_TIMEOUT": 3600,
            "BCRYPT_ROUNDS": 12
        }
        
        result = validate_security_config(config)
        
        assert result is True

    def test_validate_security_config_weak_key(self):
        """Test security config validation with weak secret key"""
        config = {
            "SECRET_KEY": "weak",
            "RATE_LIMIT_PER_MINUTE": 60
        }
        
        result = validate_security_config(config)
        
        assert result is False

    def test_validate_security_config_missing_key(self):
        """Test security config validation with missing secret key"""
        config = {
            "RATE_LIMIT_PER_MINUTE": 60
        }
        
        result = validate_security_config(config)
        
        assert result is False

    def test_config_validator_validate_all(self):
        """Test validating all configs"""
        validator = ConfigValidator()
        
        valid_config = {
            "BOT_TOKEN": "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
            "WEBHOOK_URL": "https://example.com/webhook",
            "DATABASE_URL": "postgresql://user:pass@localhost:5432/db",
            "SECRET_KEY": "a" * 32,
            "RATE_LIMIT_PER_MINUTE": 60
        }
        
        result = validator.validate_all(valid_config)
        
        assert isinstance(result, dict)
        assert 'valid' in result
        assert 'errors' in result


@pytest.mark.skipif(not LOGGING_CONFIG_AVAILABLE, reason="Logging config module not available")
class TestLoggingConfig:
    """Test logging configuration"""

    def test_setup_logging_basic(self):
        """Test basic logging setup"""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = os.path.join(temp_dir, "test.log")
            
            result = setup_logging(
                log_level="INFO",
                log_file=log_file,
                enable_json=False
            )
            
            assert result is True

    def test_setup_logging_with_json(self):
        """Test logging setup with JSON format"""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = os.path.join(temp_dir, "test.log")
            
            result = setup_logging(
                log_level="DEBUG",
                log_file=log_file,
                enable_json=True
            )
            
            assert result is True

    def test_get_logger(self):
        """Test logger retrieval"""
        logger = get_logger("test_logger")
        
        assert logger is not None
        assert logger.name == "test_logger"

    def test_configure_json_logging(self):
        """Test JSON logging configuration"""
        logger = get_logger("json_test")
        
        result = configure_json_logging(logger)
        
        assert result is True

    def test_configure_file_logging(self):
        """Test file logging configuration"""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = os.path.join(temp_dir, "test.log")
            logger = get_logger("file_test")
            
            result = configure_file_logging(logger, log_file)
            
            assert result is True

    def test_logging_config_invalid_level(self):
        """Test logging config with invalid level"""
        result = setup_logging(log_level="INVALID_LEVEL")
        
        # Should handle gracefully or return False
        assert isinstance(result, bool)

    def test_logging_config_invalid_file_path(self):
        """Test logging config with invalid file path"""
        result = setup_logging(
            log_file="/invalid/path/that/does/not/exist/test.log"
        )
        
        # Should handle gracefully
        assert isinstance(result, bool)


@pytest.mark.skipif(not SECURITY_UTILS_AVAILABLE, reason="Security utils module not available")
class TestSecurityUtils:
    """Test security utilities"""

    def test_security_utils_creation(self):
        """Test security utils creation"""
        utils = SecurityUtils()
        
        assert utils is not None

    def test_hash_password(self):
        """Test password hashing"""
        password = "test_password123"
        
        hashed = hash_password(password)
        
        assert hashed is not None
        assert isinstance(hashed, str)
        assert hashed != password  # Should be hashed
        assert len(hashed) > 20  # Reasonable hash length

    def test_verify_password_correct(self):
        """Test password verification with correct password"""
        password = "test_password123"
        hashed = hash_password(password)
        
        result = verify_password(password, hashed)
        
        assert result is True

    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password"""
        password = "test_password123"
        wrong_password = "wrong_password"
        hashed = hash_password(password)
        
        result = verify_password(wrong_password, hashed)
        
        assert result is False

    def test_generate_secure_token(self):
        """Test secure token generation"""
        token = generate_secure_token()
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 10  # Reasonable token length

    def test_generate_secure_token_custom_length(self):
        """Test secure token generation with custom length"""
        length = 32
        token = generate_secure_token(length=length)
        
        assert token is not None
        assert isinstance(token, str)
        # Note: Hex encoding doubles the length
        assert len(token) == length * 2

    def test_security_utils_token_uniqueness(self):
        """Test that generated tokens are unique"""
        token1 = generate_secure_token()
        token2 = generate_secure_token()
        
        assert token1 != token2

    def test_security_utils_hash_uniqueness(self):
        """Test that password hashes are unique (due to salt)"""
        password = "same_password"
        
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        
        # Different hashes due to different salts
        assert hash1 != hash2
        
        # But both should verify correctly
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True 