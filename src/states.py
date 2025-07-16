"""
Conversation states for the Telegram bot.
"""

from telegram.ext import ConversationHandler

# Onboarding states
ONBOARDING_LANGUAGE = 1
ONBOARDING_NAME = 2
ONBOARDING_PHONE = 3
ONBOARDING_DELIVERY_METHOD = 4
ONBOARDING_DELIVERY_ADDRESS = 5

# Cart states
CART_QUANTITY = 6
CART_OPTIONS = 7

# Order states
ORDER_CONFIRMATION = 8
ORDER_DELIVERY_ADDRESS = 9

# End conversation
END = ConversationHandler.END 