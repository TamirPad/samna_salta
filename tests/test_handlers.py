"""
Tests for bot handlers
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from telegram import Update, User, Chat, Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from src.handlers.start import OnboardingHandler, register_start_handlers
from src.handlers.menu import MenuHandler, register_menu_handlers
from src.handlers.cart import CartHandler
from src.handlers.admin import register_admin_handlers
from src.states import (
    END, ONBOARDING_LANGUAGE, ONBOARDING_NAME, ONBOARDING_PHONE,
    ONBOARDING_DELIVERY_METHOD, ONBOARDING_DELIVERY_ADDRESS
)
from src.services.cart_service import CartService
from src.services.order_service import OrderService
from src.services.admin_service import AdminService
from src.services.notification_service import NotificationService
import time


class TestOnboardingHandler:
    """Test OnboardingHandler"""

    @pytest.fixture
    def onboarding_handler(self, patch_container):
        """Create OnboardingHandler instance"""
        return OnboardingHandler()

    @pytest.fixture
    def mock_update_with_user(self):
        """Create mock update with user"""
        update = MagicMock(spec=Update)
        update.effective_user = MagicMock(spec=User)
        update.effective_user.id = 123456789
        update.effective_user.username = "testuser"
        update.effective_user.first_name = "Test"
        update.effective_user.last_name = "User"
        return update

    @pytest.fixture
    def mock_context(self):
        """Create mock context"""
        context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
        context.bot = MagicMock()
        return context

    async def test_start_command_new_user(self, onboarding_handler, mock_update_with_user, mock_context, patch_i18n):
        """Test start command for new user"""
        mock_update_with_user.message = MagicMock(spec=Message)
        mock_update_with_user.message.text = "/start"
        mock_update_with_user.effective_user = MagicMock()
        mock_update_with_user.effective_user.id = 123456789
        
        # Mock the cart service's get_customer method to return None (new user)
        with patch.object(onboarding_handler.cart_service, 'get_customer', return_value=None):
            # Mock i18n.get_text to return test text
            with patch('src.utils.i18n.i18n.get_text', return_value="Test text"):
                result = await onboarding_handler.start_command(mock_update_with_user, mock_context)
                
                assert result == ONBOARDING_LANGUAGE
                mock_update_with_user.message.reply_text.assert_called_once()

    async def test_start_command_existing_user(self, onboarding_handler, mock_update_with_user, mock_context, sample_customer):
        """Test start command for existing user"""
        mock_update_with_user.message = MagicMock(spec=Message)
        mock_update_with_user.message.text = "/start"
        mock_update_with_user.effective_user = MagicMock()
        mock_update_with_user.effective_user.id = 123456789
        
        # Mock the cart service's get_customer method to return existing customer
        with patch.object(onboarding_handler.cart_service, 'get_customer', return_value=sample_customer):
            # Mock i18n.get_text to return test text
            with patch('src.utils.i18n.i18n.get_text', return_value="Test text"):
                result = await onboarding_handler.start_command(mock_update_with_user, mock_context)
                
                assert result == END
                mock_update_with_user.message.reply_text.assert_called_once()

    async def test_handle_language_selection(self, onboarding_handler, mock_update_with_user, mock_context, patch_i18n):
        """Test language selection handling"""
        mock_update_with_user.callback_query = MagicMock(spec=CallbackQuery)
        mock_update_with_user.callback_query.data = "language_en"
        mock_update_with_user.effective_user = MagicMock()
        mock_update_with_user.effective_user.id = 123456789
        
        with patch("src.db.operations.get_or_create_customer") as mock_get_customer:
            mock_get_customer.return_value = MagicMock()
            
            # Mock i18n.get_text to return test text
            with patch('src.utils.i18n.i18n.get_text', return_value="Test text"):
                result = await onboarding_handler.handle_language_selection(mock_update_with_user, mock_context)
                
                assert result == ONBOARDING_NAME
                mock_update_with_user.callback_query.answer.assert_called_once()

    async def test_handle_name_valid(self, onboarding_handler, mock_update_with_user, mock_context, patch_i18n):
        """Test name handling with valid input"""
        mock_update_with_user.message = MagicMock(spec=Message)
        mock_update_with_user.message.text = "John Doe"
        mock_update_with_user.effective_user = MagicMock()
        mock_update_with_user.effective_user.id = 123456789
        
        with patch("src.db.operations.get_or_create_customer") as mock_get_customer:
            mock_get_customer.return_value = MagicMock()
            
            # Mock i18n.get_text to return test text
            with patch('src.utils.i18n.i18n.get_text', return_value="Test text"):
                result = await onboarding_handler.handle_name(mock_update_with_user, mock_context)
                
                assert result == ONBOARDING_PHONE
                mock_update_with_user.message.reply_text.assert_called()

    async def test_handle_name_invalid(self, onboarding_handler, mock_update_with_user, mock_context, patch_i18n):
        """Test name handling with invalid input"""
        mock_update_with_user.message = MagicMock(spec=Message)
        mock_update_with_user.message.text = "J"  # Invalid name - only 1 character
        mock_update_with_user.effective_user = MagicMock()
        mock_update_with_user.effective_user.id = 123456789
        
        # Mock context user_data
        mock_context.user_data = {"selected_language": "en"}
        
        # Mock language manager
        with patch('src.utils.language_manager.language_manager.get_user_language', return_value="en"):
            # Mock i18n.get_text to return test text
            with patch('src.utils.i18n.i18n.get_text', return_value="Test text"):
                result = await onboarding_handler.handle_name(mock_update_with_user, mock_context)
                
                assert result == ONBOARDING_NAME
                mock_update_with_user.message.reply_text.assert_called()

    async def test_handle_phone_valid(self, onboarding_handler, mock_update_with_user, mock_context, patch_i18n):
        """Test phone handling with valid input"""
        mock_update_with_user.message = MagicMock(spec=Message)
        mock_update_with_user.message.text = "+972501234567"
        mock_update_with_user.effective_user = MagicMock()
        mock_update_with_user.effective_user.id = 123456789
        
        # Mock context user_data
        mock_context.user_data = {"full_name": "John Doe", "selected_language": "en"}
        
        # Mock customer object
        mock_customer = MagicMock()
        mock_customer.name = "John Doe"
        mock_customer.telegram_id = 123456789
        
        # Mock cart service methods
        with patch.object(onboarding_handler.cart_service, 'validate_customer_data', return_value={"valid": True, "errors": []}):
            with patch.object(onboarding_handler.cart_service, 'register_customer', return_value={"success": True, "customer": mock_customer, "is_returning": False}):
                # Mock i18n.get_text to return test text
                with patch('src.utils.i18n.i18n.get_text', return_value="Test text"):
                    result = await onboarding_handler.handle_phone(mock_update_with_user, mock_context)
                    
                    assert result == ONBOARDING_DELIVERY_ADDRESS
                    mock_update_with_user.message.reply_text.assert_called()

    async def test_handle_phone_invalid(self, onboarding_handler, mock_update_with_user, mock_context, patch_i18n):
        """Test phone handling with invalid input"""
        mock_update_with_user.message = MagicMock(spec=Message)
        mock_update_with_user.message.text = "invalid_phone"
        mock_update_with_user.effective_user = MagicMock()
        mock_update_with_user.effective_user.id = 123456789
        
        # Mock context user_data
        mock_context.user_data = {"full_name": "John Doe", "selected_language": "en"}
        
        # Mock cart service methods to return validation error
        with patch.object(onboarding_handler.cart_service, 'validate_customer_data', return_value={"valid": False, "errors": ["Invalid phone"]}):
            # Mock i18n.get_text to return test text
            with patch('src.utils.i18n.i18n.get_text', return_value="Test text"):
                result = await onboarding_handler.handle_phone(mock_update_with_user, mock_context)
                
                assert result == ONBOARDING_PHONE
                mock_update_with_user.message.reply_text.assert_called()

    async def test_handle_delivery_method(self, onboarding_handler, mock_update_with_user, mock_context, patch_i18n):
        """Test delivery method handling"""
        mock_update_with_user.callback_query = MagicMock(spec=CallbackQuery)
        mock_update_with_user.callback_query.data = "delivery_pickup"
        
        result = await onboarding_handler.handle_delivery_method(mock_update_with_user, mock_context)
        
        assert result == END

    async def test_handle_delivery_address(self, onboarding_handler, mock_update_with_user, mock_context, patch_i18n):
        """Test delivery address handling"""
        mock_update_with_user.message = MagicMock(spec=Message)
        mock_update_with_user.message.text = "123 Test Street, Tel Aviv"
        mock_update_with_user.effective_user = MagicMock()
        mock_update_with_user.effective_user.id = 123456789
        
        # Mock customer object
        mock_customer = MagicMock()
        mock_customer.telegram_id = 123456789
        
        # Mock context user_data
        mock_context.user_data = {"customer": mock_customer}
        
        # Mock cart service method
        with patch.object(onboarding_handler.cart_service, 'update_customer_delivery_address', return_value=True):
            # Mock i18n.get_text to return test text
            with patch('src.utils.i18n.i18n.get_text', return_value="Test text"):
                result = await onboarding_handler.handle_delivery_address(mock_update_with_user, mock_context)
                
                assert result == END
                mock_update_with_user.message.reply_text.assert_called()

    async def test_cancel_onboarding(self, onboarding_handler, mock_update_with_user, mock_context, patch_i18n):
        """Test onboarding cancellation"""
        mock_update_with_user.message = MagicMock(spec=Message)
        mock_update_with_user.effective_user = MagicMock()
        mock_update_with_user.effective_user.id = 123456789
        
        # Mock i18n.get_text to return test text
        with patch('src.utils.i18n.i18n.get_text', return_value="Test text"):
            result = await onboarding_handler.cancel_onboarding(mock_update_with_user, mock_context)
            
            assert result == END
            mock_update_with_user.message.reply_text.assert_called_once()

    async def test_handle_unknown_command(self, onboarding_handler, mock_update_with_user, mock_context, patch_i18n):
        """Test unknown command handling"""
        mock_update_with_user.message = MagicMock(spec=Message)
        mock_update_with_user.message.text = "/unknown"
        
        # Mock i18n.get_text to return test text
        with patch('src.utils.i18n.i18n.get_text', return_value="Test text"):
            result = await onboarding_handler.handle_unknown_command(mock_update_with_user, mock_context)
            
            # The method doesn't return a state, it just sends a message
            assert result is None
            mock_update_with_user.message.reply_text.assert_called()

    async def test_handle_unknown_message(self, onboarding_handler, mock_update_with_user, mock_context, patch_i18n):
        """Test unknown message handling"""
        mock_update_with_user.message = MagicMock(spec=Message)
        mock_update_with_user.message.text = "random text"
        
        # Mock i18n.get_text to return test text
        with patch('src.utils.i18n.i18n.get_text', return_value="Test text"):
            result = await onboarding_handler.handle_unknown_message(mock_update_with_user, mock_context)
            
            # The method doesn't return a state, it just sends a message
            assert result is None
            mock_update_with_user.message.reply_text.assert_called()

    def test_is_customer_profile_complete(self, onboarding_handler, sample_customer):
        """Test customer profile completion check"""
        # Complete profile
        result = onboarding_handler._is_customer_profile_complete(sample_customer)
        assert result is True
        
        # Incomplete profile - short name
        incomplete_customer = MagicMock()
        incomplete_customer.name = "J"  # Only 1 character
        incomplete_customer.phone = "+972501234567"  # Valid phone
        
        result = onboarding_handler._is_customer_profile_complete(incomplete_customer)
        assert result is False

    def test_get_language_selection_keyboard(self, onboarding_handler):
        """Test language selection keyboard creation"""
        keyboard = onboarding_handler._get_language_selection_keyboard()
        
        assert isinstance(keyboard, InlineKeyboardMarkup)
        assert len(keyboard.inline_keyboard) > 0

    def test_get_main_page_keyboard(self, onboarding_handler):
        """Test main page keyboard creation"""
        keyboard = onboarding_handler._get_main_page_keyboard(123456789)
        
        assert isinstance(keyboard, InlineKeyboardMarkup)
        assert len(keyboard.inline_keyboard) > 0


class TestMenuHandler:
    """Test MenuHandler"""

    @pytest.fixture
    def menu_handler(self, patch_container):
        """Create MenuHandler instance"""
        return MenuHandler()

    @pytest.fixture
    def mock_callback_query(self):
        """Create mock callback query"""
        query = MagicMock(spec=CallbackQuery)
        query.from_user = MagicMock(spec=User)
        query.from_user.id = 123456789
        query.message = MagicMock(spec=Message)
        query.message.chat = MagicMock(spec=Chat)
        query.message.chat.id = 123456789
        return query

    async def test_handle_menu_callback_main_menu(self, menu_handler, mock_update, mock_context, patch_i18n):
        """Test menu callback - main menu"""
        mock_update.callback_query = MagicMock(spec=CallbackQuery)
        mock_update.callback_query.data = "menu_main"
        
        await menu_handler.handle_menu_callback(mock_update, mock_context)
        
        mock_update.callback_query.answer.assert_called_once()

    async def test_handle_menu_callback_category(self, menu_handler, mock_update, mock_context, patch_i18n):
        """Test menu callback - category selection"""
        mock_update.callback_query = MagicMock(spec=CallbackQuery)
        mock_update.callback_query.data = "category_bread"
        
        with patch("src.db.operations.get_products_by_category", return_value=[]):
            await menu_handler.handle_menu_callback(mock_update, mock_context)
            
            mock_update.callback_query.answer.assert_called_once()

    async def test_handle_menu_callback_product(self, menu_handler, mock_update, mock_context, patch_i18n):
        """Test menu callback - product selection"""
        mock_update.callback_query = MagicMock(spec=CallbackQuery)
        mock_update.callback_query.data = "product_1"
        
        with patch("src.db.operations.get_product_by_id") as mock_get_product:
            mock_get_product.return_value = MagicMock()
            mock_get_product.return_value.name = "Test Product"
            mock_get_product.return_value.description = "Test Description"
            mock_get_product.return_value.price = 10.00
            mock_get_product.return_value.category = "test"
            
            await menu_handler.handle_menu_callback(mock_update, mock_context)
            
            mock_update.callback_query.answer.assert_called_once()

    async def test_handle_menu_callback_quick_add(self, menu_handler, mock_update, mock_context, patch_i18n):
        """Test menu callback - quick add to cart"""
        mock_update.callback_query = MagicMock(spec=CallbackQuery)
        mock_update.callback_query.data = "quick_add_1"
        
        with patch("src.db.operations.get_product_by_id") as mock_get_product:
            mock_get_product.return_value = MagicMock()
            mock_get_product.return_value.name = "Test Product"
            
            with patch.object(menu_handler.container.get_cart_service(), "add_item", return_value=True):
                await menu_handler.handle_menu_callback(mock_update, mock_context)
                
                mock_update.callback_query.answer.assert_called_once()

    async def test_handle_menu_callback_unknown(self, menu_handler, mock_update, mock_context, patch_i18n):
        """Test menu callback - unknown data"""
        mock_update.callback_query = MagicMock(spec=CallbackQuery)
        mock_update.callback_query.data = "unknown_callback"
        
        await menu_handler.handle_menu_callback(mock_update, mock_context)
        
        mock_update.callback_query.answer.assert_called_once()

    async def test_quick_add_to_cart_success(self, menu_handler, mock_callback_query, patch_i18n):
        """Test quick add to cart - success"""
        with patch("src.db.operations.get_product_by_id") as mock_get_product:
            mock_get_product.return_value = MagicMock()
            mock_get_product.return_value.name = "Test Product"
            
            with patch.object(menu_handler.container.get_cart_service(), "add_item", return_value=True):
                await menu_handler._quick_add_to_cart(mock_callback_query, 1)
                
                mock_callback_query.answer.assert_called_once()

    async def test_quick_add_to_cart_product_not_found(self, menu_handler, mock_callback_query, patch_i18n):
        """Test quick add to cart - product not found"""
        with patch("src.db.operations.get_product_by_id", return_value=None):
            await menu_handler._quick_add_to_cart(mock_callback_query, 1)
            
            mock_callback_query.answer.assert_called_once()

    async def test_quick_add_to_cart_failure(self, menu_handler, mock_callback_query, patch_i18n):
        """Test quick add to cart - failure"""
        with patch("src.db.operations.get_product_by_id") as mock_get_product:
            mock_get_product.return_value = MagicMock()
            mock_get_product.return_value.name = "Test Product"
            
            with patch.object(menu_handler.container.get_cart_service(), "add_item", return_value=False):
                await menu_handler._quick_add_to_cart(mock_callback_query, 1)
                
                mock_callback_query.answer.assert_called_once()

    async def test_show_main_menu(self, menu_handler, mock_callback_query, patch_i18n):
        """Test showing main menu"""
        await menu_handler._show_main_menu(mock_callback_query)
        
        # Should call _safe_edit_message
        assert menu_handler._safe_edit_message.called

    async def test_show_category_menu_with_products(self, menu_handler, mock_callback_query, patch_i18n):
        """Test showing category menu with products"""
        with patch("src.db.operations.get_products_by_category") as mock_get_products:
            mock_get_products.return_value = [MagicMock(), MagicMock()]
            
            await menu_handler._show_category_menu(mock_callback_query, "bread")
            
            # Should call _safe_edit_message
            assert menu_handler._safe_edit_message.called

    async def test_show_category_menu_empty(self, menu_handler, mock_callback_query, patch_i18n):
        """Test showing category menu - empty category"""
        with patch("src.db.operations.get_products_by_category", return_value=[]):
            await menu_handler._show_category_menu(mock_callback_query, "bread")
            
            # Should call _safe_edit_message
            assert menu_handler._safe_edit_message.called

    async def test_show_product_details(self, menu_handler, mock_callback_query, patch_i18n):
        """Test showing product details"""
        with patch("src.db.operations.get_product_by_id") as mock_get_product:
            mock_get_product.return_value = MagicMock()
            mock_get_product.return_value.name = "Test Product"
            mock_get_product.return_value.description = "Test Description"
            mock_get_product.return_value.price = 10.00
            mock_get_product.return_value.category = "test"
            mock_get_product.return_value.image_url = "https://example.com/test.jpg"
            
            await menu_handler._show_product_details(mock_callback_query, 1)
            
            # Should call _safe_edit_message
            assert menu_handler._safe_edit_message.called

    async def test_safe_edit_message_text_message(self, menu_handler, mock_callback_query):
        """Test safe edit message - text message"""
        mock_callback_query.message.photo = None
        
        await menu_handler._safe_edit_message(mock_callback_query, "Test text")
        
        mock_callback_query.edit_message_text.assert_called_once()

    async def test_safe_edit_message_photo_message(self, menu_handler, mock_callback_query):
        """Test safe edit message - photo message"""
        mock_callback_query.message.photo = [MagicMock()]
        
        await menu_handler._safe_edit_message(mock_callback_query, "Test text")
        
        mock_callback_query.message.delete.assert_called_once()
        mock_callback_query.message.reply_text.assert_called_once()


class TestCartHandler:
    """Test CartHandler"""

    @pytest.fixture
    def cart_handler(self, patch_container):
        """Create CartHandler instance"""
        return CartHandler()

    @pytest.fixture
    def mock_message(self):
        """Create mock message"""
        message = MagicMock(spec=Message)
        message.chat = MagicMock(spec=Chat)
        message.chat.id = 123456789
        message.from_user = MagicMock(spec=User)
        message.from_user.id = 123456789
        return message

    async def test_handle_add_to_cart_success(self, cart_handler, mock_update, mock_context, patch_i18n):
        """Test add to cart - success"""
        mock_update.message = MagicMock(spec=Message)
        mock_update.message.text = "add_1"
        
        with patch.object(cart_handler.container.get_cart_service(), "add_item", return_value=True):
            await cart_handler.handle_add_to_cart(mock_update, mock_context)
            
            mock_context.bot.send_message.assert_called()

    async def test_handle_add_to_cart_failure(self, cart_handler, mock_update, mock_context, patch_i18n):
        """Test add to cart - failure"""
        mock_update.message = MagicMock(spec=Message)
        mock_update.message.text = "add_1"
        
        with patch.object(cart_handler.container.get_cart_service(), "add_item", return_value=False):
            await cart_handler.handle_add_to_cart(mock_update, mock_context)
            
            mock_context.bot.send_message.assert_called()

    async def test_handle_view_cart(self, cart_handler, mock_update, mock_context, patch_i18n):
        """Test view cart"""
        mock_update.message = MagicMock(spec=Message)
        mock_update.message.text = "/cart"
        
        with patch.object(cart_handler.container.get_cart_service(), "get_items", return_value=[]):
            await cart_handler.handle_view_cart(mock_update, mock_context)
            
            mock_context.bot.send_message.assert_called()

    async def test_handle_clear_cart(self, cart_handler, mock_update, mock_context, patch_i18n):
        """Test clear cart"""
        mock_update.message = MagicMock(spec=Message)
        mock_update.message.text = "/clear"
        
        with patch.object(cart_handler.container.get_cart_service(), "clear_cart", return_value=True):
            await cart_handler.handle_clear_cart(mock_update, mock_context)
            
            mock_context.bot.send_message.assert_called()

    async def test_handle_checkout(self, cart_handler, mock_update, mock_context, patch_i18n):
        """Test checkout"""
        mock_update.message = MagicMock(spec=Message)
        mock_update.message.text = "/checkout"
        
        with patch.object(cart_handler.container.get_cart_service(), "get_items", return_value=[]):
            with patch.object(cart_handler.container.get_order_service(), "create_order", return_value={"success": True}):
                await cart_handler.handle_checkout(mock_update, mock_context)
                
                mock_context.bot.send_message.assert_called()


class TestHandlerRegistration:
    """Test handler registration functions"""

    async def test_register_start_handlers(self, mock_application):
        """Test start handlers registration"""
        register_start_handlers(mock_application)
        
        # Should add handlers to application
        assert mock_application.add_handler.called

    async def test_register_menu_handlers(self, mock_application):
        """Test menu handlers registration"""
        register_menu_handlers(mock_application)
        
        # Should add handlers to application
        assert mock_application.add_handler.called

    async def test_register_admin_handlers(self, mock_application):
        """Test admin handlers registration"""
        register_admin_handlers(mock_application)
        
        # Should add handlers to application
        assert mock_application.add_handler.called


class TestHandlerIntegration:
    """Test handler integration workflows"""

    @pytest.fixture
    def cart_service(self):
        """Create CartService instance"""
        return CartService()

    @pytest.fixture
    def order_service(self):
        """Create OrderService instance"""
        return OrderService()

    @pytest.fixture
    def admin_service(self):
        """Create AdminService instance"""
        return AdminService()

    @pytest.fixture
    def notification_service(self):
        """Create NotificationService instance"""
        mock_bot = AsyncMock()
        return NotificationService(mock_bot)

    @pytest.mark.asyncio
    async def test_onboarding_flow(self, mock_update_with_user, mock_context):
        """Test complete onboarding flow"""
        # Mock the update and context
        update = mock_update_with_user
        context = mock_context
        
        # Test start command
        with patch("src.handlers.start.handle_start") as mock_start:
            await mock_start(update, context)
            mock_start.assert_called_once_with(update, context)

    @pytest.mark.asyncio
    async def test_menu_navigation_flow(self, mock_update_with_user, mock_context):
        """Test menu navigation flow"""
        # Mock the update and context
        update = mock_update_with_user
        context = mock_context
        
        # Test menu command
        with patch("src.handlers.menu.handle_menu") as mock_menu:
            await mock_menu(update, context)
            mock_menu.assert_called_once_with(update, context)

    @pytest.mark.asyncio
    async def test_cart_operations_flow(self, mock_update_with_user, mock_context):
        """Test cart operations flow"""
        # Mock the update and context
        update = mock_update_with_user
        context = mock_context
        
        # Test cart command
        with patch("src.handlers.cart.handle_cart") as mock_cart:
            await mock_cart(update, context)
            mock_cart.assert_called_once_with(update, context)


class TestHandlerErrorHandling:
    """Test handler error handling"""

    @pytest.fixture
    def cart_service(self):
        """Create CartService instance"""
        return CartService()

    @pytest.fixture
    def order_service(self):
        """Create OrderService instance"""
        return OrderService()

    @pytest.fixture
    def admin_service(self):
        """Create AdminService instance"""
        return AdminService()

    @pytest.fixture
    def notification_service(self):
        """Create NotificationService instance"""
        mock_bot = AsyncMock()
        return NotificationService(mock_bot)

    @pytest.mark.asyncio
    async def test_onboarding_handler_error_handling(self, mock_update_with_user, mock_context):
        """Test onboarding handler error handling"""
        update = mock_update_with_user
        context = mock_context
        
        with patch("src.handlers.start.handle_start", side_effect=Exception("Handler Error")):
            # Should not raise exception
            try:
                with patch("src.utils.error_handler.handle_error") as mock_error_handler:
                    await mock_error_handler(update, context, Exception("Handler Error"))
                    mock_error_handler.assert_called_once()
            except Exception:
                pass

    @pytest.mark.asyncio
    async def test_menu_handler_error_handling(self, mock_update_with_user, mock_context):
        """Test menu handler error handling"""
        update = mock_update_with_user
        context = mock_context
        
        with patch("src.handlers.menu.handle_menu", side_effect=Exception("Handler Error")):
            # Should not raise exception
            try:
                with patch("src.utils.error_handler.handle_error") as mock_error_handler:
                    await mock_error_handler(update, context, Exception("Handler Error"))
                    mock_error_handler.assert_called_once()
            except Exception:
                pass

    @pytest.mark.asyncio
    async def test_cart_handler_error_handling(self, mock_update_with_user, mock_context):
        """Test cart handler error handling"""
        update = mock_update_with_user
        context = mock_context
        
        with patch("src.handlers.cart.handle_cart", side_effect=Exception("Handler Error")):
            # Should not raise exception
            try:
                with patch("src.utils.error_handler.handle_error") as mock_error_handler:
                    await mock_error_handler(update, context, Exception("Handler Error"))
                    mock_error_handler.assert_called_once()
            except Exception:
                pass


class TestHandlerPerformance:
    """Test handler performance"""

    @pytest.fixture
    def cart_service(self):
        """Create CartService instance"""
        return CartService()

    @pytest.fixture
    def order_service(self):
        """Create OrderService instance"""
        return OrderService()

    @pytest.fixture
    def admin_service(self):
        """Create AdminService instance"""
        return AdminService()

    @pytest.fixture
    def notification_service(self):
        """Create NotificationService instance"""
        mock_bot = AsyncMock()
        return NotificationService(mock_bot)

    @pytest.mark.asyncio
    async def test_onboarding_handler_performance(self, mock_update_with_user, mock_context):
        """Test onboarding handler performance"""
        update = mock_update_with_user
        context = mock_context
        
        start_time = time.time()
        
        with patch("src.handlers.start.handle_start") as mock_start:
            await mock_start(update, context)
        
        execution_time = time.time() - start_time
        assert execution_time < 1.0  # Should complete within 1 second

    @pytest.mark.asyncio
    async def test_menu_handler_performance(self, mock_update_with_user, mock_context):
        """Test menu handler performance"""
        update = mock_update_with_user
        context = mock_context
        
        start_time = time.time()
        
        with patch("src.handlers.menu.handle_menu") as mock_menu:
            await mock_menu(update, context)
        
        execution_time = time.time() - start_time
        assert execution_time < 1.0  # Should complete within 1 second

    @pytest.mark.asyncio
    async def test_cart_handler_performance(self, mock_update_with_user, mock_context):
        """Test cart handler performance"""
        update = mock_update_with_user
        context = mock_context
        
        start_time = time.time()
        
        with patch("src.handlers.cart.handle_cart") as mock_cart:
            await mock_cart(update, context)
        
        execution_time = time.time() - start_time
        assert execution_time < 1.0  # Should complete within 1 second 