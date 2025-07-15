"""
Conversation states for the Telegram bot.
"""

from telegram.ext import ConversationHandler

# Onboarding states
ONBOARDING_NAME = 1
ONBOARDING_PHONE = 2
ONBOARDING_DELIVERY_METHOD = 3
ONBOARDING_DELIVERY_ADDRESS = 4

# Cart states
CART_QUANTITY = 5
CART_OPTIONS = 6

# Order states
ORDER_CONFIRMATION = 7
ORDER_DELIVERY_ADDRESS = 8

# End conversation
END = ConversationHandler.END 