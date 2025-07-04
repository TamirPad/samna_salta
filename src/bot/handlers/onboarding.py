"""
Onboarding handlers for the Samna Salta bot
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from telegram.constants import ParseMode

from src.bot.states import ONBOARDING_NAME, ONBOARDING_PHONE, ONBOARDING_DELIVERY_METHOD, ONBOARDING_DELIVERY_ADDRESS, END
from src.bot.keyboards.menu import get_delivery_method_keyboard, get_main_menu_keyboard
from src.database.operations import get_or_create_customer, get_customer_by_telegram_id
from src.utils.helpers import sanitize_phone_number, validate_phone_number

logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle /start command - begin onboarding process"""
    user = update.effective_user
    
    logger.info(f"Start command received from user {user.id} ({user.username})")
    
    try:
        # Check if user is already registered
        existing_customer = get_customer_by_telegram_id(user.id)
        if existing_customer:
            # Welcome back existing customer
            welcome_message = f"Hi {existing_customer.full_name}, great to see you again! 🎉"
            await update.message.reply_text(welcome_message)
            
            # Show main menu
            await update.message.reply_text(
                "What would you like to order today?",
                reply_markup=get_main_menu_keyboard()
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
        logger.error(f"Error in start_command: {e}")
        await update.message.reply_text(
            "Sorry, there was an error. Please try again with /start"
        )
        return END


async def handle_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle customer name input"""
    try:
        name = update.message.text.strip()
        
        if len(name) < 2:
            await update.message.reply_text(
                "Please enter your full name (at least 2 characters):"
            )
            return ONBOARDING_NAME
        
        # Store name in context
        context.user_data['full_name'] = name
        
        await update.message.reply_text(
            f"Nice to meet you, {name}! 👋\n\n"
            "Now, please share your phone number so we can contact you about your order:"
        )
        return ONBOARDING_PHONE
        
    except Exception as e:
        logger.error(f"Error in handle_name: {e}")
        await update.message.reply_text("Please try again with /start")
        return END


async def handle_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle customer phone number input"""
    try:
        phone = update.message.text.strip()
        
        # Validate phone number
        if not validate_phone_number(phone):
            await update.message.reply_text(
                "Please enter a valid Israeli phone number (e.g., 050-1234567 or +972501234567):"
            )
            return ONBOARDING_PHONE
        
        # Sanitize phone number
        sanitized_phone = sanitize_phone_number(phone)
        
        # Store phone in context
        context.user_data['phone_number'] = sanitized_phone
        
        # Create or get customer
        customer = get_or_create_customer(
            telegram_id=update.effective_user.id,
            full_name=context.user_data['full_name'],
            phone_number=sanitized_phone
        )
        context.user_data['customer_id'] = customer.id
        
        await update.message.reply_text(
            f"Thank you, {customer.full_name}! 📱\n\n"
            "How would you like to receive your order?"
        )
        
        await update.message.reply_text(
            "Please choose your delivery method:",
            reply_markup=get_delivery_method_keyboard()
        )
        return ONBOARDING_DELIVERY_METHOD
        
    except Exception as e:
        logger.error(f"Error in handle_phone: {e}")
        await update.message.reply_text("Please try again with /start")
        return END


async def handle_delivery_method(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle delivery method selection"""
    try:
        query = update.callback_query
        await query.answer()
        
        delivery_method = query.data.split('_')[1]  # 'pickup' or 'delivery'
        context.user_data['delivery_method'] = delivery_method
        
        if delivery_method == 'pickup':
            # For pickup, go directly to menu
            await query.edit_message_text(
                "Perfect! You've chosen self-pickup. We'll contact you to coordinate the pickup time.\n\n"
                "Now, let's browse our menu:"
            )
            await query.message.reply_text(
                "What would you like to order?",
                reply_markup=get_main_menu_keyboard()
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
        logger.error(f"Error in handle_delivery_method: {e}")
        await update.callback_query.message.reply_text("Please try again with /start")
        return END


async def handle_delivery_address(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle delivery address input"""
    try:
        address = update.message.text.strip()
        
        if len(address) < 10:
            await update.message.reply_text(
                "Please provide a complete delivery address (at least 10 characters):"
            )
            return ONBOARDING_DELIVERY_ADDRESS
        
        # Store address in context
        context.user_data['delivery_address'] = address
        
        # Update customer with delivery address if new customer
        if 'customer_id' in context.user_data:
            from src.database.operations import get_session
            from src.database.models import Customer
            
            session = get_session()
            try:
                customer = session.query(Customer).filter(
                    Customer.id == context.user_data['customer_id']
                ).first()
                if customer:
                    customer.delivery_address = address
                    session.commit()
            finally:
                session.close()
        
        await update.message.reply_text(
            f"Perfect! Your delivery address is: {address}\n\n"
            "Now, let's browse our menu:"
        )
        await update.message.reply_text(
            "What would you like to order?",
            reply_markup=get_main_menu_keyboard()
        )
        return END
        
    except Exception as e:
        logger.error(f"Error in handle_delivery_address: {e}")
        await update.message.reply_text("Please try again with /start")
        return END


async def cancel_onboarding(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel onboarding process"""
    await update.message.reply_text(
        "Onboarding cancelled. You can start again with /start"
    )
    return END


# Simple fallback handlers for testing
async def handle_unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle unknown commands"""
    await update.message.reply_text(
        "I don't understand that command. Try /start to begin ordering."
    )


async def handle_unknown_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle messages outside conversation"""
    await update.message.reply_text(
        "Please start with /start to begin your order."
    )


def register_onboarding_handlers(application):
    """Register onboarding handlers"""
    # Main conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start_command)],
        states={
            ONBOARDING_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_name)],
            ONBOARDING_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_phone)],
            ONBOARDING_DELIVERY_METHOD: [CallbackQueryHandler(handle_delivery_method, pattern="^delivery_")],
            ONBOARDING_DELIVERY_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_delivery_address)],
        },
        fallbacks=[CommandHandler("cancel", cancel_onboarding)],
        per_message=False,
        per_chat=True,
        per_user=True,
    )
    
    application.add_handler(conv_handler)
    
    # Fallback handlers
    application.add_handler(MessageHandler(filters.COMMAND, handle_unknown_command))
    application.add_handler(MessageHandler(filters.TEXT, handle_unknown_message)) 