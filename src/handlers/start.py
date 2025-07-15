"""
Onboarding Handler for the Telegram bot.
"""

import logging

from telegram import Update
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
                # Welcome back existing customer with menu
                welcome_message = (
                    i18n.get_text("WELCOME_BACK").format(name=existing_customer.full_name) + "\n\n" +
                    i18n.get_text("WHAT_TO_ORDER_TODAY")
                )
                await update.message.reply_text(
                    welcome_message,
                    reply_markup=get_main_menu_keyboard(),
                    parse_mode="HTML"
                )
                return END

            # Start onboarding for new customer
            await update.message.reply_text(
                i18n.get_text("WELCOME_NEW_USER") + "\n\n" +
                i18n.get_text("WELCOME_HELP_MESSAGE") + "\n\n" +
                i18n.get_text("PLEASE_ENTER_NAME"),
                parse_mode="HTML"
            )
            return ONBOARDING_NAME

        except Exception as e:
            self.logger.error("Error in start_command: %s", e, exc_info=True)
            await self._send_error_message(
                update, ErrorMessages.ERROR_TRY_START_AGAIN
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
                    i18n.get_text("NAME_TOO_SHORT"),
                    parse_mode="HTML"
                )
                return ONBOARDING_NAME

            # Store name in context
            context.user_data["full_name"] = name

            await update.message.reply_text(
                i18n.get_text("NICE_TO_MEET").format(name=name) + "\n\n" +
                i18n.get_text("PLEASE_SHARE_PHONE"),
                parse_mode="HTML"
            )
            return ONBOARDING_PHONE

        except Exception as e:
            self.logger.error("Error in handle_name: %s", e, exc_info=True)
            await self._send_error_message(update, ErrorMessages.ERROR_TRY_START_AGAIN)
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
                    update, ErrorMessages.SESSION_EXPIRED
                )
                return END

            # Validate customer data
            validation = self.cart_service.validate_customer_data(full_name, phone)
            if not validation["valid"]:
                error_msg = ", ".join(validation["errors"])
                await update.message.reply_text(
                    ErrorMessages.VALIDATION_ERROR.format(error=error_msg) + "\n\n" + ErrorMessages.PLEASE_TRY_AGAIN,
                    parse_mode="HTML"
                )
                return ONBOARDING_PHONE

            # Register customer
            result = self.cart_service.register_customer(user_id, full_name, phone)
            
            if not result["success"]:
                await update.message.reply_text(
                    ErrorMessages.VALIDATION_ERROR.format(error=result["error"]) + "\n\n" + ErrorMessages.PLEASE_TRY_AGAIN,
                    parse_mode="HTML"
                )
                return ONBOARDING_PHONE

            # Store customer data in context
            context.user_data["customer"] = result["customer"]
            context.user_data["phone_number"] = phone

            if result["is_returning"]:
                await update.message.reply_text(
                    i18n.get_text("WELCOME_BACK_UPDATED").format(name=result["customer"].full_name) + "\n\n" +
                    i18n.get_text("INFO_UPDATED") + "\n\n" +
                    i18n.get_text("WHAT_TO_ORDER_TODAY"),
                    reply_markup=get_main_menu_keyboard(),
                    parse_mode="HTML"
                )
                next_state = END
            else:
                await update.message.reply_text(
                    i18n.get_text("THANK_YOU_PHONE").format(name=result["customer"].full_name) + "\n\n" +
                    i18n.get_text("HOW_RECEIVE_ORDER") + "\n\n" +
                    i18n.get_text("CHOOSE_DELIVERY_METHOD"),
                    reply_markup=get_delivery_method_keyboard(),
                    parse_mode="HTML"
                )
                next_state = ONBOARDING_DELIVERY_METHOD

        except Exception as e:
            self.logger.error("Error in handle_phone: %s", e, exc_info=True)
            await update.message.reply_text(
                i18n.get_text("VALIDATION_ERROR").format(error=str(e)) + "\n\n" + i18n.get_text("ENTER_VALID_PHONE")
            )
            next_state = ONBOARDING_PHONE

        return next_state

    async def handle_delivery_method(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """Handle delivery method selection"""
        try:
            query = update.callback_query
            await query.answer()

            delivery_method = query.data.replace("delivery_", "")
            context.user_data["delivery_method"] = delivery_method

            if delivery_method == "delivery":
                await query.edit_message_text(
                    i18n.get_text("PLEASE_ENTER_DELIVERY_ADDRESS"),
                    parse_mode="HTML"
                )
                return ONBOARDING_DELIVERY_ADDRESS
            else:
                # Pickup - complete registration
                customer = context.user_data.get("customer")
                if customer:
                    # Update customer with delivery method
                    self.cart_service.register_customer(
                        customer.telegram_id,
                        customer.full_name,
                        customer.phone_number,
                        delivery_method=delivery_method
                    )

                await query.edit_message_text(
                    i18n.get_text("REGISTRATION_COMPLETE") + "\n\n" + i18n.get_text("WHAT_TO_ORDER_TODAY"),
                    reply_markup=get_main_menu_keyboard(),
                    parse_mode="HTML"
                )
                return END

        except Exception as e:
            self.logger.error("Error in handle_delivery_method: %s", e, exc_info=True)
            await self._send_error_message(update, i18n.ERROR_TRY_START_AGAIN)
            return END

    async def handle_delivery_address(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """Handle delivery address input"""
        try:
            address = update.message.text.strip()
            customer = context.user_data.get("customer")
            delivery_method = context.user_data.get("delivery_method")

            if not customer or not delivery_method:
                await self._send_error_message(update, i18n.SESSION_EXPIRED)
                return END

            # Update customer with delivery address
            self.cart_service.register_customer(
                customer.telegram_id,
                customer.full_name,
                customer.phone_number,
                address
            )

            await update.message.reply_text(
                i18n.get_text("REGISTRATION_COMPLETE") + "\n\n" + i18n.get_text("WHAT_TO_ORDER_TODAY"),
                reply_markup=get_main_menu_keyboard(),
                parse_mode="HTML"
            )
            return END

        except Exception as e:
            self.logger.error("Error in handle_delivery_address: %s", e, exc_info=True)
            await self._send_error_message(update, i18n.ERROR_TRY_START_AGAIN)
            return END

    async def cancel_onboarding(
        self, update: Update, _: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """Cancel onboarding process"""
        await update.message.reply_text(
            i18n.get_text("ONBOARDING_CANCELLED"),
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


def register_start_handlers(application: Application):
    """Register onboarding conversation handler"""
    handler = OnboardingHandler()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", handler.start_command)],
        states={
            ONBOARDING_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handler.handle_name),
                CommandHandler("cancel", handler.cancel_onboarding),
            ],
            ONBOARDING_PHONE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handler.handle_phone),
                CommandHandler("cancel", handler.cancel_onboarding),
            ],
            ONBOARDING_DELIVERY_METHOD: [
                CallbackQueryHandler(handler.handle_delivery_method, pattern="^delivery_"),
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
    )

    application.add_handler(conv_handler)


# Handler function for direct registration
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start handler for direct registration"""
    handler = OnboardingHandler()
    return await handler.start_command(update, context)
