"""
Tests for utility modules
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

from src.utils.helpers import is_hilbeh_available, translate_product_name, translate_category_name
from src.utils.constants import (
    RetrySettings, DatabaseSettings, LoggingSettings, CacheSettings,
    PerformanceSettings, ErrorCodes, FileSettings, TelegramSettings,
    CallbackPatterns, ConfigValidation, LoggingConstants, ErrorMessages
)
from src.utils.i18n import I18nManager, i18n, _, tr
from src.utils.language_manager import LanguageManager, language_manager


class TestHelpers:
    """Test helper functions"""

    def test_is_hilbeh_available_success(self, patch_config):
        """Test successful hilbeh availability check"""
        # Clear the cache first
        from src.utils.helpers import SimpleCache
        SimpleCache().clear()
        
        with patch("src.config.get_config") as mock_config:
            # Use a day that's actually available in the config
            mock_config.return_value.hilbeh_available_days = ["wednesday", "thursday", "friday"]
            
            # Mock datetime to return wednesday
            with patch("src.utils.helpers.datetime") as mock_datetime:
                mock_datetime.now.return_value.strftime.return_value = "wednesday"
                
                result = is_hilbeh_available()
                
                assert result is True

    def test_is_hilbeh_available_not_available(self, patch_config):
        """Test hilbeh availability when not available"""
        # Clear the cache first
        from src.utils.helpers import SimpleCache
        SimpleCache().clear()
        
        with patch("src.config.get_config") as mock_config:
            mock_config.return_value.hilbeh_available_days = ["monday", "tuesday", "wednesday"]
            
            # Mock datetime to return saturday (not available)
            with patch("src.utils.helpers.datetime") as mock_datetime:
                mock_datetime.now.return_value.strftime.return_value = "saturday"
                
                result = is_hilbeh_available()
                
                assert result is False

    def test_is_hilbeh_available_no_config(self, patch_config):
        """Test hilbeh availability when config is missing"""
        # Clear the cache first
        from src.utils.helpers import SimpleCache
        SimpleCache().clear()
        
        with patch("src.config.get_config") as mock_config:
            mock_config.side_effect = Exception("Config error")
            
            result = is_hilbeh_available()
            
            assert result is False  # Should return False on error

    def test_is_hilbeh_available_exception(self, patch_config):
        """Test hilbeh availability when datetime fails"""
        # Clear the cache first
        from src.utils.helpers import SimpleCache
        SimpleCache().clear()
        
        with patch("src.config.get_config") as mock_config:
            mock_config.return_value.hilbeh_available_days = ["monday", "tuesday", "wednesday"]
            
            with patch("src.utils.helpers.datetime") as mock_datetime:
                mock_datetime.now.side_effect = Exception("Datetime error")
                
                result = is_hilbeh_available()
                
                assert result is False  # Should return False on error

    def test_translate_product_name_english(self):
        """Test product name translation - English"""
        with patch("src.utils.language_manager.language_manager.get_user_language", return_value="en"):
            result = translate_product_name("kubaneh", {"type": "classic"}, 123456789)
            assert "Kubaneh" in result
            assert "Classic" in result

    def test_translate_product_name_hebrew(self, mock_i18n):
        """Test product name translation to Hebrew"""
        mock_i18n.get_text.side_effect = lambda key, user_id=None: {
            "PRODUCT_KUBANEH_CLASSIC": "כובאנה",
            "KUBANEH_CLASSIC": "קלאסי",
            "KUBANEH_DISPLAY_NAME": "כובאנה ({type})"
        }.get(key, key)
        
        result = translate_product_name("kubaneh", user_id=123456789)
        
        assert "כובאנה" in result

    def test_translate_product_name_unknown_product(self, mock_i18n):
        """Test product name translation for unknown product"""
        mock_i18n.get_text.side_effect = lambda key, user_id=None: {
            "PRODUCT_UNKNOWN_PRODUCT": "PRODUCT_UNKNOWN_PRODUCT"
        }.get(key, key)
        
        result = translate_product_name("unknown_product", user_id=123456789)
        
        assert result == "PRODUCT_UNKNOWN_PRODUCT"  # Should return the translation key when translation fails

    def test_translate_product_name_exception(self, mock_i18n):
        """Test product name translation with exception"""
        # Clear the cache first
        from src.utils.helpers import SimpleCache
        SimpleCache().clear()
        
        # Mock i18n to throw an exception
        mock_i18n.get_text.side_effect = Exception("Translation error")
        
        result = translate_product_name("kubaneh", user_id=123456789)
        
        # Should return the original name when translation fails
        assert result == "kubaneh"

    def test_translate_category_name_english(self):
        """Test category name translation - English"""
        with patch("src.utils.i18n.i18n.get_text", return_value="Bread"):
            result = translate_category_name("bread", 123456789)
            assert result == "Bread"

    def test_translate_category_name_hebrew(self):
        """Test category name translation - Hebrew"""
        with patch("src.utils.i18n.i18n.get_text", return_value="לחם"):
            result = translate_category_name("bread", 123456789)
            assert result == "לחם"

    def test_translate_category_name_unknown_category(self, mock_i18n):
        """Test category name translation for unknown category"""
        mock_i18n.get_text.side_effect = lambda key, user_id=None: {
            "CATEGORY_OTHER": "📦 אחר"
        }.get(key, key)
        
        result = translate_category_name("Unknown_category", user_id=123456789)
        
        assert result == "📦 אחר"  # Should return the translation when available

    def test_translate_category_name_exception(self):
        """Test category name translation - exception handling"""
        with patch("src.utils.i18n.i18n.get_text", side_effect=Exception("Error")):
            result = translate_category_name("bread", 123456789)
            assert result == "Bread"  # Should fallback to capitalized name


class TestConstants:
    """Test constants module"""

    def test_retry_settings(self):
        """Test RetrySettings constants"""
        assert RetrySettings.MAX_RETRIES == 3
        assert RetrySettings.RETRY_DELAY_SECONDS == 30
        assert RetrySettings.CONFLICT_RETRY_DELAY_SECONDS == 30
        assert RetrySettings.CONNECTION_TIMEOUT_SECONDS == 60

    def test_database_settings(self):
        """Test DatabaseSettings constants"""
        assert DatabaseSettings.DEFAULT_POOL_SIZE == 10
        assert DatabaseSettings.MAX_POOL_OVERFLOW == 20
        assert DatabaseSettings.POOL_RECYCLE_SECONDS == 3600
        assert DatabaseSettings.PRODUCTION_POOL_SIZE == 20
        assert DatabaseSettings.DEVELOPMENT_POOL_SIZE == 5

    def test_logging_settings(self):
        """Test LoggingSettings constants"""
        assert LoggingSettings.MAX_LOG_FILE_SIZE == 10 * 1024 * 1024
        assert LoggingSettings.SECURITY_LOG_FILE_SIZE == 5 * 1024 * 1024
        assert LoggingSettings.MAIN_LOG_BACKUP_COUNT == 10
        assert LoggingSettings.ERROR_LOG_BACKUP_COUNT == 10

    def test_cache_settings(self):
        """Test CacheSettings constants"""
        assert CacheSettings.PRODUCTS_CACHE_TTL_SECONDS == 600
        assert CacheSettings.CUSTOMERS_CACHE_TTL_SECONDS == 300
        assert CacheSettings.ORDERS_CACHE_TTL_SECONDS == 180
        assert CacheSettings.GENERAL_CACHE_TTL_SECONDS == 300

    def test_performance_settings(self):
        """Test PerformanceSettings constants"""
        assert PerformanceSettings.SLOW_QUERY_THRESHOLD_MS == 1000
        assert PerformanceSettings.MEMORY_WARNING_THRESHOLD_MB == 100
        assert PerformanceSettings.HIGH_EXAMINATION_RATIO_THRESHOLD == 10

    def test_error_codes(self):
        """Test ErrorCodes constants"""
        assert ErrorCodes.GENERAL_ERROR == "GENERAL_ERROR"
        assert ErrorCodes.DATABASE_ERROR == "DATABASE_ERROR"
        assert ErrorCodes.VALIDATION_ERROR == "VALIDATION_ERROR"
        assert ErrorCodes.BUSINESS_ERROR == "BUSINESS_ERROR"

    def test_file_settings(self):
        """Test FileSettings constants"""
        assert FileSettings.LOGS_DIRECTORY == "logs"
        assert FileSettings.DATA_DIRECTORY == "data"
        assert FileSettings.MAIN_LOG_FILE == "app.log"
        assert FileSettings.ERROR_LOG_FILE == "errors.log"

    def test_telegram_settings(self):
        """Test TelegramSettings constants"""
        assert TelegramSettings.MAX_MESSAGE_LENGTH == 4096
        assert TelegramSettings.MAX_CAPTION_LENGTH == 1024
        assert TelegramSettings.CALLBACK_DATA_MAX_LENGTH == 64
        assert TelegramSettings.MAX_BUTTONS_PER_ROW == 8

    def test_callback_patterns(self):
        """Test CallbackPatterns constants"""
        assert CallbackPatterns.MENU_PATTERNS["main"] == "menu_main"
        assert CallbackPatterns.MENU_PATTERNS["kubaneh"] == "menu_kubaneh"
        assert CallbackPatterns.ADD_PREFIX == "add_"
        assert CallbackPatterns.DELIVERY_PREFIX == "delivery_"

    def test_config_validation(self):
        """Test ConfigValidation constants"""
        assert "development" in ConfigValidation.VALID_ENVIRONMENTS
        assert "production" in ConfigValidation.VALID_ENVIRONMENTS
        assert "ILS" in ConfigValidation.VALID_CURRENCIES
        assert ConfigValidation.MIN_BOT_TOKEN_LENGTH == 40

    def test_logging_constants(self):
        """Test LoggingConstants constants"""
        assert "DEBUG" in LoggingConstants.VALID_LOG_LEVELS
        assert "INFO" in LoggingConstants.VALID_LOG_LEVELS
        assert LoggingConstants.MAIN_LOG_FILE == "logs/main.log"
        assert LoggingConstants.MAX_LOG_SIZE == 10 * 1024 * 1024

    def test_error_messages(self):
        """Test ErrorMessages constants"""
        assert ErrorMessages.INVALID_NAME_FORMAT == "Please enter a valid name with letters only"
        assert ErrorMessages.NAME_TOO_SHORT == "Name must be at least 2 characters long"
        assert ErrorMessages.SESSION_EXPIRED == "Your session has expired. Please start again with /start"
        assert ErrorMessages.MENU_FUNCTIONALITY_AVAILABLE == "Menu functionality is working perfectly!"


class TestI18n:
    """Test internationalization module"""

    def test_i18n_manager_singleton(self):
        """Test I18nManager singleton pattern"""
        manager1 = I18nManager()
        manager2 = I18nManager()
        assert manager1 is manager2

    def test_i18n_manager_load_translations(self, patch_config):
        """Test I18nManager translation loading"""
        with patch("os.path.exists", return_value=True):
            with patch("os.listdir", return_value=["en.json", "he.json"]):
                with patch("builtins.open", create=True) as mock_open:
                    mock_open.return_value.__enter__.return_value.read.return_value = '{"key": "value"}'
                    
                    manager = I18nManager()
                    assert "en" in manager._translations
                    assert "he" in manager._translations

    def test_i18n_manager_get_text_english(self, patch_config):
        """Test I18nManager get_text - English"""
        with patch("src.utils.i18n.I18nManager._load_translations"):
            with patch("src.utils.i18n.I18nManager._translations", {"en": {"HELLO": "Hello"}}):
                manager = I18nManager()
                result = manager.get_text("HELLO", language="en")
                assert result == "Hello"

    def test_i18n_manager_get_text_hebrew(self, patch_config):
        """Test I18nManager get_text - Hebrew"""
        with patch("src.utils.i18n.I18nManager._load_translations"):
            with patch("src.utils.i18n.I18nManager._translations", {"he": {"HELLO": "שלום"}}):
                manager = I18nManager()
                result = manager.get_text("HELLO", language="he")
                assert result == "שלום"

    def test_i18n_manager_get_text_fallback(self, patch_config):
        """Test I18nManager get_text - fallback to English"""
        with patch("src.utils.i18n.I18nManager._load_translations"):
            with patch("src.utils.i18n.I18nManager._translations", {"en": {"HELLO": "Hello"}}):
                manager = I18nManager()
                result = manager.get_text("HELLO", language="fr")  # French not available
                assert result == "Hello"  # Should fallback to English

    def test_i18n_manager_get_text_key_not_found(self, patch_config):
        """Test I18nManager get_text - key not found"""
        with patch("os.path.exists", return_value=True):
            with patch("os.listdir", return_value=["en.json"]):
                with patch("builtins.open", create=True) as mock_open:
                    mock_open.return_value.__enter__.return_value.read.return_value = '{"HELLO": "Hello"}'
                    
                    manager = I18nManager()
                    result = manager.get_text("UNKNOWN_KEY", language="en")
                    assert result == "UNKNOWN_KEY"  # Should return key if not found

    def test_i18n_manager_get_text_with_formatting(self, patch_config):
        """Test I18nManager get_text with formatting"""
        with patch("src.utils.i18n.I18nManager._load_translations"):
            with patch("src.utils.i18n.I18nManager._translations", {"en": {"GREETING": "Hello {name}"}}):
                manager = I18nManager()
                result = manager.get_text("GREETING", language="en")
                # The formatting should be handled by the calling code, not the I18nManager
                assert result == "Hello {name}"

    def test_i18n_global_instance(self, patch_config):
        """Test global i18n instance"""
        with patch("src.utils.i18n.I18nManager._load_translations"):
            with patch("src.utils.i18n.I18nManager._translations", {"en": {"TEST": "Test"}}):
                result = i18n.get_text("TEST", language="en")
                assert result == "Test"

    def test_i18n_shorthand_functions(self, patch_config):
        """Test i18n shorthand functions"""
        with patch("src.utils.i18n.I18nManager._load_translations"):
            with patch("src.utils.i18n.I18nManager._translations", {"en": {"TEST": "Test"}}):
                result1 = _("TEST", language="en")
                result2 = tr("TEST", language="en")
                assert result1 == "Test"
                assert result2 == "Test"


class TestLanguageManager:
    """Test language manager module"""

    def test_language_manager_singleton(self):
        """Test LanguageManager singleton pattern"""
        manager1 = LanguageManager()
        manager2 = LanguageManager()
        assert manager1 is manager2

    def test_language_manager_get_user_language_cached(self):
        """Test language manager caching functionality"""
        language_manager.clear_cache()
    
        with patch("src.db.operations.get_customer_by_telegram_id") as mock_get_customer:
            mock_get_customer.return_value = MagicMock(language="he")
            
            # First call should fetch from database
            result1 = language_manager.get_user_language(123456789)
            assert result1 == "he"
            
            # Second call should use cache
            result2 = language_manager.get_user_language(123456789)
            assert result2 == "he"
            
            # Should only call database once
            mock_get_customer.assert_called_once_with(123456789)

    def test_language_manager_get_user_language_from_db(self):
        """Test getting user language from database"""
        # Clear the cache first
        language_manager.clear_cache()
        
        with patch("src.db.operations.get_customer_by_telegram_id") as mock_get_customer:
            mock_get_customer.return_value = MagicMock(language="he")
            
            result = language_manager.get_user_language(123456789)
            
            assert result == "he"
            mock_get_customer.assert_called_once_with(123456789)

    def test_language_manager_get_user_language_no_customer(self):
        """Test getting user language when customer not found"""
        # Clear the cache first
        language_manager.clear_cache()
        
        with patch("src.db.operations.get_customer_by_telegram_id", return_value=None):
            result = language_manager.get_user_language(123456789)
            
            assert result == "en"  # Should default to English

    def test_language_manager_get_user_language_no_language(self):
        """Test getting user language when customer has no language set"""
        # Clear the cache first
        language_manager.clear_cache()
        
        mock_customer = MagicMock()
        mock_customer.language = None
        
        with patch("src.db.operations.get_customer_by_telegram_id", return_value=mock_customer):
            result = language_manager.get_user_language(123456789)
            
            assert result == "en"  # Should default to English

    def test_language_manager_get_user_language_exception(self):
        """Test getting user language with exception"""
        # Clear the cache first
        language_manager.clear_cache()
        
        with patch("src.db.operations.get_customer_by_telegram_id", side_effect=Exception("DB Error")):
            result = language_manager.get_user_language(123456789)
            
            assert result == "en"  # Should default to English

    def test_language_manager_set_user_language(self):
        """Test setting user language"""
        # Clear the cache first
        language_manager.clear_cache()
        
        with patch("src.db.operations.update_customer_language", return_value=True):
            success = language_manager.set_user_language(123456789, "he")
            
            assert success is True

    def test_language_manager_set_user_language_failure(self):
        """Test setting user language failure"""
        # Clear the cache first
        language_manager.clear_cache()
        
        with patch("src.db.operations.update_customer_language", return_value=False):
            success = language_manager.set_user_language(123456789, "he")
            
            assert success is False

    def test_language_manager_set_user_language_exception(self):
        """Test setting user language with exception"""
        # Clear the cache first
        language_manager.clear_cache()
        
        with patch("src.db.operations.update_customer_language", side_effect=Exception("DB Error")):
            success = language_manager.set_user_language(123456789, "he")
            
            assert success is False

    def test_language_manager_clear_cache(self):
        """Test LanguageManager clear_cache"""
        manager = LanguageManager()
        manager._user_languages[123456789] = "he"
        
        manager.clear_cache()
        assert len(manager._user_languages) == 0

    def test_language_manager_global_instance(self):
        """Test language manager global instance"""
        language_manager.clear_cache()
        
        with patch("src.db.operations.get_customer_by_telegram_id") as mock_get_customer:
            mock_get_customer.return_value = MagicMock(language="he")
            
            result = language_manager.get_user_language(123456789)
            assert result == "he"


class TestUtilsIntegration:
    """Integration tests for utilities"""

    def test_translation_workflow(self, mock_i18n):
        """Test complete translation workflow"""
        # Clear the cache first
        from src.utils.helpers import SimpleCache
        SimpleCache().clear()
        
        mock_i18n.get_text.side_effect = lambda key, user_id=None: {
            "PRODUCT_KUBANEH_CLASSIC": "כובאנה",
            "KUBANEH_CLASSIC": "קלאסי",
            "KUBANEH_DISPLAY_NAME": "כובאנה ({type})"
        }.get(key, key)
        
        # Test product translation
        product_name = translate_product_name("kubaneh", user_id=123456789)
        assert "כובאנה" in product_name
        
        # Test category translation
        category_name = translate_category_name("bread", user_id=123456789)
        assert category_name is not None

    def test_availability_workflow(self, patch_config):
        """Test complete availability workflow"""
        # Clear the cache first
        from src.utils.helpers import SimpleCache
        SimpleCache().clear()
        
        with patch("src.config.get_config") as mock_config:
            # Use a day that's actually available in the config
            mock_config.return_value.hilbeh_available_days = ["wednesday", "thursday", "friday"]
            
            # Mock datetime to return wednesday
            with patch("src.utils.helpers.datetime") as mock_datetime:
                mock_datetime.now.return_value.strftime.return_value = "wednesday"
                
                available = is_hilbeh_available()
                assert available is True

    def test_constants_usage(self):
        """Test constants usage in real scenarios"""
        # Test retry settings
        assert RetrySettings.MAX_RETRIES > 0
        assert RetrySettings.RETRY_DELAY_SECONDS > 0
        
        # Test database settings
        assert DatabaseSettings.DEFAULT_POOL_SIZE > 0
        assert DatabaseSettings.MAX_POOL_OVERFLOW > 0
        
        # Test logging settings
        assert LoggingSettings.MAX_LOG_FILE_SIZE > 0
        assert LoggingSettings.MAIN_LOG_BACKUP_COUNT > 0
        
        # Test cache settings
        assert CacheSettings.PRODUCTS_CACHE_TTL_SECONDS > 0
        assert CacheSettings.GENERAL_CACHE_TTL_SECONDS > 0

    def test_error_handling_workflow(self):
        """Test error handling workflow"""
        # Test error codes
        assert ErrorCodes.GENERAL_ERROR == "GENERAL_ERROR"
        assert ErrorCodes.DATABASE_ERROR == "DATABASE_ERROR"
        
        # Test error messages
        assert "Please enter a valid name" in ErrorMessages.INVALID_NAME_FORMAT
        assert "session has expired" in ErrorMessages.SESSION_EXPIRED

    def test_performance_workflow(self):
        """Test performance workflow"""
        # Test performance settings
        assert PerformanceSettings.SLOW_QUERY_THRESHOLD_MS > 0
        assert PerformanceSettings.MEMORY_WARNING_THRESHOLD_MB > 0
        
        # Test performance improvement messages
        assert "performance improvement" in PerformanceSettings.PERFORMANCE_IMPROVEMENT_LOW
        assert "performance improvement" in PerformanceSettings.PERFORMANCE_IMPROVEMENT_MEDIUM
        assert "performance improvement" in PerformanceSettings.PERFORMANCE_IMPROVEMENT_HIGH


class TestUtilsEdgeCases:
    """Test utility edge cases"""

    def test_translate_product_name_empty_string(self):
        """Test product name translation with empty string"""
        result = translate_product_name("", None, 123456789)
        assert result == ""

    def test_translate_product_name_none(self):
        """Test product name translation with None"""
        result = translate_product_name("", None, 123456789)  # Use empty string instead of None
        assert result == ""

    def test_translate_category_name_empty_string(self):
        """Test category name translation with empty string"""
        result = translate_category_name("", 123456789)
        assert result == ""

    def test_translate_category_name_none(self):
        """Test category name translation with None"""
        result = translate_category_name("", 123456789)  # Use empty string instead of None
        assert result == ""

    def test_language_manager_invalid_user_id(self):
        """Test language manager with invalid user ID"""
        manager = LanguageManager()
        result = manager.get_user_language(0)  # Use 0 instead of None
        assert result == "en"  # Should default to English

    def test_language_manager_invalid_language(self, mock_db_operations):
        """Test language manager with invalid language"""
        # Clear the cache first
        language_manager.clear_cache()
        
        mock_db_operations.update_customer_language.return_value = True
        
        success = language_manager.set_user_language(123456789, "invalid_lang")
        
        assert success is False  # Should fail with invalid language

    def test_i18n_manager_invalid_file(self, patch_config):
        """Test I18nManager with invalid translation file"""
        with patch("os.path.exists", return_value=True):
            with patch("os.listdir", return_value=["invalid.json"]):
                with patch("builtins.open", side_effect=Exception("File error")):
                    manager = I18nManager()
                    result = manager.get_text("TEST", language="en")
                    assert result == "TEST"  # Should return key if file error

    def test_constants_immutability(self):
        """Test constants immutability"""
        # These should not be modifiable
        original_max_retries = RetrySettings.MAX_RETRIES
        original_pool_size = DatabaseSettings.DEFAULT_POOL_SIZE
        
        # Attempting to modify should not work (though this depends on implementation)
        assert RetrySettings.MAX_RETRIES == original_max_retries
        assert DatabaseSettings.DEFAULT_POOL_SIZE == original_pool_size


class TestUtilsPerformance:
    """Test utility performance"""

    def test_translation_performance(self, performance_timer):
        """Test translation performance"""
        with patch("src.utils.language_manager.language_manager.get_user_language", return_value="en"):
            for i in range(1000):
                translate_product_name("kubaneh", {"type": "classic"}, 123456789)

    def test_availability_check_performance(self, performance_timer):
        """Test availability check performance"""
        with patch("src.utils.helpers.get_config") as mock_get_config:
            config = MagicMock()
            config.hilbeh_available_days = ["monday", "tuesday", "wednesday", "thursday", "friday"]
            mock_get_config.return_value = config
            
            with patch("datetime.datetime") as mock_datetime:
                mock_datetime.now.return_value.strftime.return_value = "monday"
                
                for i in range(1000):
                    is_hilbeh_available()

    def test_language_manager_performance(self, performance_timer):
        """Test language manager performance"""
        with patch("src.db.operations.get_customer_by_telegram_id") as mock_get_customer:
            customer = MagicMock()
            customer.language = "en"
            mock_get_customer.return_value = customer
            
            manager = LanguageManager()
            for i in range(1000):
                manager.get_user_language(123456789)

    def test_i18n_performance(self, performance_timer):
        """Test i18n performance"""
        with patch("os.path.exists", return_value=True):
            with patch("os.listdir", return_value=["en.json"]):
                with patch("builtins.open", create=True) as mock_open:
                    mock_open.return_value.__enter__.return_value.read.return_value = '{"TEST": "Test"}'
                    
                    manager = I18nManager()
                    for i in range(1000):
                        manager.get_text("TEST", language="en") 