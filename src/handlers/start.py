"""
Onboarding Handler for the Telegram bot.
"""

import logging

from telegram import Update, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from src.container import get_container
from src.utils.error_handler import (
    BusinessLogicError,
    ValidationError,
    error_handler,
)
from src.keyboards.menu_keyboards import (
    get_delivery_method_keyboard,
    get_main_menu_keyboard,
)
from src.states import (
    END,
    ONBOARDING_DELIVERY_ADDRESS,
    ONBOARDING_DELIVERY_METHOD,
    ONBOARDING_LANGUAGE,
    ONBOARDING_NAME,
    ONBOARDING_PHONE,
)
from src.utils.i18n import i18n
from src.utils.constants import ErrorMessages

logger = logging.getLogger(__name__)


class OnboardingHandler:
    """Onboarding handler for new customers"""

    def __init__(self):
        self.container = get_container()
        self.cart_service = self.container.get_cart_service()
        self.logger = logging.getLogger(self.__class__.__name__)

    async def start_command(self, update: Update, _: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle /start command - begin onboarding process"""
        user = update.effective_user

        self.logger.info(
            "Start command received from user %s (%s)", user.id, user.username
        )

        try:
            # Check if user is already registered
            existing_customer = self.cart_service.get_customer(user.id)

            if existing_customer:
                # Check if customer has complete profile data
                if self._is_customer_profile_complete(existing_customer):
                    # Welcome back existing customer with main page
                    user_id = user.id
                    welcome_message = (
                        f"🇾🇪 <b>{i18n.get_text('WELCOME', user_id=user_id)}</b> 🇾🇪\n\n"
                        f"👋 <b>{i18n.get_text('WELCOME_BACK', user_id=user_id).format(name=existing_customer.name)}</b>\n\n"
                        f"{i18n.get_text('WHAT_TO_ORDER_TODAY', user_id=user_id)}"
                    )
                    await update.message.reply_text(
                        welcome_message,
                        reply_markup=self._get_main_page_keyboard(user_id),
                        parse_mode="HTML"
                    )
                    return END
                else:
                    # Customer exists but profile is incomplete - restart onboarding
                    self.logger.info("Customer %s has incomplete profile, restarting onboarding", user.id)
                    await update.message.reply_text(
                        i18n.get_text("PROFILE_INCOMPLETE", user_id=user.id) + "\n\n" +
                        i18n.get_text("PLEASE_COMPLETE_PROFILE", user_id=user.id),
                        parse_mode="HTML"
                    )
                    # Continue to language selection

            # Start onboarding for new customer or incomplete profile with language selection
            user_id = user.id
            await update.message.reply_text(
                i18n.get_text("WELCOME_NEW_USER", user_id=user_id) + "\n\n" +
                i18n.get_text("WELCOME_HELP_MESSAGE", user_id=user_id) + "\n\n" +
                i18n.get_text("SELECT_LANGUAGE_PROMPT", user_id=user_id),
                reply_markup=self._get_language_selection_keyboard(),
                parse_mode="HTML"
            )
            return ONBOARDING_LANGUAGE

        except Exception as e:
            self.logger.error("Error in start_command: %s", e, exc_info=True)
            user_id = update.effective_user.id
            await self._send_error_message(
                update, i18n.get_text("ERROR_TRY_START_AGAIN", user_id=user_id)
            )
            return END

    def _is_customer_profile_complete(self, customer) -> bool:
        """Check if customer has complete profile data"""
        return (
            customer and
            customer.name and len(customer.name.strip()) >= 2 and
            customer.phone and len(customer.phone.strip()) >= 8
        )

    async def handle_language_selection(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """Handle language selection during onboarding"""
        try:
            query = update.callback_query
            await query.answer()
            
            user_id = update.effective_user.id
            data = query.data
            
            if data == "language_en":
                # Store language preference in context for later use
                context.user_data["selected_language"] = "en"
                # Also update the language manager cache for immediate use
                from src.utils.language_manager import language_manager
                language_manager._user_languages[user_id] = "en"
                
                await query.edit_message_text(
                    i18n.get_text("LANGUAGE_CHANGED", language="en") + "\n\n" +
                    i18n.get_text("PLEASE_ENTER_NAME", language="en"),
                    parse_mode="HTML"
                )
                return ONBOARDING_NAME
            elif data == "language_he":
                # Store language preference in context for later use
                context.user_data["selected_language"] = "he"
                # Also update the language manager cache for immediate use
                from src.utils.language_manager import language_manager
                language_manager._user_languages[user_id] = "he"
                
                await query.edit_message_text(
                    i18n.get_text("LANGUAGE_CHANGED", language="he") + "\n\n" +
                    i18n.get_text("PLEASE_ENTER_NAME", language="he"),
                    parse_mode="HTML"
                )
                return ONBOARDING_NAME
            else:
                # Invalid language selection
                await query.edit_message_text(
                    i18n.get_text("INVALID_CHOICE", user_id=user_id) + "\n\n" +
                    i18n.get_text("SELECT_LANGUAGE_PROMPT", user_id=user_id),
                    reply_markup=self._get_language_selection_keyboard(),
                    parse_mode="HTML"
                )
                return ONBOARDING_LANGUAGE

        except Exception as e:
            self.logger.error("Error in handle_language_selection: %s", e, exc_info=True)
            await self._send_error_message(update, i18n.get_text("ERROR_TRY_START_AGAIN", user_id=user_id))
            return END

    async def handle_name(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """Handle customer name input with validation"""
        try:
            name = update.message.text.strip()

            user_id = update.effective_user.id
            
            # Get user's language preference from context or language manager
            from src.utils.language_manager import language_manager
            user_language = context.user_data.get("selected_language") or language_manager.get_user_language(user_id)
            
            # Basic validation
            if len(name) < 2:
                await update.message.reply_text(
                    i18n.get_text("NAME_TOO_SHORT", language=user_language),
                    parse_mode="HTML"
                )
                return ONBOARDING_NAME

            # Store name in context
            context.user_data["full_name"] = name

            await update.message.reply_text(
                i18n.get_text("NICE_TO_MEET", language=user_language).format(name=name) + "\n\n" +
                i18n.get_text("PLEASE_SHARE_PHONE", language=user_language),
                parse_mode="HTML"
            )
            return ONBOARDING_PHONE

        except Exception as e:
            self.logger.error("Error in handle_name: %s", e, exc_info=True)
            await self._send_error_message(update, i18n.get_text("ERROR_TRY_START_AGAIN", language=user_language))
            return END

    async def handle_phone(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int | None:
        """Handle customer phone number input with validation"""
        next_state = None
        try:
            phone = update.message.text.strip()
            user_id = update.effective_user.id
            full_name = context.user_data.get("full_name")

            if not full_name:
                await self._send_error_message(
                    update, i18n.get_text("SESSION_EXPIRED", user_id=user_id)
                )
                return END

            # Get user's language preference from context or language manager
            from src.utils.language_manager import language_manager
            user_language = context.user_data.get("selected_language") or language_manager.get_user_language(user_id)

            # Validate customer data
            validation = self.cart_service.validate_customer_data(full_name, phone)
            if not validation["valid"]:
                error_msg = ", ".join(validation["errors"])
                await update.message.reply_text(
                    i18n.get_text("VALIDATION_ERROR", language=user_language).format(error=error_msg) + "\n\n" + i18n.get_text("PLEASE_TRY_AGAIN", language=user_language),
                    parse_mode="HTML"
                )
                return ONBOARDING_PHONE
            
            # Register customer
            result = self.cart_service.register_customer(user_id, full_name, phone, user_language)
            
            if not result["success"]:
                await update.message.reply_text(
                    i18n.get_text("VALIDATION_ERROR", language=user_language).format(error=result["error"]) + "\n\n" + i18n.get_text("PLEASE_TRY_AGAIN", language=user_language),
                    parse_mode="HTML"
                )
                return ONBOARDING_PHONE

            # Store customer data in context
            context.user_data["customer"] = result["customer"]
            context.user_data["phone_number"] = phone

            if result["is_returning"]:
                await update.message.reply_text(
                    i18n.get_text("WELCOME_BACK_UPDATED", language=user_language).format(name=result["customer"].name) + "\n\n" +
                    i18n.get_text("INFO_UPDATED", language=user_language) + "\n\n" +
                    i18n.get_text("WELCOME", language=user_language) + "\n\n" +
                    i18n.get_text("WHAT_TO_ORDER_TODAY", language=user_language),
                    reply_markup=self._get_main_page_keyboard(user_id),
                    parse_mode="HTML"
                )
                next_state = END
            else:
                await update.message.reply_text(
                    i18n.get_text("THANK_YOU_PHONE", language=user_language).format(name=result["customer"].name) + "\n\n" +
                    i18n.get_text("PLEASE_ENTER_DELIVERY_ADDRESS_ONBOARDING", language=user_language) + "\n\n" +
                    i18n.get_text("DELIVERY_ADDRESS_ONBOARDING_HELP", language=user_language),
                    parse_mode="HTML"
                )
                next_state = ONBOARDING_DELIVERY_ADDRESS

        except Exception as e:
            self.logger.error("Error in handle_phone: %s", e, exc_info=True)
            await update.message.reply_text(
                i18n.get_text("VALIDATION_ERROR", language=user_language).format(error=str(e)) + "\n\n" + i18n.get_text("ENTER_VALID_PHONE", language=user_language)
            )
            next_state = ONBOARDING_PHONE

        return next_state

    async def handle_delivery_method(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """Handle delivery method selection (no longer used in onboarding)"""
        # This method is kept for backward compatibility but not used in onboarding
        return END

    async def handle_delivery_address(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """Handle delivery address input during onboarding"""
        try:
            address = update.message.text.strip()
            customer = context.user_data.get("customer")

            if not customer:
                await self._send_error_message(update, i18n.get_text("SESSION_EXPIRED", user_id=user_id))
                return END

            user_id = update.effective_user.id
            
            # Validate address
            if len(address) < 5:
                await update.message.reply_text(
                    i18n.get_text("ADDRESS_TOO_SHORT", user_id=user_id),
                    parse_mode="HTML"
                )
                return ONBOARDING_DELIVERY_ADDRESS

            # Update customer with delivery address
            self.cart_service.update_customer_delivery_address(
                customer.telegram_id,
                address
            )

            user_id = update.effective_user.id
            await update.message.reply_text(
                i18n.get_text("REGISTRATION_COMPLETE", user_id=user_id) + "\n\n" +
                i18n.get_text("DELIVERY_ADDRESS_SAVED_ONBOARDING", user_id=user_id).format(address=address) + "\n\n" +
                i18n.get_text("WELCOME", user_id=user_id) + "\n\n" +
                i18n.get_text("WHAT_TO_ORDER_TODAY", user_id=user_id),
                reply_markup=self._get_main_page_keyboard(user_id),
                parse_mode="HTML"
            )
            return END

        except Exception as e:
            self.logger.error("Error in handle_delivery_address: %s", e, exc_info=True)
            await self._send_error_message(update, i18n.get_text("ERROR_TRY_START_AGAIN", user_id=user_id))
            return END

    async def cancel_onboarding(
        self, update: Update, _: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """Cancel onboarding process"""
        user_id = update.effective_user.id
        await update.message.reply_text(
            i18n.get_text("ONBOARDING_CANCELLED", user_id=user_id),
            parse_mode="HTML"
        )
        return END

    @error_handler("unknown_command")
    async def handle_unknown_command(
        self, update: Update, _: ContextTypes.DEFAULT_TYPE
    ):
        """Handle unknown commands during onboarding"""
        await update.message.reply_text(
            i18n.get_text("UNKNOWN_COMMAND_ONBOARDING"),
            parse_mode="HTML"
        )

    @error_handler("unknown_message")
    async def handle_unknown_message(
        self, update: Update, _: ContextTypes.DEFAULT_TYPE
    ):
        """Handle unknown messages during onboarding"""
        await update.message.reply_text(
            i18n.get_text("UNKNOWN_MESSAGE_ONBOARDING"),
            parse_mode="HTML"
        )

    async def _send_error_message(self, update, message: str):
        """Send error message to user"""
        try:
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    message, parse_mode="HTML"
                )
            else:
                await update.message.reply_text(message, parse_mode="HTML")
        except Exception as e:
            self.logger.error("Failed to send error message: %s", e)

    def _get_language_selection_keyboard(self):
        """Get language selection keyboard for onboarding"""
        keyboard = [
            [
                InlineKeyboardButton("🇺🇸 English", callback_data="language_en"),
                InlineKeyboardButton("🇮🇱 עברית", callback_data="language_he"),
            ],
        ]
        return InlineKeyboardMarkup(keyboard)

    def _get_main_page_keyboard(self, user_id: int = None):
        """Get main page keyboard with Menu, My Info, and Order tracking buttons"""
        keyboard = [
            [
                InlineKeyboardButton(i18n.get_text("BUTTON_MENU", user_id=user_id), callback_data="main_menu"),
                InlineKeyboardButton(i18n.get_text("BUTTON_MY_INFO", user_id=user_id), callback_data="main_my_info"),
            ],
            [
                InlineKeyboardButton(i18n.get_text("BUTTON_ACTIVE_ORDERS", user_id=user_id), callback_data="main_active_orders"),
                InlineKeyboardButton(i18n.get_text("BUTTON_COMPLETED_ORDERS", user_id=user_id), callback_data="main_completed_orders"),
            ],
        ]
        return InlineKeyboardMarkup(keyboard)

    async def handle_main_page_callback(self, update: Update, _: ContextTypes.DEFAULT_TYPE):
        """Handle main page callbacks (My Info, Menu, Language)"""
        query = update.callback_query
        await query.answer()

        data = query.data
        user_id = update.effective_user.id

        self.logger.info("🏠 MAIN PAGE CALLBACK: User %s clicked: %s", user_id, data)

        try:
            if data == "main_my_info":
                await self._show_my_info(query)
            elif data == "main_menu":
                await self._show_menu(query)
            elif data == "main_page":
                await self._show_main_page(query)
            elif data == "main_active_orders":
                await self._show_customer_active_orders(query)
            elif data == "main_completed_orders":
                await self._show_customer_completed_orders(query)
            elif data == "language_selection":
                # Route language selection to My Info handler
                await self._show_my_info(query)
            elif data.startswith("language_"):
                # Handle language change from My Info
                await self._handle_language_change_from_my_info(query)
            elif data.startswith("customer_order_"):
                # Handle customer order details
                await self._show_customer_order_details(query)
            else:
                self.logger.warning("⚠️ UNKNOWN MAIN PAGE CALLBACK: %s", data)

        except Exception as e:
            self.logger.error("Error in handle_main_page_callback: %s", e)
            await query.edit_message_text("❌ An error occurred. Please try again.")

    async def _show_my_info(self, query: CallbackQuery):
        """Show user information"""
        try:
            user_id = query.from_user.id
            data = query.data
            
            # Handle language selection from My Info
            if data == "language_selection":
                await self._handle_language_selection_from_my_info(query)
                return
            
            customer = self.cart_service.get_customer(user_id)
            
            if customer:
                info_text = (
                    f"👤 <b>{i18n.get_text('MY_INFO_TITLE', user_id=user_id)}</b>\n\n"
                    f"<b>{i18n.get_text('NAME_FIELD', user_id=user_id)}</b> {customer.name or '🤷'}\n"
                    f"<b>{i18n.get_text('PHONE_FIELD', user_id=user_id)}</b> {customer.phone or '📞'}\n"
                    f"<b>{i18n.get_text('ADDRESS_FIELD', user_id=user_id)}</b> {customer.delivery_address or i18n.get_text('NOT_SET', user_id=user_id)}\n\n"
                    f"{i18n.get_text('CONTACT_SUPPORT_FOR_UPDATES', user_id=user_id)}"
                )
            else:
                info_text = i18n.get_text("USER_INFO_NOT_FOUND", user_id=user_id)

            await query.edit_message_text(
                info_text,
                reply_markup=self._get_my_info_keyboard(user_id),
                parse_mode="HTML"
            )

        except Exception as e:
            self.logger.error("Error showing my info: %s", e)
            await query.edit_message_text(
                i18n.get_text("UNEXPECTED_ERROR", user_id=user_id),
                reply_markup=self._get_back_to_main_keyboard(user_id)
            )

    async def _show_menu(self, query: CallbackQuery):
        """Show the food menu"""
        try:
            from src.keyboards.menu_keyboards import get_dynamic_main_menu_keyboard
            user_id = query.from_user.id
            
            await query.edit_message_text(
                i18n.get_text("MENU_PROMPT", user_id=user_id),
                reply_markup=get_dynamic_main_menu_keyboard(user_id),
                parse_mode="HTML"
            )

        except Exception as e:
            self.logger.error("Error showing menu: %s", e)
            await query.edit_message_text(
                "❌ Error loading menu. Please try again.",
                reply_markup=self._get_back_to_main_keyboard()
            )

    async def _show_main_page(self, query: CallbackQuery):
        """Show the main page with welcome message"""
        try:
            user_id = query.from_user.id
            customer = self.cart_service.get_customer(user_id)
            
            if customer:
                welcome_message = (
                    f"🇾🇪 <b>{i18n.get_text('WELCOME', user_id=user_id)}</b> 🇾🇪\n\n"
                    f"👋 <b>{i18n.get_text('WELCOME_BACK', user_id=user_id).format(name=customer.name)}</b>\n\n"
                    f"{i18n.get_text('WHAT_TO_ORDER_TODAY', user_id=user_id)}"
                )
            else:
                welcome_message = (
                    f"🇾🇪 <b>{i18n.get_text('WELCOME', user_id=user_id)}</b> 🇾🇪\n\n"
                    f"{i18n.get_text('WHAT_TO_ORDER_TODAY', user_id=user_id)}"
                )

            await query.edit_message_text(
                welcome_message,
                reply_markup=self._get_main_page_keyboard(user_id),
                parse_mode="HTML"
            )

        except Exception as e:
            self.logger.error("Error showing main page: %s", e)
            await query.edit_message_text(
                i18n.get_text("UNEXPECTED_ERROR", user_id=user_id),
                reply_markup=self._get_main_page_keyboard(user_id)
            )

    def _get_my_info_keyboard(self, user_id: int):
        """Get My Info keyboard with language selection"""
        from src.utils.language_manager import language_manager
        
        current_lang = language_manager.get_user_language(user_id)
        
        keyboard = [
            [InlineKeyboardButton(i18n.get_text("LANGUAGE_BUTTON", user_id=user_id), callback_data="language_selection")],
            [InlineKeyboardButton(i18n.get_text("BACK_TO_MAIN", user_id=user_id), callback_data="main_page")],
        ]
        return InlineKeyboardMarkup(keyboard)

    def _get_back_to_main_keyboard(self, user_id: int = None):
        """Get keyboard to go back to main page"""
        keyboard = [
            [InlineKeyboardButton(i18n.get_text("BACK_TO_MAIN", user_id=user_id), callback_data="main_page")],
        ]
        return InlineKeyboardMarkup(keyboard)

    async def _handle_language_selection_from_my_info(self, query: CallbackQuery):
        """Handle language selection from My Info section"""
        try:
            user_id = query.from_user.id
            
            # Show language selection keyboard
            await query.edit_message_text(
                i18n.get_text("SELECT_LANGUAGE_PROMPT", user_id=user_id),
                reply_markup=self._get_language_selection_keyboard(),
                parse_mode="HTML"
            )
                
        except Exception as e:
            self.logger.error("Error handling language selection from my info: %s", e)
            await query.edit_message_text(
                i18n.get_text("UNEXPECTED_ERROR", user_id=user_id),
                reply_markup=self._get_back_to_main_keyboard(user_id)
            )

    async def _handle_language_selection(self, query: CallbackQuery):
        """Handle language selection"""
        try:
            user_id = query.from_user.id
            data = query.data
            
            if data == "language_selection":
                # Show language selection keyboard
                from src.keyboards.language_keyboards import get_language_selection_keyboard
                
                await query.edit_message_text(
                    i18n.get_text("SELECT_LANGUAGE_PROMPT", user_id=user_id),
                    reply_markup=get_language_selection_keyboard(user_id),
                    parse_mode="HTML"
                )
                
            elif data.startswith("language_"):
                # Handle language change
                from src.utils.language_manager import language_manager
                
                language = data.split("_")[1]  # language_en -> en
                language_manager.set_user_language(user_id, language)
                
                # Show success message in new language and return to main page
                success_text = i18n.get_text("LANGUAGE_CHANGED", user_id=user_id)
                await query.edit_message_text(
                    success_text,
                    reply_markup=self._get_main_page_keyboard(user_id),
                    parse_mode="HTML"
                )
                
        except Exception as e:
            self.logger.error("Error handling language selection: %s", e)
            await query.edit_message_text(
                i18n.get_text("UNEXPECTED_ERROR", user_id=user_id),
                reply_markup=self._get_back_to_main_keyboard(user_id)
            )

    async def _handle_language_change_from_my_info(self, query: CallbackQuery):
        """Handle language change from My Info section"""
        try:
            user_id = query.from_user.id
            data = query.data
            
            # Handle language change
            from src.utils.language_manager import language_manager
            
            language = data.split("_")[1]  # language_en -> en
            language_manager.set_user_language(user_id, language)
            
            # Show success message in new language and return to My Info
            success_text = i18n.get_text("LANGUAGE_CHANGED", language=language)
            await query.edit_message_text(
                success_text,
                reply_markup=self._get_my_info_keyboard(user_id),
                parse_mode="HTML"
            )
                
        except Exception as e:
            self.logger.error("Error handling language change from my info: %s", e)
            await query.edit_message_text(
                i18n.get_text("UNEXPECTED_ERROR", user_id=user_id),
                reply_markup=self._get_back_to_main_keyboard(user_id)
            )

    async def _show_customer_active_orders(self, query: CallbackQuery):
        """Show customer's active orders"""
        try:
            user_id = query.from_user.id
            customer_order_service = self.container.get_customer_order_service()
            
            orders = customer_order_service.get_customer_active_orders(user_id)
            
            if not orders:
                text = (
                    i18n.get_text("CUSTOMER_ACTIVE_ORDERS_TITLE", user_id=user_id) + "\n\n" + 
                    i18n.get_text("CUSTOMER_NO_ACTIVE_ORDERS", user_id=user_id)
                )
                keyboard = [
                    [InlineKeyboardButton(i18n.get_text("BACK_TO_MAIN", user_id=user_id), callback_data="main_page")]
                ]
            else:
                text = f"{i18n.get_text('CUSTOMER_ACTIVE_ORDERS_TITLE', user_id=user_id)} ({len(orders)})"
                keyboard = []
                
                for order in orders:
                    order_summary = (
                        f"#{order['order_id']} - {order['status'].capitalize()} - "
                        f"₪{order['total']:.2f}"
                    )
                    keyboard.append([
                        InlineKeyboardButton(
                            order_summary,
                            callback_data=f"customer_order_{order['order_id']}"
                        )
                    ])
                
                keyboard.append([
                    InlineKeyboardButton(i18n.get_text("BACK_TO_MAIN", user_id=user_id), callback_data="main_page")
                ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                text, parse_mode="HTML", reply_markup=reply_markup
            )
            
        except Exception as e:
            self.logger.error("Error showing customer active orders: %s", e)
            await query.edit_message_text(
                i18n.get_text("CUSTOMER_ORDERS_ERROR", user_id=user_id),
                reply_markup=self._get_back_to_main_keyboard(user_id)
            )

    async def _show_customer_completed_orders(self, query: CallbackQuery):
        """Show customer's completed orders"""
        try:
            user_id = query.from_user.id
            customer_order_service = self.container.get_customer_order_service()
            
            orders = customer_order_service.get_customer_completed_orders(user_id)
            
            if not orders:
                text = (
                    i18n.get_text("CUSTOMER_COMPLETED_ORDERS_TITLE", user_id=user_id) + "\n\n" + 
                    i18n.get_text("CUSTOMER_NO_COMPLETED_ORDERS", user_id=user_id)
                )
                keyboard = [
                    [InlineKeyboardButton(i18n.get_text("BACK_TO_MAIN", user_id=user_id), callback_data="main_page")]
                ]
            else:
                text = f"{i18n.get_text('CUSTOMER_COMPLETED_ORDERS_TITLE', user_id=user_id)} ({len(orders)})"
                keyboard = []
                
                for order in orders:
                    order_summary = (
                        f"#{order['order_id']} - {order['status'].capitalize()} - "
                        f"₪{order['total']:.2f}"
                    )
                    keyboard.append([
                        InlineKeyboardButton(
                            order_summary,
                            callback_data=f"customer_order_{order['order_id']}"
                        )
                    ])
                
                keyboard.append([
                    InlineKeyboardButton(i18n.get_text("BACK_TO_MAIN", user_id=user_id), callback_data="main_page")
                ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                text, parse_mode="HTML", reply_markup=reply_markup
            )
            
        except Exception as e:
            self.logger.error("Error showing customer completed orders: %s", e)
            await query.edit_message_text(
                i18n.get_text("CUSTOMER_ORDERS_ERROR", user_id=user_id),
                reply_markup=self._get_back_to_main_keyboard(user_id)
            )

    async def _show_customer_order_details(self, query: CallbackQuery):
        """Show details for a specific customer order"""
        try:
            user_id = query.from_user.id
            data = query.data
            
            # Extract order ID from callback data
            order_id = int(data.split("_")[-1])
            
            customer_order_service = self.container.get_customer_order_service()
            order = customer_order_service.get_customer_order_by_id(order_id, user_id)
            
            if not order:
                await query.edit_message_text(
                    i18n.get_text("CUSTOMER_ORDER_NOT_FOUND", user_id=user_id),
                    reply_markup=self._get_back_to_main_keyboard(user_id)
                )
                return
            
            # Format order details
            details = [
                i18n.get_text("CUSTOMER_ORDER_DETAILS_TITLE", user_id=user_id).format(number=order["order_number"]),
                i18n.get_text("CUSTOMER_ORDER_STATUS", user_id=user_id).format(status=order["status"].capitalize()),
                i18n.get_text("CUSTOMER_ORDER_TOTAL", user_id=user_id).format(total=order["total"]),
                i18n.get_text("CUSTOMER_ORDER_DATE", user_id=user_id).format(
                    date=order["created_at"].strftime('%Y-%m-%d %H:%M') if order["created_at"] else "Unknown"
                ),
                i18n.get_text("CUSTOMER_ORDER_DELIVERY_METHOD", user_id=user_id).format(
                    method=order["delivery_method"].capitalize() if order["delivery_method"] else "Unknown"
                ),
            ]
            
            if order.get("delivery_address"):
                details.append(
                    i18n.get_text("CUSTOMER_ORDER_DELIVERY_ADDRESS", user_id=user_id).format(
                        address=order["delivery_address"]
                    )
                )
            
            if order.get("items"):
                details.append(f"\n{i18n.get_text('CUSTOMER_ORDER_ITEMS', user_id=user_id)}")
                for item in order["items"]:
                    from src.utils.helpers import translate_product_name
                    translated_name = translate_product_name(item["product_name"], item.get("options", {}), user_id)
                    details.append(
                        i18n.get_text("CUSTOMER_ORDER_ITEM_LINE", user_id=user_id).format(
                            name=translated_name,
                            quantity=item["quantity"],
                            price=item["total_price"]
                        )
                    )
            
            text = "\n".join(details)
            
            keyboard = [
                [InlineKeyboardButton(i18n.get_text("BACK_TO_MAIN", user_id=user_id), callback_data="main_page")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                text, parse_mode="HTML", reply_markup=reply_markup
            )
            
        except Exception as e:
            self.logger.error("Error showing customer order details: %s", e)
            await query.edit_message_text(
                i18n.get_text("CUSTOMER_ORDERS_ERROR", user_id=user_id),
                reply_markup=self._get_back_to_main_keyboard(user_id)
            )


def register_start_handlers(application: Application):
    """Register onboarding conversation handler"""
    handler = OnboardingHandler()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", handler.start_command)],
        states={
            ONBOARDING_LANGUAGE: [
                CallbackQueryHandler(handler.handle_language_selection, pattern="^language_(en|he)$"),
                CommandHandler("cancel", handler.cancel_onboarding),
            ],
            ONBOARDING_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handler.handle_name),
                CommandHandler("cancel", handler.cancel_onboarding),
            ],
            ONBOARDING_PHONE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handler.handle_phone),
                CommandHandler("cancel", handler.cancel_onboarding),
            ],
            ONBOARDING_DELIVERY_ADDRESS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handler.handle_delivery_address),
                CommandHandler("cancel", handler.cancel_onboarding),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", handler.cancel_onboarding),
            handler.handle_unknown_command,
            handler.handle_unknown_message,
        ],
        per_message=False,
    )

    application.add_handler(conv_handler)


# Handler function for direct registration
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start handler for direct registration"""
    handler = OnboardingHandler()
    return await handler.start_command(update, context)
