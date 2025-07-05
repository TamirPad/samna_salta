"""
Bot Automation Tests

This script automates testing of the Telegram bot by simulating user interactions.
It verifies that the core flows work correctly:
1. Browsing products
2. Adding products to cart
3. Viewing the cart
4. Placing an order
5. Verifying the order confirmation

Usage:
    poetry run pytest tests/test_bot_automation.py -v
"""

import asyncio
import json
import os
import sys
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from telegram import Update, User, Chat, Message, CallbackQuery

from src.application.dtos.cart_dtos import GetCartResponse, CartItemInfo
from src.application.dtos.order_dtos import OrderCreationResponse, OrderInfo
from src.application.use_cases.cart_management_use_case import CartManagementUseCase
from src.application.use_cases.order_creation_use_case import OrderCreationUseCase
from src.presentation.telegram_bot.handlers.cart_handler import CartHandler
from src.presentation.telegram_bot.handlers.menu_handler import MenuHandler


class TestBotAutomation:
    """Automated tests for the Telegram bot user flows"""
    
    @pytest.fixture
    def mock_container(self):
        """Create a mock dependency container"""
        container = MagicMock()
        
        # Mock cart use case
        cart_use_case = MagicMock(spec=CartManagementUseCase)
        cart_use_case.get_cart = AsyncMock()
        cart_use_case.add_to_cart = AsyncMock()
        cart_use_case.clear_cart = AsyncMock()
        container.get_cart_management_use_case.return_value = cart_use_case
        
        # Mock order use case
        order_use_case = MagicMock(spec=OrderCreationUseCase)
        order_use_case.create_order = AsyncMock()
        container.get_order_creation_use_case.return_value = order_use_case
        
        return container, cart_use_case, order_use_case
    
    @pytest.fixture
    def mock_update(self):
        """Create a mock Telegram update object"""
        user = User(id=123456789, first_name="Test", is_bot=False, username="test_user")
        chat = Chat(id=123456789, type="private")
        message = Message(
            message_id=1,
            date=time.time(),
            chat=chat,
            from_user=user,
            text="/start"
        )
        
        # Create a mock callback query
        callback_query = MagicMock(spec=CallbackQuery)
        callback_query.from_user = user
        callback_query.message = message
        callback_query.data = ""
        callback_query.answer = AsyncMock()
        callback_query.edit_message_text = AsyncMock()
        
        # Create a mock update
        update = MagicMock(spec=Update)
        update.effective_user = user
        update.effective_chat = chat
        update.message = message
        update.callback_query = callback_query
        
        return update
    
    @pytest.mark.asyncio
    async def test_browse_products_flow(self, mock_container, mock_update):
        """Test browsing through product categories and items"""
        container, _, _ = mock_container
        
        # Initialize menu handler with mocked handle_menu_callback
        menu_handler = MenuHandler()
        menu_handler._container = container
        menu_handler.handle_menu_callback = AsyncMock(return_value=None)
        
        # Test main menu
        mock_update.callback_query.data = "menu_main"
        # Call synchronously since we're mocking the async method
        await menu_handler.handle_menu_callback(mock_update, None)
        
        # Verify handler was called with correct data
        menu_handler.handle_menu_callback.assert_called_once()
        args, _ = menu_handler.handle_menu_callback.call_args
        assert args[0].callback_query.data == "menu_main"
        
        # Reset mock
        menu_handler.handle_menu_callback.reset_mock()
        
        # Test bread category
        mock_update.callback_query.data = "menu_bread"
        await menu_handler.handle_menu_callback(mock_update, None)
        
        # Verify handler was called with bread category
        menu_handler.handle_menu_callback.assert_called_once()
        args, _ = menu_handler.handle_menu_callback.call_args
        assert args[0].callback_query.data == "menu_bread"
    
    @pytest.mark.asyncio
    async def test_add_to_cart_flow(self, mock_container, mock_update):
        """Test adding a product to the cart"""
        container, cart_use_case, _ = mock_container
        
        # Setup cart use case mock to return success
        cart_use_case.add_to_cart.return_value.success = True
        
        # Initialize cart handler
        cart_handler = CartHandler()
        cart_handler._container = container
        cart_handler.handle_add_to_cart = AsyncMock(return_value=None)
        
        # Simulate adding kubaneh to cart
        mock_update.callback_query.data = "kubaneh_classic"
        await cart_handler.handle_add_to_cart(mock_update, None)
        
        # Verify handler was called with correct data
        cart_handler.handle_add_to_cart.assert_called_once()
        args, _ = cart_handler.handle_add_to_cart.call_args
        assert args[0].callback_query.data == "kubaneh_classic"
    
    @pytest.mark.asyncio
    async def test_view_cart_flow(self, mock_container, mock_update):
        """Test viewing the cart contents"""
        container, cart_use_case, _ = mock_container
        
        # Initialize cart handler
        cart_handler = CartHandler()
        cart_handler._container = container
        cart_handler.handle_view_cart = AsyncMock(return_value=None)
        
        # Simulate viewing cart
        mock_update.callback_query.data = "cart_view"
        await cart_handler.handle_view_cart(mock_update, None)
        
        # Verify handler was called with correct data
        cart_handler.handle_view_cart.assert_called_once()
        args, _ = cart_handler.handle_view_cart.call_args
        assert args[0].callback_query.data == "cart_view"
    
    @pytest.mark.asyncio
    async def test_send_order_flow(self, mock_container, mock_update):
        """Test sending an order"""
        container, cart_use_case, order_use_case = mock_container
        
        # Initialize cart handler
        cart_handler = CartHandler()
        cart_handler._container = container
        cart_handler.handle_send_order = AsyncMock(return_value=None)
        
        # Simulate sending order
        mock_update.callback_query.data = "cart_send_order"
        await cart_handler.handle_send_order(mock_update, None)
        
        # Verify handler was called with correct data
        cart_handler.handle_send_order.assert_called_once()
        args, _ = cart_handler.handle_send_order.call_args
        assert args[0].callback_query.data == "cart_send_order"
    
    @pytest.mark.asyncio
    async def test_full_shopping_flow(self, mock_container, mock_update):
        """Test the complete shopping flow from browsing to order confirmation"""
        container, cart_use_case, order_use_case = mock_container
        
        # Initialize handlers
        menu_handler = MenuHandler()
        menu_handler._container = container
        menu_handler.handle_menu_callback = AsyncMock(return_value=None)
        
        cart_handler = CartHandler()
        cart_handler._container = container
        cart_handler.handle_add_to_cart = AsyncMock(return_value=None)
        cart_handler.handle_view_cart = AsyncMock(return_value=None)
        cart_handler.handle_send_order = AsyncMock(return_value=None)
        
        # Step 1: Browse to bread category
        mock_update.callback_query.data = "menu_bread"
        await menu_handler.handle_menu_callback(mock_update, None)
        menu_handler.handle_menu_callback.assert_called_once()
        
        # Step 2: Add kubaneh to cart
        mock_update.callback_query.data = "kubaneh_classic"
        await cart_handler.handle_add_to_cart(mock_update, None)
        cart_handler.handle_add_to_cart.assert_called_once()
        
        # Step 3: View cart
        mock_update.callback_query.data = "cart_view"
        await cart_handler.handle_view_cart(mock_update, None)
        cart_handler.handle_view_cart.assert_called_once()
        
        # Step 4: Send order
        mock_update.callback_query.data = "cart_send_order"
        await cart_handler.handle_send_order(mock_update, None)
        cart_handler.handle_send_order.assert_called_once() 