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

from src.states import (
    END,
    ONBOARDING_DELIVERY_ADDRESS,
    ONBOARDING_DELIVERY_METHOD,
    ONBOARDING_LANGUAGE,
    ONBOARDING_CHOICE,
    ONBOARDING_NAME,
    ONBOARDING_PHONE,
)
from src.utils.i18n import i18n
from src.utils.helpers import get_dynamic_welcome_message, get_dynamic_welcome_for_returning_users


logger = logging.getLogger(__name__)


class OnboardingHandler:
    """Onboarding handler for new customers"""

    def __init__(self):
        self.container = get_container()
        self.cart_service = self.container.get_cart_service()
        self.logger = logging.getLogger(self.__class__.__name__)

    async def _update_single_window(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, reply_markup=None, parse_mode: str = "HTML"):
        """Always keep a single bot message visible by editing the last bot message when possible.
        - If invoked from a callback query, edit that message (or its caption) or delete and send a new one.
        - If invoked from a user text message, edit the last stored bot message; if missing, send a new one.
        Stores the last bot message id in context.user_data['last_bot_message_id'].
        """
        try:
            if update.callback_query:
                query = update.callback_query
                msg = query.message
                try:
                    if getattr(msg, "text", None):
                        await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode=parse_mode)
                        context.user_data["last_bot_message_id"] = msg.message_id
                        return
                    # Photo/caption message
                    if getattr(msg, "caption", None) is not None or getattr(msg, "photo", None):
                        # Try editing caption first
                        try:
                            await query.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode=parse_mode)
                            context.user_data["last_bot_message_id"] = msg.message_id
                            return
                        except Exception:
                            pass
                    # Fallback: delete and send new
                    try:
                        await msg.delete()
                    except Exception:
                        pass
                    sent = await msg.reply_text(text=text, reply_markup=reply_markup, parse_mode=parse_mode)
                    context.user_data["last_bot_message_id"] = sent.message_id
                    return
                except Exception:
                    # Last resort
                    sent = await msg.reply_text(text=text, reply_markup=reply_markup, parse_mode=parse_mode)
                    context.user_data["last_bot_message_id"] = sent.message_id
                    return

            # Message-based flow (user typed input)
            chat_id = update.effective_chat.id
            last_id = context.user_data.get("last_bot_message_id")
            if last_id:
                # Try editing previous bot message
                try:
                    await context.bot.edit_message_text(chat_id=chat_id, message_id=last_id, text=text, reply_markup=reply_markup, parse_mode=parse_mode)
                    return
                except Exception:
                    # Try editing caption (in case the last message was a photo)
                    try:
                        await context.bot.edit_message_caption(chat_id=chat_id, message_id=last_id, caption=text, reply_markup=reply_markup, parse_mode=parse_mode)
                        return
                    except Exception:
                        # Delete and send a new message
                        try:
                            await context.bot.delete_message(chat_id=chat_id, message_id=last_id)
                        except Exception:
                            pass
            sent = await update.effective_chat.send_message(text=text, reply_markup=reply_markup, parse_mode=parse_mode)
            context.user_data["last_bot_message_id"] = sent.message_id
        except Exception as e:
            self.logger.error("_update_single_window failed: %s", e)

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
                    # Welcome back existing customer with beautiful main page
                    user_id = user.id
                    
                    # Fetch optional business description to show under the welcome headline
                    try:
                        from src.db.operations import get_business_settings_dict
                        _settings = get_business_settings_dict()
                        _desc = (_settings or {}).get("business_description")
                        description_line = f"\n{_desc}" if _desc else ""
                    except Exception:
                        description_line = ""

                    welcome_message = f"""🌟 <b>{get_dynamic_welcome_for_returning_users(user_id=user_id)}</b>{description_line}

👋 <b>{i18n.get_text("WELCOME_BACK", user_id=user_id).format(name=existing_customer.name)}</b>

🍽️ {i18n.get_text("WHAT_TO_ORDER_TODAY", user_id=user_id)}"""
                    await self._update_single_window(update, _, welcome_message, self._get_main_page_keyboard(user_id))
                    return END
                else:
                    # Customer exists but profile is incomplete - restart onboarding
                    self.logger.info("Customer %s has incomplete profile, restarting onboarding", user.id)
                    await self._update_single_window(update, _, i18n.get_text("PROFILE_INCOMPLETE", user_id=user.id) + "\n\n" + i18n.get_text("PLEASE_COMPLETE_PROFILE", user_id=user.id))
                    # Continue to language selection

            # Start onboarding for new customer or incomplete profile with beautiful language selection
            user_id = user.id
            # Fetch optional business description to show under the welcome headline
            try:
                from src.db.operations import get_business_settings_dict
                _settings = get_business_settings_dict()
                _desc = (_settings or {}).get("business_description")
                description_line = f"\n{_desc}" if _desc else ""
            except Exception:
                description_line = ""

            welcome_text = f"""🎉 <b>{get_dynamic_welcome_message(user_id=user_id)}</b>{description_line}

🌍 {i18n.get_text("SELECT_LANGUAGE_PROMPT", user_id=user_id)}"""

            await self._update_single_window(update, _, welcome_text, self._get_language_selection_keyboard())
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
                
                await self._update_single_window(update, context,
                    i18n.get_text("ONBOARDING_CHOICE_PROMPT", language="en"),
                    self._get_onboarding_choice_keyboard(user_id)
                )
                return ONBOARDING_CHOICE
            elif data == "language_he":
                # Store language preference in context for later use
                context.user_data["selected_language"] = "he"
                # Also update the language manager cache for immediate use
                from src.utils.language_manager import language_manager
                language_manager._user_languages[user_id] = "he"
                
                await self._update_single_window(update, context,
                    i18n.get_text("ONBOARDING_CHOICE_PROMPT", language="he"),
                    self._get_onboarding_choice_keyboard(user_id)
                )
                return ONBOARDING_CHOICE
            else:
                # Invalid language selection
                await self._update_single_window(update, context, i18n.get_text("INVALID_CHOICE", user_id=user_id) + "\n\n" + i18n.get_text("SELECT_LANGUAGE_PROMPT", user_id=user_id), self._get_language_selection_keyboard())
                return ONBOARDING_LANGUAGE

        except Exception as e:
            self.logger.error("Error in handle_language_selection: %s", e, exc_info=True)
            await self._send_error_message(update, i18n.get_text("ERROR_TRY_START_AGAIN", user_id=user_id))
            return END

    async def handle_onboarding_choice(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """Handle selection between signup and guest after language selection"""
        try:
            query = update.callback_query
            await query.answer()

            user_id = update.effective_user.id
            data = query.data

            if data == "onboard_signup":
                # Proceed with existing signup flow
                lang = context.user_data.get("selected_language") or "he"
                await self._update_single_window(
                    update,
                    context,
                    i18n.get_text("PLEASE_ENTER_NAME", language=lang),
                )
                return ONBOARDING_NAME
            elif data == "onboard_guest":
                # Create or fetch a minimal customer tied to telegram id
                from src.db.operations import get_or_create_customer
                lang = context.user_data.get("selected_language") or "he"
                tg_user = update.effective_user
                # Always save guest name as a neutral placeholder to avoid implying full signup
                display_name = "Guest"
                # phone None indicates guest (incomplete profile)
                get_or_create_customer(tg_user.id, display_name, None, lang)

                # Mark session as guest
                context.user_data["is_guest"] = True

                # Show main page with a small guest notice
                notice = i18n.get_text("GUEST_MODE_NOTICE", language=lang)
                await query.edit_message_text(
                    f"{notice}\n\n" + i18n.get_text("MENU_PROMPT", user_id=user_id),
                    reply_markup=self._get_main_page_keyboard(user_id),
                    parse_mode="HTML",
                )
                return END
            else:
                await query.edit_message_text(
                    i18n.get_text("INVALID_CHOICE", user_id=user_id),
                    reply_markup=self._get_language_selection_keyboard(),
                    parse_mode="HTML",
                )
                return ONBOARDING_LANGUAGE

        except Exception as e:
            self.logger.error("Error in handle_onboarding_choice: %s", e, exc_info=True)
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
                await self._update_single_window(update, context, i18n.get_text("NAME_TOO_SHORT", language=user_language))
                return ONBOARDING_NAME

            # Store name in context
            context.user_data["full_name"] = name

            await self._update_single_window(update, context, i18n.get_text("NICE_TO_MEET", language=user_language).format(name=name) + "\n\n" + i18n.get_text("PLEASE_SHARE_PHONE", language=user_language))
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
                await self._update_single_window(update, context, i18n.get_text("VALIDATION_ERROR", language=user_language).format(error=error_msg) + "\n\n" + i18n.get_text("PLEASE_TRY_AGAIN", language=user_language))
                return ONBOARDING_PHONE
            
            # Register customer
            result = self.cart_service.register_customer(user_id, full_name, phone, user_language)
            
            if not result["success"]:
                await self._update_single_window(update, context, i18n.get_text("VALIDATION_ERROR", language=user_language).format(error=result["error"]) + "\n\n" + i18n.get_text("PLEASE_TRY_AGAIN", language=user_language))
                return ONBOARDING_PHONE

            # Store customer data in context
            context.user_data["customer"] = result["customer"]
            context.user_data["phone_number"] = phone

            if result["is_returning"]:
                await self._update_single_window(update, context, i18n.get_text("WELCOME_BACK_UPDATED", language=user_language).format(name=result["customer"].name) + "\n\n" + i18n.get_text("INFO_UPDATED", language=user_language) + "\n\n" + get_dynamic_welcome_for_returning_users(user_id=user_id) + "\n\n" + i18n.get_text("WHAT_TO_ORDER_TODAY", language=user_language), self._get_main_page_keyboard(user_id))
                next_state = END
            else:
                await self._update_single_window(update, context, i18n.get_text("THANK_YOU_PHONE", language=user_language).format(name=result["customer"].name) + "\n\n" + i18n.get_text("PLEASE_ENTER_DELIVERY_ADDRESS_ONBOARDING", language=user_language) + "\n\n" + i18n.get_text("DELIVERY_ADDRESS_ONBOARDING_HELP", language=user_language))
                next_state = ONBOARDING_DELIVERY_ADDRESS

        except Exception as e:
            self.logger.error("Error in handle_phone: %s", e, exc_info=True)
            await self._update_single_window(update, context, i18n.get_text("VALIDATION_ERROR", language=user_language).format(error=str(e)) + "\n\n" + i18n.get_text("ENTER_VALID_PHONE", language=user_language))
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
                await self._update_single_window(update, context, i18n.get_text("ADDRESS_TOO_SHORT", user_id=user_id))
                return ONBOARDING_DELIVERY_ADDRESS

            # Update customer with delivery address
            self.cart_service.update_customer_delivery_address(
                customer.telegram_id,
                address
            )

            user_id = update.effective_user.id
            await self._update_single_window(update, context, i18n.get_text("REGISTRATION_COMPLETE", user_id=user_id) + "\n\n" + i18n.get_text("DELIVERY_ADDRESS_SAVED_ONBOARDING", user_id=user_id).format(address=address) + "\n\n" + get_dynamic_welcome_message(user_id=user_id) + "\n\n" + i18n.get_text("WHAT_TO_ORDER_TODAY", user_id=user_id), self._get_main_page_keyboard(user_id))
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
        await self._update_single_window(update, _, i18n.get_text("ONBOARDING_CANCELLED", user_id=user_id))
        return END

    @error_handler("unknown_command")
    async def handle_unknown_command(
        self, update: Update, _: ContextTypes.DEFAULT_TYPE
    ):
        """Handle unknown commands during onboarding"""
        await self._update_single_window(update, _, i18n.get_text("UNKNOWN_COMMAND_ONBOARDING"))

    @error_handler("unknown_message")
    async def handle_unknown_message(
        self, update: Update, _: ContextTypes.DEFAULT_TYPE
    ):
        """Handle unknown messages during onboarding"""
        await self._update_single_window(update, _, i18n.get_text("UNKNOWN_MESSAGE_ONBOARDING"))

    async def _send_error_message(self, update, message: str):
        """Send error message to user"""
        try:
            if update.callback_query:
                await self._update_single_window(update, None, message)
            else:
                await self._update_single_window(update, None, message)
        except Exception as e:
            self.logger.error("Failed to send error message: %s", e)

    def _get_language_selection_keyboard(self):
        """Get professional language selection keyboard"""
        keyboard = [
            [
                InlineKeyboardButton("🇺🇸 English", callback_data="language_en"),
                InlineKeyboardButton("🇮🇱 עברית", callback_data="language_he"),
            ],
        ]
        return InlineKeyboardMarkup(keyboard)

    def _get_onboarding_choice_keyboard(self, user_id: int):
        keyboard = [
            [InlineKeyboardButton(i18n.get_text("BUTTON_SIGN_UP", user_id=user_id), callback_data="onboard_signup")],
            [InlineKeyboardButton(i18n.get_text("BUTTON_CONTINUE_AS_GUEST", user_id=user_id), callback_data="onboard_guest")],
        ]
        return InlineKeyboardMarkup(keyboard)

    def _get_main_page_keyboard(self, user_id: int = None):
        """Get professional main page keyboard with each button on its own line"""
        keyboard = [
            # Menu button
            [InlineKeyboardButton(
                i18n.get_text('BUTTON_MENU', user_id=user_id), 
                callback_data="main_menu"
            )],
            # My Profile button
            [InlineKeyboardButton(
                i18n.get_text('BUTTON_MY_INFO', user_id=user_id), 
                callback_data="main_my_info"
            )],
            # Track Orders button
            [InlineKeyboardButton(
                i18n.get_text('BUTTON_TRACK_ORDERS', user_id=user_id), 
                callback_data="main_track_orders"
            )],
            # Contact Us button
            [InlineKeyboardButton(
                i18n.get_text('BUTTON_CONTACT_US', user_id=user_id), 
                callback_data="main_contact_us"
            )],
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
            elif data == "main_track_orders":
                await self._show_track_orders(query)
            elif data == "main_contact_us":
                await self._show_contact_us(query)
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
                info_text = f"""
👤 <b>{i18n.get_text('MY_INFO_TITLE', user_id=user_id)}</b>

👨‍💼 <b>{i18n.get_text('NAME_FIELD', user_id=user_id)}</b> {customer.name or '🤷'}
📞 <b>{i18n.get_text('PHONE_FIELD', user_id=user_id)}</b> {customer.phone or '📞'}
🏠 <b>{i18n.get_text('ADDRESS_FIELD', user_id=user_id)}</b> {customer.delivery_address or i18n.get_text('NOT_SET', user_id=user_id)}

💬 {i18n.get_text('CONTACT_SUPPORT_FOR_UPDATES', user_id=user_id)}
                """.strip()
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
            
            new_text = i18n.get_text("MENU_PROMPT", user_id=user_id)
            new_markup = get_dynamic_main_menu_keyboard(user_id)

            # Avoid Telegram error when text/markup are identical
            try:
                await query.edit_message_text(
                    new_text,
                    reply_markup=new_markup,
                    parse_mode="HTML"
                )
            except Exception as e:
                if "Message is not modified" in str(e):
                    # Nothing to change; silently ignore
                    return
                raise

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
                    f"<b>{get_dynamic_welcome_for_returning_users(user_id=user_id)}</b>\n\n"
                    f"<b>{i18n.get_text('WELCOME_BACK', user_id=user_id).format(name=customer.name)}</b>\n\n"
                    f"{i18n.get_text('WHAT_TO_ORDER_TODAY', user_id=user_id)}"
                )
            else:
                welcome_message = (
                    f"<b>{get_dynamic_welcome_for_returning_users(user_id=user_id)}</b>\n\n"
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
        """Get professional My Info keyboard with beautiful styling"""
        from src.utils.language_manager import language_manager
        
        current_lang = language_manager.get_user_language(user_id)
        
        keyboard = [
            [InlineKeyboardButton(
                i18n.get_text('LANGUAGE_BUTTON', user_id=user_id), 
                callback_data="language_selection"
            )],
            [InlineKeyboardButton(
                i18n.get_text('BACK_TO_MAIN', user_id=user_id), 
                callback_data="main_page"
            )],
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

    async def _show_track_orders(self, query: CallbackQuery):
        """Show track orders interface with options for active and completed orders"""
        try:
            user_id = query.from_user.id
            
            text = i18n.get_text("TRACK_ORDERS_TITLE", user_id=user_id)
            keyboard = [
                [InlineKeyboardButton(
                    i18n.get_text("BUTTON_ACTIVE_ORDERS", user_id=user_id), 
                    callback_data="main_active_orders"
                )],
                [InlineKeyboardButton(
                    i18n.get_text("BUTTON_COMPLETED_ORDERS", user_id=user_id), 
                    callback_data="main_completed_orders"
                )],
                [InlineKeyboardButton(
                    i18n.get_text("BACK_TO_MAIN", user_id=user_id), 
                    callback_data="main_page"
                )],
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                text, parse_mode="HTML", reply_markup=reply_markup
            )
            
        except Exception as e:
            self.logger.error("Error showing track orders: %s", e)
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
                i18n.get_text("CUSTOMER_ORDER_DETAILS_TITLE", user_id=user_id).format(number=order["order_id"]),
                "",
                i18n.get_text("CUSTOMER_ORDER_STATUS", user_id=user_id).format(status=order["status"].capitalize()),
                i18n.get_text("CUSTOMER_ORDER_TOTAL", user_id=user_id).format(total=order["total"]),
                i18n.get_text("CUSTOMER_ORDER_DATE", user_id=user_id).format(
                    date=order["created_at"].strftime('%Y-%m-%d %H:%M') if order["created_at"] else i18n.get_text("UNKNOWN_DATE", user_id=user_id)
                ),
                i18n.get_text("CUSTOMER_ORDER_DELIVERY_METHOD", user_id=user_id).format(
                    method=order["delivery_method"].capitalize() if order["delivery_method"] else i18n.get_text("UNKNOWN_METHOD", user_id=user_id)
                ),
            ]
            
            if order.get("delivery_address"):
                details.append(
                    i18n.get_text("CUSTOMER_ORDER_DELIVERY_ADDRESS", user_id=user_id).format(
                        address=order["delivery_address"]
                    )
                )
            
            if order.get("items"):
                details.append("")
                details.append(i18n.get_text('CUSTOMER_ORDER_ITEMS', user_id=user_id))
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

    async def _show_contact_us(self, query: CallbackQuery):
        """Show business contact information"""
        try:
            user_id = query.from_user.id
            
            # Get business contact information from settings
            from src.utils.helpers import get_business_info_for_customers
            business_info = get_business_info_for_customers(user_id, compact=False)
            
            if business_info:
                text = f"{i18n.get_text('CONTACT_US_TITLE', user_id=user_id)}\n\n{business_info}"
            else:
                text = i18n.get_text("CONTACT_INFO_NOT_AVAILABLE", user_id=user_id)
            
            keyboard = [
                [InlineKeyboardButton(i18n.get_text("BACK_TO_MAIN", user_id=user_id), callback_data="main_page")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                text, parse_mode="HTML", reply_markup=reply_markup
            )
            
        except Exception as e:
            self.logger.error("Error showing contact us: %s", e)
            await query.edit_message_text(
                i18n.get_text("UNEXPECTED_ERROR", user_id=user_id),
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
            ONBOARDING_CHOICE: [
                CallbackQueryHandler(handler.handle_onboarding_choice, pattern="^(onboard_signup|onboard_guest)$"),
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
