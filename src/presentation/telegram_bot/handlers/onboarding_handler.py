"""
Clean Architecture Onboarding Handler

Handles customer onboarding flow using use cases and dependency injection.
"""

import logging

from telegram import Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from ....application.use_cases.customer_registration_use_case import (
    CustomerRegistrationRequest,
    CustomerRegistrationResponse,
)
from ....infrastructure.container.dependency_injection import get_container
from ....infrastructure.utilities.exceptions import (
    BusinessLogicError,
    ValidationError,
    error_handler,
)
from ..keyboards.menu import get_delivery_method_keyboard, get_main_menu_keyboard
from ..states import (
    END,
    ONBOARDING_DELIVERY_ADDRESS,
    ONBOARDING_DELIVERY_METHOD,
    ONBOARDING_NAME,
    ONBOARDING_PHONE,
)

logger = logging.getLogger(__name__)


class OnboardingHandler:
    """
    Clean Architecture onboarding handler

    Uses dependency injection and use cases for business logic.
    Handles presentation layer concerns only.
    """

    def __init__(self):
        self._container = get_container()
        self._customer_registration_use_case = (
            self._container.get_customer_registration_use_case()
        )
        self._logger = logging.getLogger(self.__class__.__name__)

    async def start_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """Handle /start command - begin onboarding process"""
        user = update.effective_user

        self._logger.info(
            f"Start command received from user {user.id} ({user.username})"
        )

        try:
            # Check if user is already registered using use case
            existing_customer = (
                await self._customer_registration_use_case.find_customer_by_telegram_id(
                    user.id
                )
            )

            if existing_customer:
                # Welcome back existing customer with menu in one message
                welcome_message = (
                    f"Hi {existing_customer.full_name.value}, great to see you again! 🎉\n\n"
                    "What would you like to order today?"
                )
                await update.message.reply_text(
                    welcome_message,
                    reply_markup=get_main_menu_keyboard(),
                )
                return END

            # Start onboarding for new customer
            await update.message.reply_text(
                "Welcome to Samna Salta! 🍞\n\n"
                "I'm here to help you order our delicious traditional Yemenite products.\n\n"
                "To get started, please tell me your full name:"
            )
            return ONBOARDING_NAME

        except Exception as e:
            self._logger.error(f"Error in start_command: {e}")
            await self._send_error_message(
                update, "Sorry, there was an error. Please try again with /start"
            )
            return END

    async def handle_name(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """Handle customer name input with validation"""
        try:
            name = update.message.text.strip()

            # Basic validation
            if len(name) < 2:
                await update.message.reply_text(
                    "Please enter your full name (at least 2 characters):"
                )
                return ONBOARDING_NAME

            # Store name in context
            context.user_data["full_name"] = name

            await update.message.reply_text(
                f"Nice to meet you, {name}! 👋\n\n"
                "Now, please share your phone number so we can contact you about your order:"
            )
            return ONBOARDING_PHONE

        except Exception as e:
            self._logger.error(f"Error in handle_name: {e}")
            await self._send_error_message(update, "Please try again with /start")
            return END

    async def handle_phone(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """Handle customer phone number input with validation"""
        try:
            phone = update.message.text.strip()
            user_id = update.effective_user.id
            full_name = context.user_data.get("full_name")

            if not full_name:
                await self._send_error_message(
                    update, "Session expired. Please start again with /start"
                )
                return END

            # Use customer registration use case
            registration_request = CustomerRegistrationRequest(
                telegram_id=user_id, full_name=full_name, phone_number=phone
            )

            response = await self._customer_registration_use_case.execute(
                registration_request
            )

            if not response.success:
                # Show validation error to user
                await update.message.reply_text(
                    f"❌ {response.error_message}\n\nPlease try again:"
                )
                return ONBOARDING_PHONE

            # Store customer data in context
            context.user_data["customer"] = response.customer
            context.user_data["phone_number"] = phone

            if response.is_returning_customer:
                await update.message.reply_text(
                    f"Welcome back, {response.customer.full_name.value}! 🎉\n\n"
                    "Your information has been updated.\n\n"
                    "What would you like to order today?",
                    reply_markup=get_main_menu_keyboard()
                )
                return END
            else:
                await update.message.reply_text(
                    f"Thank you, {response.customer.full_name.value}! 📱\n\n"
                    "How would you like to receive your order?\n\n"
                    "Please choose your delivery method:",
                    reply_markup=get_delivery_method_keyboard(),
                )
                return ONBOARDING_DELIVERY_METHOD

        except ValidationError as e:
            self._logger.warning(f"Validation error in handle_phone: {e}")
            await update.message.reply_text(
                f"❌ {str(e)}\n\nPlease enter a valid phone number:"
            )
            return ONBOARDING_PHONE
        except Exception as e:
            self._logger.error(f"Error in handle_phone: {e}")
            await self._send_error_message(update, "Please try again with /start")
            return END

    async def handle_delivery_method(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """Handle delivery method selection"""
        try:
            query = update.callback_query
            await query.answer()

            delivery_method = query.data.split("_")[1]  # 'pickup' or 'delivery'
            context.user_data["delivery_method"] = delivery_method

            if delivery_method == "pickup":
                # For pickup, go directly to menu
                await query.edit_message_text(
                    "Perfect! You've chosen self-pickup. We'll contact you to coordinate the pickup time.\n\n"
                    "What would you like to order?",
                    reply_markup=get_main_menu_keyboard(),
                )
                return END
            else:
                # For delivery, ask for address
                await query.edit_message_text(
                    "Great! You've chosen delivery. There's a 5 ILS delivery charge.\n\n"
                    "Please provide your full delivery address:"
                )
                return ONBOARDING_DELIVERY_ADDRESS

        except Exception as e:
            self._logger.error(f"Error in handle_delivery_method: {e}")
            await self._send_error_message(
                update.callback_query, "Please try again with /start"
            )
            return END

    async def handle_delivery_address(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """Handle delivery address input with business validation"""
        try:
            address = update.message.text.strip()

            # Business rule validation
            if len(address) < 10:
                await update.message.reply_text(
                    "Please provide a complete delivery address (at least 10 characters):"
                )
                return ONBOARDING_DELIVERY_ADDRESS

            # Store address in context
            context.user_data["delivery_address"] = address

            # Update customer with delivery address if we have a customer
            customer = context.user_data.get("customer")
            if customer and hasattr(customer, "id") and customer.id:
                try:
                    # Create updated registration request
                    updated_request = CustomerRegistrationRequest(
                        telegram_id=update.effective_user.id,
                        full_name=customer.full_name.value,
                        phone_number=customer.phone_number.value,
                        delivery_address=address,
                    )

                    # Update customer through use case
                    await self._customer_registration_use_case.execute(updated_request)

                except Exception as e:
                    self._logger.warning(f"Failed to update customer address: {e}")
                    # Continue anyway - address is stored in context

            await update.message.reply_text(
                f"Perfect! Your delivery address is: {address}\n\n"
                "What would you like to order?",
                reply_markup=get_main_menu_keyboard()
            )
            return END

        except Exception as e:
            self._logger.error(f"Error in handle_delivery_address: {e}")
            await self._send_error_message(update, "Please try again with /start")
            return END

    async def cancel_onboarding(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """Handle onboarding cancellation"""
        self._logger.info(f"Onboarding cancelled by user {update.effective_user.id}")

        await update.message.reply_text(
            "Onboarding cancelled. You can start again anytime with /start"
        )

        # Clear context
        context.user_data.clear()
        return END

    async def handle_unknown_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle unknown commands during onboarding"""
        await update.message.reply_text(
            "I didn't understand that command. Please use /start to begin ordering."
        )

    async def handle_unknown_message(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle unexpected messages during onboarding"""
        await update.message.reply_text(
            "Please follow the onboarding steps. Use /cancel to restart or /start to begin."
        )

    async def _send_error_message(self, update, message: str):
        """Send error message handling both Update and CallbackQuery"""
        try:
            if hasattr(update, "callback_query") and update.callback_query:
                await update.callback_query.message.reply_text(message)
            elif hasattr(update, "message") and update.message:
                await update.message.reply_text(message)
            else:
                # Fallback
                await update.effective_message.reply_text(message)
        except Exception as e:
            self._logger.error(f"Error sending error message: {e}")


def register_onboarding_handlers(application):
    """Register onboarding conversation handler with Clean Architecture"""
    handler = OnboardingHandler()

    # Create conversation handler
    onboarding_conv = ConversationHandler(
        entry_points=[CommandHandler("start", handler.start_command)],
        states={
            ONBOARDING_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handler.handle_name)
            ],
            ONBOARDING_PHONE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handler.handle_phone)
            ],
            ONBOARDING_DELIVERY_METHOD: [
                CallbackQueryHandler(
                    handler.handle_delivery_method, pattern="^delivery_"
                )
            ],
            ONBOARDING_DELIVERY_ADDRESS: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, handler.handle_delivery_address
                )
            ],
        },
        fallbacks=[
            CommandHandler("cancel", handler.cancel_onboarding),
            MessageHandler(filters.COMMAND, handler.handle_unknown_command),
            MessageHandler(filters.ALL, handler.handle_unknown_message),
        ],
        name="onboarding",
        persistent=False,
    )

    application.add_handler(onboarding_conv)
